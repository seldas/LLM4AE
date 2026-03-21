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
import ActionHistoryPanel from '../components/action-history-panel';

import '../globals.css';

interface Props {
  overrideFileName?: string;
  overrideFolder?: string;
}

export default function Annotate_Panel({ overrideFileName, overrideFolder}: Props) {
  const [doc, dispatch] = useReducer(docReducer, initialDocState)
  const [selectedText, setSelectedText] = useState('');

  const labelNormalizer: Record<string, string> = {
    'R/O': 'DIAGNOSTIC',
    'BSYM': 'MEDICAL HISTORY',
    'TEMPO': 'TEMPORAL',
    'DATE': 'TEMPORAL',
    'TIME': 'TEMPORAL',
    'DURATION': 'TEMPORAL',
    'RELATIVE': 'TEMPORAL',
    'LATENCY': 'TEMPORAL',
    'TEMPORAL SEQUENCE': 'TEMPORAL',
    'COD': 'CAUSE OF DEATH',
    'SYMPTOM': 'AE',
    'SIGN': 'AE',
    'AGE': 'AGE',
    'SEX': 'SEX',
    'GENDER': 'SEX',
  }; 
  
  // Layer Management
  const [activeLayers, setActiveLayers] = useState<string[]>(['SME1', 'AI']); // Default layers
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [userRole, setUserRole] = useState<string>("MJ.L");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [metaView, setMetaView] = useState<'none' | 'demographic' | 'products' | 'outcomes'>('none');

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      const u = JSON.parse(storedUser);
      setCurrentUser(u);
      setIsLoggedIn(true);
      const isGuest = u.username === 'guest';
      setIsReadOnly(isGuest);
      const role = u.migration_key || u.username;
      setUserRole(role);
      
      if (role === 'SME2') setActiveLayers(['SME2', 'AI']);
      else if (role === 'ADJUDICATOR') setActiveLayers(['SME1', 'SME2', 'AI', 'ADJ']);
    }
  }, []);

  const [relationshipBuilderMode, setRelationshipBuilderMode] = useState(false);
  const [currentAnnotationRelation, setCurrentAnnotationRelation] = useState<Annotation | null>(null);
  const [currentRelationType, setCurrentRelationType] = useState<keyof AnnotationRelationships | ''>('');
  
  const [annotationOptions, setAnnotationOptions] = useState<AnnotationOptions>({});
  const [optionColors, setOptionColors] = useState<{ [key: string]: string }>({});
  const [activeLabelFilters, setActiveLabelFilters] = useState<string[]>([]);
  const [showRejected, setShowRejected] = useState(false);
  
  const [unifiedContextMenu, setUnifiedContextMenu] = useState<{
          visible: boolean; x: number; y: number;
          type: 'annotation' | 'relationship' | 'verification';
          options?: string[]; start?: number; end?: number;
        }>({ visible: false, x: 0, y: 0, type: 'annotation' });

  const [selectedPopupLabel, setSelectedPopupLabel] = useState('');
  const [selectedTermContext, setSelectedTermContext] = useState<{ text: string; start: number; end: number } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showFinishConfirm, setShowFinishConfirm] = useState(false);
  
  const [llmPopup, setLlmPopup] = useState<{ 
    visible: boolean; x: number; y: number; text: string; start: number; end: number; 
    type?: 'AI' | 'SME' | 'NEW'; label?: string; isVerified?: boolean
  }>({ visible: false, x: 0, y: 0, text: '', start: 0, end: 0 });

  const currentPageData = doc.pages[doc.currentPageIndex] || null;

  // Filter Annotations for Display (No forced normalization here anymore)
  const visibleAnnotations = useMemo(() => {
    return doc.annotations.filter(a => {
      const note = a.note.toUpperCase();
      const isRejected = note.includes('REJECTED');
      if (isRejected && !showRejected) return false;

      const isSme1 = (note.includes('SME1') || note.includes('MJ.L')) && activeLayers.includes('SME1');
      const isSme2 = (note.includes('SME2') || note.includes('K.L')) && activeLayers.includes('SME2');
      const isAI = (note.includes('LLM') || note.includes('llama') || note.includes('BERT')) && activeLayers.includes('AI');
      const isAdj = note.includes('ADJUDICATOR') && activeLayers.includes('ADJ');
      
      return isSme1 || isSme2 || isAI || isAdj;
    });
  }, [doc.annotations, activeLayers, showRejected]);

  // Track unsaved changes
  useEffect(() => {
    setHasUnsavedChanges(doc.actionHistory.length > 0);
  }, [doc.actionHistory.length]);

  const handleSave = async (shouldClose = false) => {
      if (isReadOnly) return;
      try {
        await saveAnnotationsToDb({
          fileName: overrideFileName || doc.saveFileName,
          curr_folder: overrideFolder ?? 'Playground',
          pages: doc.pages,
          annotations: doc.annotations,
          meta: doc.meta,
        });
        setSaveSuccess(true);
        dispatch({ type: DocActionTypes.COMMIT_HISTORY });
        setHasUnsavedChanges(false);
        setTimeout(() => setSaveSuccess(false), 2000);
        if (shouldClose) window.close();
      } catch (error: any) {
        alert(`❌ Failed to save: ${error.message}`);
      }
  };

  const handleFinish = () => {
    if (hasUnsavedChanges) {
      setShowFinishConfirm(true);
    } else {
      window.close();
    }
  };

  const handleLayerToggle = (layer: string) => {
    setActiveLayers(prev => 
      prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]
    );
  };

  const handleExport = async () => {
    const workbook = new ExcelJS.Workbook();
    const worksheet = workbook.addWorksheet('Annotations');

    worksheet.columns = [
      { header: 'Text', key: 'text', width: 40 },
      { header: 'Label', key: 'label', width: 20 },
      { header: 'Start', key: 'start', width: 10 },
      { header: 'End', key: 'end', width: 10 },
      { header: 'Page', key: 'page', width: 10 },
      { header: 'Provenance', key: 'note', width: 30 },
    ];

    doc.annotations.forEach(anno => {
      worksheet.addRow({
        text: anno.textContext.text,
        label: anno.label,
        start: anno.textContext.start,
        end: anno.textContext.end,
        page: anno.textContext.page + 1,
        note: anno.note
      });
    });

    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    
    // Construct dynamic filename
    const caseNumber = doc.meta.case_number || doc.meta.caseNumber || overrideFileName?.split('.')[0] || 'Unknown';
    const version = doc.meta.version || 'v1';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    
    anchor.download = `Annotation_${caseNumber}_${version}_${timestamp}.xlsx`;
    anchor.click();
    window.URL.revokeObjectURL(url);
  };

  // Selection Logic
  const handleTextSelection = () => {
      if (isReadOnly) return;
      const selection = window.getSelection();
      if (!selection || !selection.toString().trim()) return;

      const text = selection.toString().trim().replace(/\u00A0/g, ' ');
      const range = selection.getRangeAt(0);      const startNode = range.startContainer;
      const container = document.querySelector('.page .text-block');
      
      if (!container?.contains(startNode)) return;
    
      const rect = range.getBoundingClientRect();
      
      const tempRange = document.createRange();
      tempRange.selectNodeContents(container);
      tempRange.setEnd(startNode, range.startOffset);
      const absoluteStart = (tempRange.cloneContents().textContent || "").length;
      const absoluteEnd = absoluteStart + text.length;
    
      setSelectedText(text);
    
      if (!relationshipBuilderMode) {
        setUnifiedContextMenu({
          visible: true, x: rect.left + window.scrollX, y: rect.top + window.scrollY,
          type: 'annotation', start: absoluteStart, end: absoluteEnd
        });
      } else if (currentAnnotationRelation) {
          setUnifiedContextMenu({
            visible: true, x: rect.left + window.scrollX, y: rect.top + window.scrollY,
            type: 'relationship', start: absoluteStart, end: absoluteEnd,
            options: ['Set', 'Delete']
          });
      }
  };

  const handleAddAnnotation = (label: string) => {
      if (isReadOnly) return;
      const newAnnotation: Annotation = {
        textContext: {
          text: selectedText,
          page: doc.currentPageIndex,
          start: unifiedContextMenu.start as number,
          end: unifiedContextMenu.end as number,
          disputed: false,
        },
        label: label, // Keep original label
        note: userRole,
        relationships: { latency: {text:'',page:0}, date: {text:'',page:0}, time: {text:'',page:0}, frequency: {text:'',page:0}, temporal_sequence: {text:'',page:0} },
      };
      dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation, historyType: 'add' } });
      setUnifiedContextMenu(prev => ({ ...prev, visible: false }));
  };

  const handleVerifyAnnotation = (start: number, end: number, text: string, label: string, note: string) => {
    if (isReadOnly) return;
    // 1. Find and update the existing AI annotation
    const existingAI = doc.annotations.find(a => 
      a.textContext.start === start && 
      a.textContext.end === end && 
      (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) &&
      (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert'))
    );

    if (existingAI) {
      const updatedAI = {
        ...existingAI,
        note: `${existingAI.note} | VERIFIED BY ${userRole}`
      };
      
      // Dispatch UPDATE for AI with 'verify' historyType
      dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAI, historyType: 'verify' } });

      // 2. Create and add the human annotation
      const newHumanAnnotation: Annotation = {
        textContext: {
          text,
          start,
          end,
          page: doc.currentPageIndex,
          disputed: false,
        },
        label: label,
        note: userRole,
        relationships: { latency: {text:'',page:0}, date: {text:'',page:0}, time: {text:'',page:0}, frequency: {text:'',page:0}, temporal_sequence: {text:'',page:0} },
      };

      // Dispatch ADD for human with 'add' historyType
      dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newHumanAnnotation, historyType: 'add' } });
    }
  };

  const handleRejectAnnotation = (start: number, end: number, label: string) => {
    if (isReadOnly) return;
    const existing = doc.annotations.find(a => 
      a.textContext.start === start && 
      a.textContext.end === end && 
      (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase())
    );
    
    if (existing) {
      const updatedAnnotation = {
        ...existing,
        note: `${existing.note} | REJECTED BY ${userRole}`
      };
      dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAnnotation, historyType: 'reject' } });
      setLlmPopup(prev => ({ ...prev, visible: false }));
      setSelectedTermContext(null);
    }
  };

  const handleLlmAddAnnotation = (labelOverride?: string) => {
    if (isReadOnly) return;
    const { start, end, text, type } = llmPopup;
    const label = labelOverride || selectedPopupLabel;
    
    const newAnnotation: Annotation = {
      textContext: {
        text,
        start,
        end,
        page: doc.currentPageIndex,
        disputed: false,
      },
      label: label,
      note: userRole,
      relationships: {
        latency: { text: '', page: 0 },
        date: { text: '', page: 0 },
        time: { text: '', page: 0 },
        frequency: { text: '', page: 0 },
        temporal_sequence: { text: '', page: 0 },
      },
    };
  
    if (type === 'AI') {
      const existingAI = doc.annotations.find(a => 
        a.textContext.start === start && 
        a.textContext.end === end && 
        (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) &&
        (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert'))
      );

      if (existingAI) {
        const updatedAI = {
          ...existingAI,
          note: `${existingAI.note} | VERIFIED BY ${userRole}`
        };
        
        // Separate history entry 1: Verify AI
        dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAI, historyType: 'verify' } });

        // Separate history entry 2: Add Human
        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation, historyType: 'add' } });
      }
    } else {
      dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation, historyType: 'add' } });
    }

    setLlmPopup((prev) => ({ ...prev, visible: false }));
    setSelectedTermContext(null);
  };

  const handleUnverifyAnnotation = (start: number, end: number, label: number | string) => {
    if (isReadOnly) return;
    const labelStr = String(label);
    
    const humanAnno = doc.annotations.find(a => 
      a.textContext.start === start && 
      a.textContext.end === end && 
      (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) &&
      (a.note.toUpperCase().includes('SME') || a.note.toUpperCase().includes('MJ.L') || a.note.toUpperCase().includes('K.L') || a.note.toUpperCase().includes('ADJUDICATOR'))
    );

    const aiAnno = doc.annotations.find(a => 
      a.textContext.start === start && 
      a.textContext.end === end && 
      (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) &&
      (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert')) &&
      a.note.toUpperCase().includes('VERIFIED')
    );

    if (aiAnno) {
      const revertedAiNote = aiAnno.note.split(' | VERIFIED BY')[0];
      const revertedAi = { ...aiAnno, note: revertedAiNote };
      dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: revertedAi } });
      if (humanAnno) {
        dispatch({ type: DocActionTypes.REMOVE_ANNOTATION, payload: { annotation: humanAnno } });
      }
    }
    
    setLlmPopup(prev => ({ ...prev, visible: false }));
    setSelectedTermContext(null);
  };

  const onClickAnnotation = (text: string, start: number, end: number, x: number, y: number, note?: string, label?: string) => {
    let type: 'AI' | 'SME' | 'NEW' = 'NEW';
    let isVerified = false;

    if (note) {
      const upperNote = note.toUpperCase();
      const isAI = upperNote.includes('LLM') || upperNote.includes('AI') || upperNote.includes('LLAMA') || upperNote.includes('BERT');
      const isHuman = upperNote.includes('SME') || upperNote.includes('MJ.L') || upperNote.includes('K.L') || upperNote.includes('ADJUDICATOR');

      if (isAI) {
        type = 'AI';
        isVerified = upperNote.includes('VERIFIED');
      } else if (isHuman) {
        type = 'SME';
      }
    }
    
    setLlmPopup({
      visible: true, x, y, text, start, end, type, label, isVerified
    });
    if (label) setSelectedPopupLabel(label);
  };

  useEffect(() => {
    if (overrideFileName && overrideFolder) {
      getHistoryFile(overrideFileName, overrideFolder).then(data => {
        if (!data) return;
        dispatch({ type: DocActionTypes.LOAD, payload: { ...data, fileName: overrideFileName } });
      });
    }
  }, [overrideFileName, overrideFolder]);

  useEffect(() => {
    const labels = new Set(['DRUG', 'AE', 'MEDICAL HISTORY', 'LAB', 'TEMPORAL', 'AGE', 'SEX', 'COD', 'DIAGNOSTIC']);
    doc.annotations.forEach(a => labels.add(a.label.toUpperCase()));
    
    const arr = Array.from(labels).sort();
    setAnnotationOptions(Object.fromEntries(arr.map(l => [l, l])));
    setOptionColors(generateOptionColors(arr));
    
    // Auto-enable new labels in filter
    setActiveLabelFilters(prev => {
      const newFilters = [...prev];
      let changed = false;
      arr.forEach(l => {
        if (!newFilters.includes(l)) {
          newFilters.push(l);
          changed = true;
        }
      });
      return changed ? newFilters : prev;
    });
  }, [doc.annotations]);

  return (
    <div className="app-container h-screen overflow-hidden flex flex-col bg-gray-100">
      
      {/* 🟢 NEW TOP BANNER */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm z-30">
        <div className="flex items-center gap-6">
          <div>
            <button 
              onClick={handleExport}
              className="group flex items-center gap-2 px-3 py-1.5 bg-gray-50 hover:bg-emerald-50 border border-gray-200 hover:border-emerald-200 rounded-lg transition-all"
            >
              <span className="text-emerald-600 text-sm">📊</span>
              <span className="text-[10px] font-black text-gray-500 group-hover:text-emerald-700 uppercase tracking-widest">Export Excel</span>
            </button>
          </div>

          {/* User Section in Header */}
          <div className="flex items-center gap-2 border-l border-gray-200 pl-4">
            {isLoggedIn && currentUser ? (
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-black text-[10px] border border-indigo-200 shadow-sm uppercase">
                  {(currentUser.full_name || currentUser.username).charAt(0)}
                </div>
                <div>
                   <span className="text-[10px] font-black text-gray-800 block leading-none">
                     {currentUser.username === 'guest' ? 'Anonymous' : (currentUser.full_name || currentUser.username)}
                   </span>
                   <span className="text-[8px] font-bold text-gray-400 uppercase tracking-tighter">
                     {currentUser.username === 'guest' ? 'Guest Access' : 'Active User'}
                   </span>
                </div>
              </div>
            ) : (
              <button 
                onClick={() => setIsLoggedIn(true)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded text-[10px] font-black uppercase shadow-sm transition-all"
              >
                Sign In
              </button>
            )}
          </div>

          {/* Layer Toggles */}
          <div className="flex items-center gap-2 border-l border-gray-200 pl-4">
            <span className="text-[10px] font-bold text-gray-400 uppercase">Layers:</span>
            <div className="flex items-center bg-gray-100 rounded-lg p-0.5 gap-1">
              {['SME1', 'SME2', 'AI', 'ADJ'].map(layer => (
                <button
                  key={layer}
                  onClick={() => handleLayerToggle(layer)}
                  className={`px-2.5 py-1 rounded-md text-[10px] font-black transition-all ${
                    activeLayers.includes(layer) 
                    ? 'bg-white text-blue-600 shadow-sm ring-1 ring-black/5' 
                    : 'text-gray-400 hover:text-gray-600'
                  }`}
                >
                  {layer}
                </button>
              ))}
            </div>
          </div>

          {/* Metadata Toggles */}
          <div className="flex items-center gap-2 border-l border-gray-200 pl-4">
            <span className="text-[10px] font-bold text-gray-400 uppercase">View Data:</span>
            <div className="flex gap-1">
              {['Demographic', 'Products', 'Outcomes'].map(v => (
                <button
                  key={v}
                  onClick={() => setMetaView(metaView === v.toLowerCase() ? 'none' : v.toLowerCase() as any)}
                  className={`px-2 py-1 rounded text-[10px] font-bold border transition-all ${
                    metaView === v.toLowerCase() ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {/* Rejected Toggle */}
          <div className="flex items-center gap-2 border-l border-gray-200 pl-4">
            <span className="text-[10px] font-bold text-gray-400 uppercase">Rejected:</span>
            <button 
              onClick={() => setShowRejected(!showRejected)}
              className={`flex items-center gap-2 px-2 py-1 rounded-lg transition-all ${
                showRejected ? 'bg-red-100 text-red-700 ring-1 ring-red-200' : 'bg-gray-100 text-gray-400'
              }`}
            >
              <div className={`w-3 h-3 rounded-full transition-colors ${showRejected ? 'bg-red-500' : 'bg-gray-300'}`} />
              <span className="text-[10px] font-black uppercase tracking-tighter">Show Rejected AI</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {!isReadOnly && <button onClick={() => handleSave(false)} className="text-xs font-bold text-gray-600 hover:text-black">Save</button>}
          <button onClick={handleFinish} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-xs font-bold shadow-md transition-all">
            {isReadOnly ? 'Close' : 'Finish'}
          </button>
        </div>
      </header>

      {/* 🔴 FINISH CONFIRMATION MODAL */}
      {showFinishConfirm && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 animate-in zoom-in-95 duration-200">
            <div className="text-center">
              <div className="w-16 h-16 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-4 text-2xl">
                ⚠️
              </div>
              <h3 className="text-lg font-black text-gray-900 mb-2">Unsaved Changes</h3>
              <p className="text-sm text-gray-500 mb-6 font-medium">
                You have unsaved annotations. Would you like to save them before finishing?
              </p>
              
              <div className="grid grid-cols-2 gap-3">
                <button 
                  onClick={() => handleSave(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-xl text-xs font-black shadow-lg shadow-blue-200 transition-all"
                >
                  SAVE & FINISH
                </button>
                <button 
                  onClick={() => window.close()}
                  className="bg-gray-100 hover:bg-gray-200 text-gray-600 py-2.5 rounded-xl text-xs font-black transition-all"
                >
                  DISCARD & EXIT
                </button>
              </div>
              
              <button 
                onClick={() => setShowFinishConfirm(false)}
                className="mt-4 text-[10px] font-black text-gray-400 hover:text-gray-600 uppercase tracking-widest"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 flex overflow-hidden">
        {/* Left Sidebar (Stacked Panels) */}
        <div className="w-[450px] flex flex-col flex-shrink-0 h-full border-r border-gray-200 bg-white overflow-hidden">
          {/* Top Part: Annotation Summary */}
          <div className="flex-[3] border-b border-gray-200 overflow-hidden">
            <AnnotationPanel
              annotations={visibleAnnotations}
              annotationOptions={annotationOptions}
              setAnnotationOptions={setAnnotationOptions}
              optionColors={optionColors}
              setOptionColors={setOptionColors}
              handleRemoveAnnotation={(a) => !isReadOnly && dispatch({ type: DocActionTypes.REMOVE_ANNOTATION, payload: { annotation: a } })}
              activeLabelFilters={activeLabelFilters}
              setActiveLabelFilters={setActiveLabelFilters}
              selectedTermContext={selectedTermContext}
              setSelectedTermContext={setSelectedTermContext}
              handleExtendMatch={() => {}}
              isReadOnly={isReadOnly}
            />
          </div>
          
          {/* Bottom Part: Action History */}
          <div className="flex-[2] overflow-hidden">
            <ActionHistoryPanel 
              history={doc.actionHistory}
              optionColors={optionColors}
              onUndo={(id) => !isReadOnly && dispatch({ type: DocActionTypes.UNDO_ACTION, payload: { actionId: id } })}
            />
          </div>
        </div>

        {/* Center: Narrative */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          
          {/* Narrative Toolbar (NEW) */}
          <div className="px-12 py-3 border-b border-gray-100 flex items-center justify-between bg-gray-50/30">
            <div className="flex items-center gap-4">
              <span className="text-[11px] font-black text-gray-500 uppercase tracking-widest">Narrative View</span>
              
              {/* Display Toggle (Relationship Builder Mode) */}
              <div className="flex items-center gap-3 bg-white border border-gray-200 rounded-full px-4 py-1.5 shadow-sm">
                <span className={`text-[10px] font-bold transition-colors ${!relationshipBuilderMode ? 'text-blue-600' : 'text-gray-400'}`}>Standard</span>
                <button 
                  onClick={() => setRelationshipBuilderMode(!relationshipBuilderMode)}
                  className={`relative w-10 h-5 rounded-full transition-colors duration-200 focus:outline-none ${
                    relationshipBuilderMode ? 'bg-orange-500' : 'bg-gray-200'
                  }`}
                >
                  <div className={`absolute top-1 left-1 bg-white w-3 h-3 rounded-full shadow-sm transform transition-transform duration-200 ${
                    relationshipBuilderMode ? 'translate-x-5' : 'translate-x-0'
                  }`} />
                </button>
                <span className={`text-[10px] font-bold transition-colors ${relationshipBuilderMode ? 'text-orange-600' : 'text-gray-400'}`}>Link Mode</span>
              </div>
            </div>

            <div className="text-[10px] font-medium text-gray-400">
              Page {doc.currentPageIndex + 1} of {doc.pages.length}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 lg:p-8">
            <div className="max-w-6xl mx-auto relative">
              
              {relationshipBuilderMode ? (
                <PageDisplayBuilder
                  annotations={visibleAnnotations}
                  currentPage={doc.currentPageIndex}
                  pageData={currentPageData || ''}
                  currentAnnotationRelation={currentAnnotationRelation}
                  optionColors={optionColors}
                  handleTextSelection={handleTextSelection}
                  userRole={userRole as any}
                  isReadOnly={isReadOnly}
                />
              ) : (
                <PageDisplay
                  annotations={visibleAnnotations}
                  updateAnnotationNote={handleVerifyAnnotation}
                  userRole={userRole as any}
                  currentPage={doc.currentPageIndex}
                  pageData={currentPageData || ''}
                  optionColors={optionColors}
                  handleTextSelection={handleTextSelection}
                  activeLabelFilters={activeLabelFilters}
                  disableFilter={false}
                  annotationSet="SME"
                  onClickAnnotation={onClickAnnotation}
                  selectedTermContext={selectedTermContext}
                  setSelectedTermContext={setSelectedTermContext}
                  isReadOnly={isReadOnly}
                />
              )}
            </div>
          </div>

          {/* Bottom Drawer: Metadata */}
          {metaView !== 'none' && (
            <div className="h-1/3 bg-gray-50 border-t border-gray-200 overflow-y-auto p-6 animate-in slide-in-from-bottom-full duration-300">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-black text-gray-800 uppercase tracking-widest">{metaView}</h3>
                <button onClick={() => setMetaView('none')} className="text-gray-400 hover:text-black font-bold">✕</button>
              </div>
              <div 
                className="prose prose-sm max-w-none bg-white p-6 rounded-xl border border-gray-200 shadow-inner"
                dangerouslySetInnerHTML={{ __html: doc.meta[metaView] || 'No data available' }} 
              />
            </div>
          )}
        </div>

        {/* Relationship Linker (If active) */}
        {relationshipBuilderMode && (
          <div className="w-96 bg-gray-50 border-l border-gray-200 p-4 overflow-y-auto">
             <RelationshipBuilderPanel
                annotations={visibleAnnotations}
                handleSelectCell={(a, type) => {
                  if (isReadOnly) return;
                  setCurrentAnnotationRelation(a);
                  setCurrentRelationType(type);
                }}
                currentAnnotation={currentAnnotationRelation}
                currentRelationshipType={currentRelationType}
                isReadOnly={isReadOnly}
              />
          </div>
        )}
      </main>

      {unifiedContextMenu.visible && !isReadOnly && (
        <UnifiedContextMenuDisplay
          contextMenu={unifiedContextMenu}
          annotationOptions={annotationOptions}
          optionColors={optionColors}
          addAnnotation={handleAddAnnotation}
          handleAddRelationship={(opt) => {
             // Handle relationship set logic here or via dispatch
             setUnifiedContextMenu(prev => ({ ...prev, visible: false }));
          }}
          closeContextMenu={() => setUnifiedContextMenu(prev => ({ ...prev, visible: false }))}
        />
      )}

      <LLMAnnotationPopup
        x={llmPopup.x} y={llmPopup.y} visible={llmPopup.visible && !isReadOnly} text={llmPopup.text}
        annotationOptions={annotationOptions}
        type={llmPopup.type}
        userRole={userRole}
        selectedLabel={llmPopup.label || ''}
        isVerified={llmPopup.isVerified}
        onAdd={handleLlmAddAnnotation}
        onUnverify={() => handleUnverifyAnnotation(llmPopup.start, llmPopup.end, llmPopup.label || '')}
        onReject={() => handleRejectAnnotation(llmPopup.start, llmPopup.end, llmPopup.label || '')}
        onRemove={() => handleRejectAnnotation(llmPopup.start, llmPopup.end, llmPopup.label || '')}
        onClose={() => {
          setLlmPopup(prev => ({ ...prev, visible: false }));
          setSelectedTermContext(null);
        }}
      />
    </div>
  );
}
