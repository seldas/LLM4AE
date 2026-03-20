// annotate_panel.tsx
'use client';

import { useState, useReducer, useEffect, useRef, useMemo, JSX } from 'react';
import { docReducer, initialDocState, DocActionTypes } from '../lib/doc-reducer';
import {
  Annotation,
  AnnotationOptions,
  AnnotationRelationships,
  TextContext
} from '../lib/interfaces';
import { getHistoryFile, saveAnnotationsToDb } from '../lib/api';
import {  
  escapeRegExp,
  generateOptionColors
} from '../lib/util';

import ExcelJS from 'exceljs';
import UnifiedContextMenuDisplay from '../components/context-menus/unified-context-menu';
import AnnotationPanel from '../components/annotation-panel';
import PageDisplay from '../components/page-display-brat';
import PageDisplayBuilder from '../components/page-display-builder';
import RelationshipBuilderPanel from '../components/relationship-builder-panel';
import LLMAnnotationPopup from '../components/context-menus/llm-annotation-popup';

import '../globals.css';

interface Props {
  overrideFileName?: string;
  overrideFolder?: string;
}

export default function Annotate_Panel({ overrideFileName, overrideFolder}: Props) {
  const [doc, dispatch] = useReducer(docReducer, initialDocState)
  const [selectedText, setSelectedText] = useState('');
  const [selectedSet, setSelectedSet] = useState('USER');
  const [selectedAISet, setSelectedAISet] = useState('LLM');  
  const [relationshipBuilderMode, setRelationshipBuilderMode] = useState(false);
  const [currentAnnotationRelation, setCurrentAnnotationRelation] = useState<Annotation | null>(null);
  const [currentRelationType, setCurrentRelationType] = useState<keyof AnnotationRelationships | ''>('');
  const [verificationMode, setVerificationMode] = useState(false)
  const [inspectedAnnotation, setInspectedAnnotation] = useState<Annotation | null>(null);
  const [userRole, setUserRole] = useState<"SME1" | "SME2" | "Adjudicator" | "AI">("SME1");
  const [annotationOptions, setAnnotationOptions] = useState<AnnotationOptions>({});
  const [optionColors, setOptionColors] = useState<{ [key: string]: string }>({});
  const currentPageData = doc.pages[doc.currentPageIndex] || null;    
  const [activeLabelFilters, setActiveLabelFilters] = useState<string[]>([]);
  const isUserSet = ["USER"].includes(selectedSet)
  const [unifiedContextMenu, setUnifiedContextMenu] = useState<{
          visible: boolean;
          x: number;
          y: number;
          type: 'annotation' | 'relationship' | 'verification';
          options?: string[];
          start?: number;
          end?: number;
        }>({
          visible: false,
          x: 0,
          y: 0,
          type: 'annotation',
      });
  const [llmPopup, setLlmPopup] = useState({
          visible: false,
          x: 0,
          y: 0,
          text: '',
          start: 0,
          end: 0,
      });
  const [selectedPopupLabel, setSelectedPopupLabel] = useState('');
  const [selectedTermContext, setSelectedTermContext] = useState<{ text: string; start: number; end: number } | null>(null);
  const [saveAsName, setSaveAsName] = useState('');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showRightPanel, setShowRightPanel] = useState(true);
  const [isExportDropdownOpen, setIsExportDropdownOpen] = useState(false);

  const labelNormalizer: Record<string, string> = {
      // 'MHX': 'HX',
      // 'FHX': 'HX',
      // 'CDRUG': 'DRUG',
      // 'SDRUG': 'DRUG',
      // 'MAE': 'AE',
      'R/O': 'DIAGNOSTIC',
      // 'PDX': 'DIAGNOSIS',
      // 'SDX': 'DIAGNOSIS',
      'BSYM': 'MEDICAL HISTORY',
      // Add more if needed
      'TEMPO': 'TEMPORAL',
      'DATE': 'TEMPORAL',
      'TIME': 'TEMPORAL',
      'DURATION': 'TEMPORAL',
      'RELATIVE': 'TEMPORAL',
      'LATENCY': 'TEMPORAL',
      'TEMPORAL SEQUENCE': 'TEMPORAL',
  }; 
  const [newLabel, setNewLabel] = useState('');
  const handleAddNewLabel = () => {
      const trimmed = newLabel.trim();
      if (!trimmed || annotationOptions[trimmed]) return;
    
      const updatedOptions = { ...annotationOptions, [trimmed]: trimmed };
      const updatedColors = { ...optionColors, [trimmed]: `hsl(${Math.floor(Math.random() * 360)}, 50%, 85%)` };
    
      setAnnotationOptions(updatedOptions);
      setOptionColors(updatedColors);
      setActiveLabelFilters([...activeLabelFilters, trimmed]);
      setNewLabel('');
  };
    
  const normalizeLabel = (label: string): string =>
  labelNormalizer[label.toUpperCase()] || label.toUpperCase();

  const sortedAnnotations = useMemo(() => {
      const filtered = doc.annotations
        .filter((a) =>
          userRole === "Adjudicator"
            ? a.note.includes("SME") || a.note.includes("Adjudicator")            
            : a.note.includes(userRole)
        )
        .map((a) => ({
          ...a,
          label: normalizeLabel(a.label),
        }));
    
      return filtered.sort((a, b) => (a.textContext.start ?? 0) - (b.textContext.start ?? 0));
  }, [doc.annotations, userRole]);

  const sortedAnnotations_right = useMemo(() => {
    const filtered = doc.annotations
      .filter((a) =>
        a.note.includes(selectedAISet)
      )
      .map((a) => ({
        ...a,
        label: normalizeLabel(a.label),
      }));
  
    return filtered.sort((a, b) => (a.textContext.start ?? 0) - (b.textContext.start ?? 0));
}, [doc.annotations, selectedAISet]);

  const aiAnnotations = useMemo(() =>
      doc.annotations
        .filter((a) => a.note.includes(selectedAISet)) // "LLM" or "ETHER"
        .map((a) => ({ ...a, label: normalizeLabel(a.label) }))
        .sort((a, b) => (a.textContext.start ?? 0) - (b.textContext.start ?? 0)),
  [doc.annotations, selectedAISet]);

  // Function to save the current state
  const handleSave = async (shouldClose = false) => {
      const baseNameCandidate = saveAsName || doc.saveFileName || `case-${Date.now()}`;
      const sanitizedBase = baseNameCandidate.trim().replace(/\.json$/i, '') || `case-${Date.now()}`;
      const fileName = `${sanitizedBase}.json`;
      const folder = overrideFolder ?? 'Playground';

      try {
        await saveAnnotationsToDb({
          fileName,
          curr_folder: folder,
          pages: doc.pages,
          annotations: doc.annotations,
          meta: doc.meta,
        });

        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 3000);
        setSaveAsName('');

        if (shouldClose) {
          window.close();
        }
      } catch (error: any) {
        const message = error?.message || 'Unknown error';
        alert(`❌ Failed to save annotations: ${message}`);
      }
  };


  const handleExtendMatch = (baseAnnotation: Annotation) => {
      const baseText = baseAnnotation.textContext.text.trim();
      const baseLabel = baseAnnotation.label;
      const pageIndex = doc.currentPageIndex;
      const note = `${userRole},EXT`;
      const currentTextBlock = currentPageData as string; // assuming it's plain text now
      const regex = new RegExp(`\\b${escapeRegExp(baseText)}\\b`, 'gi');
    
      let match;
      const newAnnotations: Annotation[] = [];
      while ((match = regex.exec(currentTextBlock)) !== null) {
          const start = match.index;
          const end = start + match[0].length;
          const matchedText = match[0].trim();
        
          const isDuplicate = sortedAnnotations.some(
            (a) =>
              a.textContext.page === pageIndex &&
              a.textContext.start === start &&
              a.textContext.end === end &&
              a.label === baseLabel &&
              !a.note.includes('LLM') &&
              !a.note.includes('ETHER')  
          );
          if (isDuplicate) continue;
        
          newAnnotations.push({
            textContext: {
              text: matchedText,
              page: pageIndex,
              start,
              end,
              disputed: false,
            },
            label: baseLabel,
            note,
            relationships: {
              latency: { text: '', page: 0 },
              date: { text: '', page: 0 },
              time: { text: '', page: 0 },
              frequency: { text: '', page: 0 },
              temporal_sequence: { text: '', page: 0 },
            },
          });
        }

      // Dispatch all new annotations
      newAnnotations.forEach((annotation) =>
        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation } })
      );
    

  };

  const handleDownloadJSON = () => {
    // Create export data with proper structure
    const exportData = {
      pages: doc.pages,
      annotations: doc.annotations,
      meta: doc.meta
    };

    // Create blob and download link
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${doc.saveFileName || 'annotation_data'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };


  const handleExportAdjudication = async () => {
    // Get SME1 and SME2 annotations
    const sme1Annotations = doc.annotations.filter(a => a.note.includes('SME1'));
    const sme2Annotations = doc.annotations.filter(a => a.note.includes('SME2'));

      // Create a new workbook and worksheet
      const workbook = new ExcelJS.Workbook();
      const worksheet = workbook.addWorksheet('Annotations');
  
      // Define columns with headers and widths
      worksheet.columns = [
          { header: 'Start', key: 'start', width: 10 },
          { header: 'End', key: 'end', width: 10 },
          { header: 'SME1 Label', key: 'sme1Label', width: 15 },
          { header: 'SME2 Label', key: 'sme2Label', width: 15 },
          { header: 'SME1 Note', key: 'sme1Note', width: 20 },
          { header: 'SME2 Note', key: 'sme2Note', width: 20 },
          { header: 'SME1 Text', key: 'sme1Text', width: 20 },
          { header: 'SME2 Text', key: 'sme2Text', width: 20 },
          { header: 'Context', key: 'context', width: 50 },
          { header: 'Label Consistency', key: 'labelConsistency', width: 15 },
          { header: 'Span Consistency', key: 'spanConsistency', width: 15 }
      ];
  
      // Style the header row
      worksheet.getRow(1).font = { bold: true };
      worksheet.getRow(1).fill = {
          type: 'pattern',
          pattern: 'solid',
          fgColor: { argb: 'FFE0E0E0' } // Light gray background
      };
  
      // Add SME1 annotations data
      sme1Annotations.forEach(annotation => {
          const start = annotation.textContext.start;
          const end = annotation.textContext.end;
          const sme1Label = annotation.label;
          const sme1Note = annotation.note;
          const sme1Text = annotation.textContext.text;
  

          const context = generateHighlightedContext(
            doc.pages[annotation.textContext.page], 
            start as number, 
            end as number
          );
          
          const sme2Annotation = sme2Annotations.find(a => 
              Math.max((start as number), (a.textContext.start as number)) <= 
              Math.min((end as number), (a.textContext.end as number))
          );
          
          const sme2Label = sme2Annotation ? sme2Annotation.label : '';
          const sme2Note = sme2Annotation ? sme2Annotation.note : 'Missing';
          const sme2Text = sme2Annotation ? sme2Annotation.textContext.text : '';
          
          const labelConsistency = sme2Annotation ? 
              (sme2Label === sme1Label ? 'Match' : 'Mismatch') : '';
          const spanConsistency = sme2Annotation ? 
              (start === sme2Annotation.textContext.start && 
               end === sme2Annotation.textContext.end ? 'Match' : 'Mismatch') : 'Missing';

          const row = worksheet.addRow({
              start, 
              end, 
              sme1Label, 
              sme2Label, 
              sme1Note, 
              sme2Note, 
              sme1Text, 
              sme2Text, 
              context, 
              labelConsistency,
              spanConsistency
          });

          // Style the consistency cells based on values
          const labelConsistencyCell = row.getCell('labelConsistency');
          if (labelConsistency === 'Match') {
              labelConsistencyCell.font = { color: { argb: 'FF008000' }, bold: true }; // Green
          } else if (labelConsistency === 'Mismatch' || labelConsistency === '') {
              labelConsistencyCell.font = { color: { argb: 'FFFF0000' }, bold: true }; // Red
          }

          const spanConsistencyCell = row.getCell('spanConsistency');
          if (spanConsistency === 'Match') {
              spanConsistencyCell.font = { color: { argb: 'FF008000' }, bold: true }; // Green
          } else if (spanConsistency === 'Mismatch' || spanConsistency === 'Missing') {
              spanConsistencyCell.font = { color: { argb: 'FFFF0000' }, bold: true }; // Red
          }
      });
  
      // Add SME2 annotations that are not in SME1
      sme2Annotations.forEach(annotation => {
          const start = annotation.textContext.start;
          const end = annotation.textContext.end;
          const sme2Note = annotation.note;
          const sme2Label = annotation.label;
          const sme2Text = annotation.textContext.text;
          const context = doc.pages[annotation.textContext.page].slice(
              Math.max(0, (start as number) - 100), 
              (end as number) + 100
          );
          
          const sme1Annotation = sme1Annotations.find(a => 
              Math.max((start as number), (a.textContext.start as number)) <= 
              Math.min((end as number), (a.textContext.end as number))
          );
          
          if (!sme1Annotation) {
              const labelConsistency = '';
              const spanConsistency = 'Missing';
              const sme1Label = '';
              const sme1Note = 'Missing';
              const sme1Text = '';

              const row = worksheet.addRow({
                  start, 
                  end, 
                  sme1Label, 
                  sme2Label, 
                  sme1Note, 
                  sme2Note, 
                  sme1Text, 
                  sme2Text, 
                  context, 
                  labelConsistency,
                  spanConsistency
              });

              // Style the consistency cells
              const labelConsistencyCell = row.getCell('labelConsistency');
              labelConsistencyCell.font = { color: { argb: 'FFFF0000' }, bold: true }; // Red

              const spanConsistencyCell = row.getCell('spanConsistency');
              spanConsistencyCell.font = { color: { argb: 'FFFF0000' }, bold: true }; // Red
          }
      });
  
  
      // Export the workbook
      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${doc.saveFileName || 'data'}_adjudication.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
  };

  const handleExportExcel = async () => {
      // Get all annotations including SME and LLM
      const allAnnotations = doc.annotations;
  
      // Create a new workbook and worksheet
      const workbook = new ExcelJS.Workbook();
      const worksheet = workbook.addWorksheet('Annotations');
  
      // Define columns with headers and widths
      worksheet.columns = [
          { header: 'Start', key: 'start', width: 10 },
          { header: 'End', key: 'end', width: 10 },
          { header: 'Label', key: 'label', width: 15 },
          { header: 'Note', key: 'note', width: 20 },
          { header: 'Text', key: 'text', width: 20 },
          { header: 'Context', key: 'context', width: 50 }
      ];
  
      // Style the header row
      worksheet.getRow(1).font = { bold: true };
      worksheet.getRow(1).fill = {
          type: 'pattern',
          pattern: 'solid',
          fgColor: { argb: 'FFE0E0E0' } // Light gray background
      };
  
      // Add all annotations data
      allAnnotations.forEach(annotation => {
          const start = annotation.textContext.start;
          const end = annotation.textContext.end;
          const label = annotation.label;
          const note = annotation.note;
          const text = annotation.textContext.text;
  
          const context = generateHighlightedContext(
            doc.pages[0], //always use page 0 for now
            start as number, 
            end as number
          );


          const row = worksheet.addRow({
              start, 
              end, 
              label, 
              note, 
              text, 
              context
          });
          const contextCell = row.getCell('context');
          contextCell.value = { richText: context };
      });
  
  
      // Export the workbook
      const buffer = await workbook.xlsx.writeBuffer();
      const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${doc.saveFileName || 'data'}_annotation.xlsx`;
      link.click();
      window.URL.revokeObjectURL(url);
  };

  const handleAddAnnotation = (label: string) => {
      const defaultContext: TextContext = { page: 0, text: '' };
      const newNote = userRole;
    
      const newAnnotation: Annotation = {
        textContext: {
          text: selectedText,
          page: doc.currentPageIndex,
          disputed: false,
          start: unifiedContextMenu.start as number,
          end: unifiedContextMenu.end as number,
        },
        label,
        note: newNote,
        relationships: {
          latency: defaultContext,
          date: defaultContext,
          time: defaultContext,
          frequency: defaultContext,
          temporal_sequence: defaultContext,
        },
      };
    
      dispatch({
        type: DocActionTypes.ADD_ANNOTATION,
        payload: { annotation: newAnnotation },
      });
    
      setUnifiedContextMenu({
        visible: false,
        x: 0,
        y: 0,
        type: 'annotation', // or keep the last type if needed
      });
      setSelectedTermContext(null);
  };


  const removeAnnotation = (annotation: Annotation) => {
      dispatch({
        type: DocActionTypes.REMOVE_ANNOTATION,
        payload: { annotation },
      });
      setSelectedTermContext(null); 
  };

  const handleTextSelection = () => {
      const selection = window.getSelection();
      if (!isUserSet || !selection || !selection.toString().trim()) return;
    
      const text = selection.toString().trim();
      const range = selection.getRangeAt(0);
      const startNode = range.startContainer;
      const startOffset = range.startOffset;
    
      const container = document.querySelector('.page .text-block');
      if (!container?.contains(startNode)) {
        console.log('Selection is outside of the container.');
        return;
      }
    
      if (
        startNode.nodeType === Node.ELEMENT_NODE &&
        (startNode as Element).closest('span')
      ) {
        console.log('Selection started inside an annotated span. Aborting.');
        return;
      }
    
      const rect = range.getBoundingClientRect();
      const menuX = rect.left + window.scrollX;
      const menuY = Math.min(
        rect.top + window.scrollY,
        window.scrollY + window.innerHeight - 160
      );
    
      // ✅ Correct offset calculation using full clean text
      const tempRange = document.createRange();
      tempRange.selectNodeContents(container);
      tempRange.setEnd(startNode, startOffset);
      const prefixText = tempRange.cloneContents().textContent || "";
      const absoluteStart = prefixText.length;
      const absoluteEnd = absoluteStart + text.length;
    
      setSelectedText(text);
    
      const pageAnnotations = sortedAnnotations.filter(
        (a) => a.textContext.page === doc.currentPageIndex
      );
    
      let existingAnn = false;
    
      // ✅ Allow overlaps in relationshipBuilderMode
      if (!relationshipBuilderMode) {
        for (const a of pageAnnotations) {
          const start = a.textContext.start as number;
          const end = a.textContext.end as number;
    
          if (absoluteStart >= start && absoluteEnd <= end) {
            setInspectedAnnotation(a);
            existingAnn = true;
            break;
          }
        }
      }
    
      if (verificationMode) {
        // do nothing
      } else if (!relationshipBuilderMode) {
        setUnifiedContextMenu({
          visible: true,
          x: menuX,
          y: menuY,
          type: 'annotation', 
          start: absoluteStart,
          end: absoluteEnd
        });
      } else if (currentAnnotationRelation) {
        const existingRelationship = currentAnnotationRelation.relationships[
            currentRelationType as keyof Annotation['relationships']
          ]?.text;
        
          setUnifiedContextMenu({
            visible: true,
            x: menuX,
            y: menuY,
            type: 'relationship',
            start: absoluteStart,
            end: absoluteEnd,
            options: existingRelationship === '' ? ['Set'] : ['Set', 'Delete'],
          });
      }
  };

  const handleAddRelationship = (option: string) => {
      const text = selectedText;
      const page = doc.currentPageIndex;
      const start = unifiedContextMenu.start as number;
      const end = unifiedContextMenu.end as number;
    
      const relationshipContext: TextContext = { text, page, start, end };
    
      if (option === "Set") {
        dispatch({
          type: DocActionTypes.ADD_RELATION,
          payload: {
            annotation: currentAnnotationRelation as Annotation,
            relation: currentRelationType,
            context: relationshipContext,
          },
        });
      } else if (option === "Delete") {
        dispatch({
          type: DocActionTypes.ADD_RELATION,
          payload: {
            annotation: currentAnnotationRelation as Annotation,
            relation: currentRelationType,
            context: { text: '', page: 0 },
          },
        });
      }
    
      setUnifiedContextMenu({
        visible: false,
        x: 0,
        y: 0,
        type: 'relationship',
      });
  };


  const handleBuildRelationship = (forceExit: boolean = false) => {
      if (forceExit) {
        setRelationshipBuilderMode(false);
        setCurrentAnnotationRelation(null);
        setCurrentRelationType('');
        setUnifiedContextMenu({
          visible: false,
          x: 0,
          y: 0,
          type: 'relationship',
        });
      } else {
        setRelationshipBuilderMode(true);
        setCurrentAnnotationRelation(null);
        setCurrentRelationType('');
      }
  };

  const handleSelectRelationCell = (annotation: Annotation, relationshipType: keyof AnnotationRelationships) => {
    // Convert legacy data if needed.
    if (relationshipType == "latency" && annotation.relationships.latency?.text == "") {
      annotation.relationships.span && 
      dispatch({
        type:  DocActionTypes.ADD_RELATION  ,
        payload: { annotation: annotation, relation: relationshipType, context: annotation.relationships.span}
      });
    };
    if (relationshipType == "temporal_sequence" && annotation.relationships.temporal_sequence?.text == "") {
      annotation.relationships.frequency && 
      dispatch({
        type:  DocActionTypes.ADD_RELATION  ,
        payload: { annotation: annotation, relation: relationshipType, context: annotation.relationships.frequency}
      });
    };
    
    if (relationshipBuilderMode) {
      setCurrentAnnotationRelation(annotation);
      setCurrentRelationType(relationshipType)
    };
  }



  const handleLLMAnnotationClick = (text: string, start: number, end: number, x: number, y: number) => {
    const llmMatch = doc.annotations.find(
      (a) =>
        a.textContext.text === text &&
        a.textContext.start === start &&
        a.textContext.end === end
    );
    if (userRole === "Adjudicator") {
      if (llmMatch?.note?.includes(userRole)) {
        return;
      }
    
      const prefillLabel = llmMatch?.label?.toUpperCase() || ''; // Blank if not found
    
      setLlmPopup({ visible: true, x, y, text, start, end });
      setSelectedPopupLabel(prefillLabel); // Always set selected label
    } else {
      const defaultContext: TextContext = { page: 0, text: '' };

      const label = llmMatch?.label?.toUpperCase() || ''; // Blank if not found
    
      // Check if annotation already exists for this term with same label and userRole(LLM)
      const existingAnnotation = doc.annotations.find(
        (a) =>
          a.textContext.text === text &&
          a.textContext.start === start &&
          a.textContext.end === end &&
          a.label === label &&
          a.note === userRole + '(LLM)'
      );
    
      if (existingAnnotation) {
        // If exists, remove it
        dispatch({ type: DocActionTypes.REMOVE_ANNOTATION, payload: { annotation: existingAnnotation } });
      } else {
        // If not exists, add new annotation
        const newAnnotation: Annotation = {
          textContext: {
            text,
            start,
            end,
            page: doc.currentPageIndex,
            disputed: false,
          },
          label,
          note: userRole + '(LLM)',
          relationships: {
            latency: defaultContext,
            date: defaultContext,
            time: defaultContext,
            frequency: defaultContext,
            temporal_sequence: defaultContext,
          },
        };
        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation } });
      }
    }
  };

  const handleLlmAddAnnotation = () => {
      const defaultContext: TextContext = { page: doc.currentPageIndex, text: '' };
      const { start, end, text } = llmPopup;
      const label = selectedPopupLabel;
    
      const existing = doc.annotations.find(
        (a) =>
          a.textContext.start === start &&
          a.textContext.end === end &&
          a.textContext.text === text 
      );
    
      let actionType = DocActionTypes.ADD_ANNOTATION;
      let finalNote = `${userRole},${selectedSet}`;
      let finalLabel = label;
    
      if (existing) {
        const isSameUser = existing.note === userRole;
        const isKeyword = existing.note === 'Keyword';
    
        if (isSameUser || isKeyword) {
          // Update the note if it was a placeholder
          finalNote = isKeyword ? userRole : existing.note;
    
          // Merge labels
          const existingLabels = existing.label.split(',').map((l) => l.trim());
          const labelSet = new Set([...existingLabels, label]);
          finalLabel = Array.from(labelSet).join(', ');
    
          actionType = DocActionTypes.UPDATE_ANNOTATION;
        } else {
          // Belongs to another userRole — keep as ADD_ANNOTATION with default note/label
          finalNote = `${userRole},${selectedSet}`;
          finalLabel = label;
        }
      }
    
      const newAnnotation: Annotation = {
        textContext: {
          text,
          start,
          end,
          page: doc.currentPageIndex,
          disputed: false,
        },
        label: finalLabel,
        note: finalNote,
        relationships: {
          latency: defaultContext,
          date: defaultContext,
          time: defaultContext,
          frequency: defaultContext,
          temporal_sequence: defaultContext,
        },
      };
    
      dispatch({ type: actionType, payload: { annotation: newAnnotation } });
      setLlmPopup((prev) => ({ ...prev, visible: false }));
  };

  const prevSetRef = useRef<string | null>(null);

  const handleMetaPanelTextSelection = () => {
      const selection = window.getSelection();
      const text = selection?.toString().trim();
    
      if (!text) return;
    
      // Just set the text — don't try to match it in currentPageData!
      setSelectedTermContext({ text, start: 0, end: 0 });  // start/end are placeholders
  };

  const updateAnnotationNote = (
    start: number,
    end: number,
    text: string,
    label: string,
    addNote: string,
  ) => {
    const target = sortedAnnotations.find(
      (a) =>
        a.textContext.start === start &&
        a.textContext.end === end &&
        a.textContext.text === text &&
        a.label === label &&
        !a.note?.includes('LLM')
    );
  
    if (!target) return;
  
    // Split existing notes and new notes
    const existingNotes = (target.note || "")
      .split(",")
      .map((n) => n.trim())
      .filter((n) => n);

    const newNotes = addNote
      .split(",")
      .map((n) => n.trim())
      .filter((n) => n);
  
    // Combine existing and new notes, ensuring uniqueness
    const noteSet = new Set([...existingNotes, ...newNotes]);
  
    // Remove 'WARN' if 'verified' is being added
    if (newNotes.includes('verified')) {
      noteSet.delete('WARN');
    }
  
    const updatedAnnotation = {
      ...target,
      note: Array.from(noteSet).join(", "),
    };
  
    dispatch({
      type: DocActionTypes.UPDATE_ANNOTATION,
      payload: {
        annotation: updatedAnnotation,
      },
    });

  };



  const generateHighlightedContext = (text: string | undefined, start: number, end: number) => {
    if (!text) return [];
    
    const contextStart = Math.max(0, start - 100);
    const contextEnd = end + 100;
    
    const richText: ExcelJS.RichText[] = [];
    
    // Add prefix text
    richText.push({
      text: text.slice(contextStart, start)
    });
    
    // Add highlighted term
    richText.push({
      text: text.slice(start, end),
      font: { bold: true }
    });
    
    // Add suffix text
    richText.push({
      text: text.slice(end, contextEnd)
    });
    
    return richText;
  };
  
  useEffect(() => {
      const smeLabels = new Set<string>(
        ['DRUG', 'SDRUG', 'CDRUG', 'DOSE', 'LAB', 'TREATMENT', 'DISPOSITION',
          'AE', 'MAE', 'CAUSE OF DEATH', 'DIAGNOSTIC', 'STATUS', 
          'MEDICAL HISTORY', 'IND', 'FAMILY HISTORY', 'TEMPORAL', 'AGE', 'SEX', 
        ]);
    
      doc.annotations.forEach((a) => {
          const upperLabel = normalizeLabel(a.label.trim());

          if (a.note.includes("ETHER")) {
            return; 
          } else {
            smeLabels.add(upperLabel);
          }
      });
    
      const allLabelsArray = [...new Set([...smeLabels])].sort();
      
      // 🔁 Always reset options/colors on annotation set change
      const newOptions = Object.fromEntries(allLabelsArray.map((label) => [label, label]));
      setAnnotationOptions(newOptions);
      setOptionColors(generateOptionColors(allLabelsArray));
      prevSetRef.current = selectedSet;
      
  }, [doc.annotations, selectedSet]);

  useEffect(() => {
    if (overrideFileName && overrideFolder) {
      getHistoryFile(overrideFileName, overrideFolder)
        .then((data) => {
          if (!data) return;
          dispatch({
            type: DocActionTypes.LOAD,
            payload: {
              pages: data.pages || [],
              annotations: data.annotations || [],
              meta: data.meta || {},  
              fileName: overrideFileName
            },
          });
        });
    }
  }, [overrideFileName, overrideFolder]);
  
  const demographicKeys = [
    "Attachments Info-Link", "Age in Years", "Sex",
    "Weight In kg", "Medical History and Comments", "Reporter Qualifications", "Health Professional", "All Lab Tests",
    "Confirmatory Test Comments", "Seriousness", "All Outcomes"
  ];

  const defaultLabelOrder = ['DRUG', 'SDRUG', 'CDRUG', 'DOSE', 'LAB', 'TREATMENT', 'DISPOSITION', 
    'AE', 'MAE', 'CAUSE OF DEATH', 'DIAGNOSTIC', 'STATUS', 
    'MEDICAL HISTORY', 'IND', 'FAMILY HISTORY', 'TEMPORAL', 'AGE', 'SEX', 
  ];

  return (
      <div className="app-container">
        {/* Side Panel for Annotations */}
        {!relationshipBuilderMode && (
            <AnnotationPanel
              annotations={sortedAnnotations}
              annotationOptions={annotationOptions}
              setAnnotationOptions={setAnnotationOptions}
              optionColors={optionColors}
              setOptionColors={setOptionColors}
              handleRemoveAnnotation={removeAnnotation}
              activeLabelFilters={activeLabelFilters}
              setActiveLabelFilters={setActiveLabelFilters}
              selectedTermContext={selectedTermContext}
              setSelectedTermContext={setSelectedTermContext}
              handleExtendMatch={handleExtendMatch}  
            />
        )}
          
        {/* Main Display Panel */}
        <div className="main-panel">
          {/* Only reveal UI when valid document is available */}
          {currentPageData && (
            <div className={`page-container ${relationshipBuilderMode ? 'flex-row' : 'flex-col'}`}>
              {relationshipBuilderMode ? (
                <>
                  <div style={{ flex: 1, paddingRight: '4px' }}>
                    <div style={{ textAlign: 'left', padding: '8px' }}>
                        <button className="toggle-btn" onClick={() => handleBuildRelationship(true)}>
                          ← Back
                        </button>
                    </div>  
                    <p style={{ textAlign: 'center' }}>
                      Select a cell in the table to edit then select context from the document.
                    </p>
                    <RelationshipBuilderPanel
                      annotations={sortedAnnotations}
                      handleSelectCell={handleSelectRelationCell}
                      currentAnnotation={currentAnnotationRelation}
                      currentRelationshipType={currentRelationType}
                    />
                  </div>
    
                  <div className="sme-panel text-display-panel-col">
                    <PageDisplayBuilder
                      annotations={sortedAnnotations}
                      currentPage={doc.currentPageIndex}
                      pageData={currentPageData}
                      currentAnnotationRelation={currentAnnotationRelation}
                      optionColors={optionColors}
                      handleTextSelection={handleTextSelection}
                      userRole = {userRole}  
                    />
                  </div>
                </>
              ) : (
                <>
                  <div className="page-center-column w-full">
                    {/* Top Action Banner */}
                    <div className="flex items-center justify-between px-6 py-3 bg-white border-b border-gray-200 shadow-sm">
                      <div className="flex items-center gap-6">
                        <div className="flex flex-col">
                          <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Project / File</span>
                          <h2 className="text-lg font-bold text-gray-800 truncate max-w-lg">
                            {overrideFolder} / {overrideFileName || doc.saveFileName}
                          </h2>
                        </div>

                        <button
                          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all duration-200 ${
                            relationshipBuilderMode 
                              ? 'bg-blue-600 text-white shadow-md' 
                              : 'bg-white text-blue-600 border border-blue-200 hover:bg-blue-50'
                          }`}
                          onClick={() => handleBuildRelationship(relationshipBuilderMode)}
                          disabled={!isUserSet}
                        >
                          {relationshipBuilderMode ? '✓ Relationship Mode' : '⛓ Relationship Mode'}
                        </button>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="flex items-center bg-gray-100 rounded-lg p-1 mr-2">
                          <button
                            onClick={() => handleSave(false)}
                            className="px-4 py-1.5 rounded-md text-sm font-bold text-gray-700 hover:bg-white hover:shadow-sm transition-all"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => handleSave(true)}
                            className="px-4 py-1.5 rounded-md text-sm font-bold text-indigo-700 hover:bg-white hover:shadow-sm transition-all"
                          >
                            Save & Close
                          </button>
                        </div>

                        <div className="relative">
                          <button
                            onClick={() => setIsExportDropdownOpen(!isExportDropdownOpen)}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-bold shadow-sm transition-all"
                          >
                            Export ▾
                          </button>
                          {isExportDropdownOpen && (
                            <div className="absolute right-0 mt-2 w-64 bg-white rounded-xl shadow-xl py-2 z-50 border border-gray-100 animate-in fade-in slide-in-from-top-2">
                              <button
                                onClick={handleDownloadJSON}
                                className="block w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                              >
                                📄 Download Raw JSON
                              </button>
                              <button
                                onClick={handleExportExcel}
                                className="block w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                              >
                                📊 Export Annotations (Excel)
                              </button>
                              <button
                                onClick={handleExportAdjudication}
                                className="block w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                              >
                                ⚖️ Export Adjudication (Excel)
                              </button>
                            </div>
                          )}
                        </div>

                        <button
                          onClick={() => window.close()}
                          className="bg-gray-800 hover:bg-black text-white px-4 py-2 rounded-lg text-sm font-bold transition-all"
                        >
                          Exit
                        </button>
                      </div>
                    </div>

                    {/* Filter Bar */}
                    <div className="px-6 py-2 bg-gray-50 border-b border-gray-200">
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div className="flex flex-wrap gap-x-4 gap-y-2 items-center">
                          <span className="text-xs font-bold text-gray-500 uppercase mr-2">Filters:</span>
                          {Object.entries(annotationOptions)
                            .sort(([a], [b]) => {
                              const indexA = defaultLabelOrder.indexOf(a.toUpperCase());
                              const indexB = defaultLabelOrder.indexOf(b.toUpperCase());
                              if (indexA === -1 && indexB === -1) return a.localeCompare(b);
                              if (indexA === -1) return 1;
                              if (indexB === -1) return -1;
                              return indexA - indexB;
                            })
                            .map(([label, _]: [string, string]) => {
                              const isChecked = activeLabelFilters.includes(label);
                              const color = optionColors[label] || 'lightgray';
                              return (
                                <label key={label} className="flex items-center gap-1.5 text-xs font-bold cursor-pointer group">
                                  <input
                                    type="checkbox"
                                    checked={isChecked}
                                    onChange={() => {
                                      const updated = isChecked
                                        ? activeLabelFilters.filter((l) => l !== label)
                                        : [...activeLabelFilters, label];
                                      setActiveLabelFilters(updated);
                                    }}
                                    className="hidden"
                                  />
                                  <div 
                                    className={`w-3.5 h-3.5 rounded-full border transition-all ${isChecked ? 'ring-2 ring-offset-1 ring-blue-400 scale-110' : 'opacity-40 group-hover:opacity-70'}`}
                                    style={{ backgroundColor: color, borderColor: isChecked ? 'white' : 'rgba(0,0,0,0.1)' }}
                                  ></div>
                                  <span className={isChecked ? 'text-gray-900' : 'text-gray-400 group-hover:text-gray-600'}>
                                    {labelNormalizer[label.toUpperCase()] || label.toUpperCase()}
                                  </span>
                                </label>
                              );
                            })}
                        </div>
                    
                        <div className="flex items-center gap-4">
                          <button
                            onClick={() => {
                              const allSelected = Object.keys(annotationOptions).every(label => activeLabelFilters.includes(label));
                              setActiveLabelFilters(allSelected ? [] : Object.keys(annotationOptions));
                            }}
                            className="text-[10px] uppercase font-black text-blue-600 hover:text-blue-800"
                          >
                            {Object.keys(annotationOptions).every(label => activeLabelFilters.includes(label)) ? "Clear All" : "Select All"}
                          </button>
                    
                          <div className="flex items-center gap-2 bg-white px-2 py-1 rounded-md border border-gray-200">
                            <input
                              type="text"
                              value={newLabel}
                              onChange={(e) => setNewLabel(e.target.value)}
                              onKeyDown={(e) => e.key === 'Enter' && handleAddNewLabel()}
                              placeholder="Add type..."
                              className="text-[11px] font-bold outline-none bg-transparent w-20"
                            />
                            <button onClick={handleAddNewLabel} className="text-blue-600 font-bold text-xs">+</button>
                          </div>

                          {selectedTermContext?.text && (
                            <div className="flex items-center gap-2 bg-yellow-100 px-2 py-1 rounded border border-yellow-200">
                              <span className="text-[10px] font-bold text-yellow-800 truncate max-w-[100px]">
                                {selectedTermContext.text}
                              </span>
                              <button onClick={() => setSelectedTermContext(null)} className="text-yellow-600 font-bold text-xs">✕</button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  <div
                    onClick={() => setShowRightPanel(!showRightPanel)}
                    className="absolute top-1/2 transform -translate-y-1/2 bg-lime-100 hover:bg-lime-200 text-gray-600 hover:text-black border-l border-gray-300 cursor-pointer"
                    style={{
                      right: 0,
                      width: '30px',
                      height: '120px',
                      fontSize: '1rem',
                      margin: '10px',
                      writingMode: 'vertical-rl',
                      textOrientation: 'mixed',
                      fontWeight: 500,
                      userSelect: 'none',
                    }}
                    title={showRightPanel ? 'Hide AI Panel' : 'Show AI Panel'}
                  >
                    {showRightPanel ? 'Hide AI Panel' : 'Show AI Panel'}
                  </div>          
                  {/* Headers */}
                  <div className="flex w-full sticky top-0 z-20">
                    {/* SME Header */}
                    <div className="w-1/2 pr-2">
                      <div className="text-header gap-4 items-center bg-indigo-50 p-2 shadow-md">
                        <h3 className="font-semibold text-gray-800 text-lg">SME Annotation</h3>
                        
                        {verificationMode && (
                          <div className="text-green-700 font-medium text-sm">✅ Verification Mode Active</div>
                        )}
                        
                        {/* Role Selector */}
                        <select
                          id="role"
                          className="text-sm font-semibold bg-indigo-100 border border-indigo-400 text-indigo-800 rounded px-3 py-2 shadow-sm hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          value={userRole}
                          onChange={(e) => {
                            const role = e.target.value as "SME1" | "SME2" | "Adjudicator";
                            setUserRole(role);
                            setVerificationMode(role === "Adjudicator");
                          }}
                        >
                          <option value="SME1">SME1</option>
                          <option value="SME2">SME2</option>
                          <option value="Adjudicator">Adjudicator</option>
                        </select>
                      </div>
                    </div>

                    {/* AI Header */}
                    {showRightPanel && (
                      <div className="w-1/2 pl-2">
                        <div className="text-header gap-4 items-center bg-lime-50 p-2 shadow-md">
                          <h3 className="font-semibold text-gray-800 text-lg">Metadata/AI Annotation</h3>
                          {/* <p className="text-sm text-gray-600">Click to verify</p> */}
                          <select
                            value={selectedAISet}
                            onChange={(e) => setSelectedAISet(e.target.value)}
                            className="text-sm font-semibold bg-lime-100 border border-lime-400 text-lime-800 rounded px-3 py-2 shadow-sm hover:bg-lime-200 focus:outline-none focus:ring-2 focus:ring-lime-500"
                          >
                            <optgroup label="Metadata Views">
                              <option value="demographic">Demographic</option>
                              <option value="products">Products</option>
                              <option value="outcomes">Outcomes</option>
                            </optgroup>
                            <optgroup label="AI Annotations">
                              <option value="LLM">AI - Llama 4</option>
                            </optgroup>
                            <optgroup label="SME Annotations">
                              <option value="SME1">SME1</option>
                              <option value="SME2">SME2</option>
                            </optgroup>
                          </select>
                        </div>
                        <p className="italic text-sm text-lime-600">Click AI annotation to add it to SME panel</p>
                      </div>
                    )}
                  </div>                  
                  <div className="text-display-panel flex flex-col items-start w-full mx-auto">
                    {/* Content */}
                    <div className="flex w-full">
                      {/* SME Content */}
                      <div className="sme-panel text-display-panel-col w-1/2 pr-2">
                        <PageDisplay
                          annotations={sortedAnnotations}
                          updateAnnotationNote={updateAnnotationNote}
                          userRole={userRole}
                          currentPage={doc.currentPageIndex}
                          pageData={currentPageData}
                          optionColors={optionColors}
                          handleTextSelection={handleTextSelection}
                          activeLabelFilters={activeLabelFilters}
                          disableFilter={false} 
                          annotationSet="SME"
                          onClickAnnotation={handleLLMAnnotationClick}
                          selectedTermContext={selectedTermContext}
                          setSelectedTermContext={setSelectedTermContext}
                        />
                      </div>

                      {/* AI Content */}
                      {showRightPanel && (
                        <div className="ai-panel text-display-panel-col w-1/2 relative pl-2">
                          {['LLM', 'ETHER'].includes(selectedAISet) ? (
                            <PageDisplay
                              annotations={aiAnnotations}
                              updateAnnotationNote={() => {}}
                              userRole={'AI'}
                              currentPage={doc.currentPageIndex}
                              pageData={currentPageData}
                              optionColors={optionColors}
                              handleTextSelection={() => {}}
                              activeLabelFilters={activeLabelFilters}
                              disableFilter={false}
                              annotationSet={selectedAISet}
                              onClickAnnotation={handleLLMAnnotationClick}
                              selectedTermContext={null}
                              setSelectedTermContext={() => {}}
                            />
                          ) : ['SME1', 'SME2'].includes(selectedAISet) ? (
                            <PageDisplay
                              annotations={sortedAnnotations_right}
                              updateAnnotationNote={updateAnnotationNote}
                              userRole={selectedAISet}
                              currentPage={doc.currentPageIndex}
                              pageData={currentPageData}
                              optionColors={optionColors}
                              handleTextSelection={handleTextSelection}
                              activeLabelFilters={activeLabelFilters}
                              disableFilter={false} 
                              annotationSet="SME"
                              onClickAnnotation={handleLLMAnnotationClick}
                              selectedTermContext={selectedTermContext}
                              setSelectedTermContext={setSelectedTermContext}
                            />
                          ) : (
                            <div
                              className="p-6 text-sm leading-relaxed bg-gray-50 rounded-lg shadow-inner border border-gray-200"
                              onMouseUp={handleMetaPanelTextSelection}
                            >
                              {doc.meta?.[selectedAISet.toLowerCase()]
                                ? (() => {
                                    const content = doc.meta[selectedAISet.toLowerCase()];
                                    return typeof content === 'string' ? (
                                      <div
                                        className="prose prose-sm max-w-none"
                                        dangerouslySetInnerHTML={{ __html: content }}
                                      />
                                    ) : (
                                      <div className="text-gray-500 italic">No structured content found.</div>
                                    );
                                  })()
                                : <div className="text-gray-500 italic">No content available.</div>}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                </>
              )}
            </div>
          )}
        </div>
          
        {unifiedContextMenu.visible && (
          <UnifiedContextMenuDisplay
            contextMenu={unifiedContextMenu}
            annotationOptions={annotationOptions}
            optionColors={optionColors}
            addAnnotation={handleAddAnnotation}
            handleAddRelationship={handleAddRelationship}
            closeContextMenu={() =>
              setUnifiedContextMenu((prev) => ({ ...prev, visible: false }))
            }
          />
        )}

        <LLMAnnotationPopup
          x={llmPopup.x}
          y={llmPopup.y}
          visible={llmPopup.visible}
          text={llmPopup.text}
          annotationOptions={annotationOptions}
          selectedLabel={selectedPopupLabel}
          onChangeLabel={setSelectedPopupLabel}
          onAdd={handleLlmAddAnnotation}
          onClose={() => setLlmPopup((prev) => ({ ...prev, visible: false }))}
        />
          
      </div>
  );
};
