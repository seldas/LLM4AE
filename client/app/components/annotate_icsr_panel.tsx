// annotate_icsr_panel.tsx
'use client';

import { useState, useReducer, useEffect, useRef, useMemo, JSX, ReactNode } from 'react';
import { docReducer, initialDocState, DocActionTypes } from '../lib/doc-reducer';
import {
  Annotation,
  AnnotationOptions,
  AnnotationRelationships,
  TextContext,
  AnnotationGuideline
} from '../lib/interfaces';
import { getHistoryFile, getCaseById, saveAnnotationsToDb } from '../lib/api';
import {  
  escapeRegExp,
  generateOptionColors,
  API_BASE, 
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
  overrideProject?: string;
  overrideId?: string;
}

const PRIMARY_ENTITY_LABELS = new Set(['AE','SDRUG','CDRUG','ODRUG','TREATMENT','SDRUG','CDrug','SDrug','Treatment']);
const TEMPORAL_LABELS = new Set(['TEMPORAL','DATE','TIME','DURATION','RELATIVE','LATENCY']);

// Icons
const IconSave = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg>;
const IconExport = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>;
const IconExit = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>;
const IconSparkles = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>;
const IconRobot = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>;

export default function AnnotateIcsrPanel({ overrideProject, overrideId}: Props) {
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
  const [activeLayers, setActiveLayers] = useState<string[]>(['Human', 'LLM', 'BERT']);
  const [theme, setTheme] = useState<'light' | 'dark' | 'soft'>('light');
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [userRole, setUserRole] = useState<string>("Anonymous");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
  
  const [isProcessingLlm, setIsProcessingLlm] = useState(false);
  const [isProcessingBert, setIsProcessingBert] = useState(false);
  
  const [metaView, setMetaView] = useState<'none' | 'demographic' | 'products' | 'outcomes'>('none');
  const availableMetaEntries = useMemo(() => {
    return []; // For ICSR integration, we might not have standard metadata entries yet
  }, [doc.meta]);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      const u = JSON.parse(storedUser);
      setCurrentUser(u);
      setIsLoggedIn(true);
      const isGuest = u.username === 'guest';
      setIsReadOnly(isGuest);
      const displayName = u.full_name || u.username;
      setUserRole(displayName);
    } else {
        // Default to a system user if none logged in
        setUserRole("ICSR_Annotator");
    }
  }, []);

  const [relationshipBuilderMode, setRelationshipBuilderMode] = useState(false);
  const [currentAnnotationRelation, setCurrentAnnotationRelation] = useState<Annotation | null>(null);
  const [currentRelationType, setCurrentRelationType] = useState<keyof AnnotationRelationships | ''>('');
  
  const [annotationOptions, setAnnotationOptions] = useState<AnnotationOptions>({});
  const [annotationGuidelines, setAnnotationGuidelines] = useState<AnnotationGuideline[]>([]);
  const [optionColors, setOptionColors] = useState<{ [key: string]: string }>({});
  const [activeLabelFilters, setActiveLabelFilters] = useState<string[]>([]);
  const [temporalTerms, setTemporalTerms] = useState<Annotation[]>([]);
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
    type?: 'LLM' | 'BERT' | 'SME' | 'NEW'; label?: string; isVerified?: boolean;
    note?: string;
  }>({ visible: false, x: 0, y: 0, text: '', start: 0, end: 0 });

  const currentPageData = doc.pages[doc.currentPageIndex] || null;

  // Filter Annotations for Display
  const visibleAnnotations = useMemo(() => {
    if (!doc.annotations) return [];
    const enriched = doc.annotations.map(a => {
        const note = (a.note || "").toUpperCase();
        const isLLM = note.includes('LLM') || note.includes('LLAMA');
        const isBERT = note.includes('BERT');
        const isAI = isLLM || isBERT || note.includes('AI');
        const isVerified = note.includes('VERIFIED');
        const isImported = note.includes('IMPORTED');
        
        let layer = 'Human';
        let priority = 1;

        if (isLLM && !isVerified) {
          layer = 'LLM';
          priority = 2;
        } else if (isBERT && !isVerified) {
          layer = 'BERT';
          priority = 3;
        } else if (isAI && !isVerified) {
          layer = 'LLM';
          priority = 2;
        } else if (isImported) {
          layer = 'BERT'; // Reuse BERT layer for imported ones for visibility
          priority = 4;
        } else {
          layer = 'Human';
          priority = 1;
        }

        const normalizedLabel = labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase();
        return { ...a, priority, layer, normalizedLabel };
      });

      let filtered = enriched.filter(a => {
        const note = (a.note || "").toUpperCase();
        if (note.includes('REJECTED') && !showRejected) return false;
        return activeLayers.includes(a.layer);
      });

      const positionMap: Record<string, typeof enriched[0]> = {};
      filtered.sort((a, b) => b.priority - a.priority).forEach(ann => {
        const key = `${ann.textContext.start}-${ann.textContext.end}-${ann.label}`;
        positionMap[key] = ann;
      });
    return Object.values(positionMap);
  }, [doc.annotations, activeLayers, showRejected]);

  const filteredLinkAnnotations = useMemo(() => {
    return visibleAnnotations.filter(a => {
      const label = a.label.toUpperCase();
      const note = a.note.toUpperCase();
      const isPureAI = (note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT') || note.includes('AI') || note.includes('IMPORTED')) && !note.includes('VERIFIED');
      const isHuman = !isPureAI;
      const isAEDrug = ['AE', 'SYMPTOM', 'SIGN', 'DRUG', 'SDRUG', 'CDRUG'].includes(label);
      return isHuman && isAEDrug;
    });
  }, [visibleAnnotations]);

  const isPrimaryEntitySelected = currentAnnotationRelation
    ? PRIMARY_ENTITY_LABELS.has(labelNormalizer[currentAnnotationRelation.label.toUpperCase()] || currentAnnotationRelation.label.toUpperCase())
    : false;

  const linkModeColors: Record<string, string> = {
    'AE': 'hsl(0, 70%, 50%)', 
    'SYMPTOM': 'hsl(0, 70%, 50%)',
    'SIGN': 'hsl(0, 70%, 50%)',
    'DRUG': 'hsl(210, 70%, 50%)', 
    'SDRUG': 'hsl(210, 70%, 50%)',
    'CDRUG': 'hsl(210, 70%, 50%)'
  };

  useEffect(() => {
    if (currentAnnotationRelation) {
      const updated = doc.annotations.find(a => 
        a.textContext.start === currentAnnotationRelation.textContext.start && 
        a.textContext.end === currentAnnotationRelation.textContext.end &&
        a.label === currentAnnotationRelation.label &&
        a.note === currentAnnotationRelation.note
      );
      if (updated) setCurrentAnnotationRelation(updated);
    }
  }, [doc.annotations]);

  useEffect(() => {
    setHasUnsavedChanges(doc.actionHistory.length > 0);
  }, [doc.actionHistory.length]);

  const handleSave = async (shouldClose = false) => {
      if (isReadOnly) return;
      try {
        await saveAnnotationsToDb({
          id: overrideId || '',
          curr_folder: overrideProject ?? 'AskMyFAERS_Integration',
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

  const handleLayerToggle = (layer: string) => {
    setActiveLayers(prev => prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]);
  };

  const handleLlmAnnotate = async () => {
    if (isReadOnly || isProcessingLlm) return;
    setIsProcessingLlm(true);
    try {
      const res = await fetch(`${API_BASE}/llm-annotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: overrideId, folder: overrideProject ?? 'AskMyFAERS_Integration' })
      });
      if (!res.ok) {
        console.log('Response status:', res.status);
        console.log('Response text:', await res.text());
        throw new Error('LLM request failed');
      };
      
      // Start polling for completion
      pollProcessingStatus('llm');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
      setIsProcessingLlm(false);
    }
  };

  const handleBertAnnotate = async () => {
    if (isReadOnly || isProcessingBert) return;
    setIsProcessingBert(true);
    try {
      const res = await fetch(`${API_BASE}/bert-annotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file: overrideId, folder: overrideProject ?? 'AskMyFAERS_Integration' })
      });
      if (!res.ok) throw new Error('BERT request failed');
      
      // Start polling for completion
      pollProcessingStatus('bert');
    } catch (err: any) {
      alert(`Error: ${err.message}`);
      setIsProcessingBert(false);
    }
  };

  const pollProcessingStatus = (type: 'llm' | 'bert') => {
    const interval = setInterval(async () => {
      try {
        const data = await getCaseById(overrideId || '');
        if (!data) return;
        
        const meta = data.meta || {};
        const isDone = type === 'llm' ? meta.llm_processed === 'Done' : meta.bert_processed === 'Done';
        
        if (isDone) {
          clearInterval(interval);
          if (type === 'llm') setIsProcessingLlm(false);
          else setIsProcessingBert(false);
          // Reload the entire document to get new annotations
          dispatch({ type: DocActionTypes.LOAD, payload: { ...data, fileName: overrideId ?? 'default-file-name' } });
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 3000);
    
    // Safety timeout after 2 minutes
    setTimeout(() => {
      clearInterval(interval);
      setIsProcessingLlm(false);
      setIsProcessingBert(false);
    }, 120000);
  };

  const handleIcsrExport = async () => {
    try {
      const res = await fetch(`${API_BASE}/export_icsr/${overrideId}`);
      if (!res.ok) throw new Error('Export failed');
      const data = await res.json();
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `AskMyFAERS_Annotations_${overrideId}.json`;
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (error: any) {
      alert(`❌ Failed to export ICSR: ${error.message}`);
    }
  };

  const handleSendBackToSource = async () => {
    try {
      const res = await fetch(`${API_BASE}/export_icsr/${overrideId}`);
      if (!res.ok) throw new Error('Export failed');
      const data = await res.json();
      
      // In a real scenario, you would POST this to AskMyFAERS
      console.log("Sending back to AskMyFAERS:", data);
      
      alert("✓ Successfully sent annotations back to AskMyFAERS (Simulated)\n\nNote: In a production environment, this would perform a background POST to the AskMyFAERS API.");
    } catch (error: any) {
      alert(`❌ Failed to send back: ${error.message}`);
    }
  };

  const handleTextSelection = () => {
      if (isReadOnly) return;
      const selection = window.getSelection();
      if (!selection || !selection.toString().trim()) return;
      const text = selection.toString().trim().replace(/\u00A0/g, ' ');
      const range = selection.getRangeAt(0);      
      const startNode = range.startContainer;
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
        if (!annotationGuidelines.length) return;
        setUnifiedContextMenu({ visible: true, x: rect.left + window.scrollX, y: rect.top + window.scrollY, type: 'annotation', start: absoluteStart, end: absoluteEnd });
      } else if (currentAnnotationRelation) {
          setUnifiedContextMenu({ visible: true, x: rect.left + window.scrollX, y: rect.top + window.scrollY, type: 'relationship', start: absoluteStart, end: absoluteEnd, options: ['Set', 'Delete'] });
      }
  };

  const handleAddAnnotation = (label: string) => {
      if (isReadOnly) return;
      const newAnnotation: Annotation = {
        textContext: { text: selectedText, page: doc.currentPageIndex, start: unifiedContextMenu.start as number, end: unifiedContextMenu.end as number, disputed: false },
        label: label,
        note: userRole,
        relationships: { latency: {text:'',page:0}, date: {text:'',page:0}, time: {text:'',page:0}, frequency: {text:'',page:0}, temporal_sequence: {text:'',page:0} },
      };
      dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation, historyType: 'add' } });
      setUnifiedContextMenu(prev => ({ ...prev, visible: false }));
  };

  const handleVerifyAnnotation = (start: number, end: number, text: string, label: string, note: string) => {
    if (isReadOnly) return;
    const existingAI = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert') || a.note.toUpperCase().includes('IMPORTED')));
    if (existingAI) {
      const updatedAI = { ...existingAI, note: `${existingAI.note} | VERIFIED BY ${userRole}` };
      dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAI, historyType: 'verify' } });
      const newHumanAnnotation: Annotation = {
        textContext: { text, start, end, page: doc.currentPageIndex, disputed: false },
        label: label, note: userRole,
        relationships: { latency: {text:'',page:0}, date: {text:'',page:0}, time: {text:'',page:0}, frequency: {text:'',page:0}, temporal_sequence: {text:'',page:0} },
      };
      dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newHumanAnnotation, historyType: 'add' } });
    }
  };

  const handleRejectAnnotation = (start: number, end: number, label: string) => {
    if (isReadOnly) return;
    const existing = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()));
    if (existing) {
      const updatedAnnotation = { ...existing, note: `${existing.note} | REJECTED BY ${userRole}` };
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
      textContext: { text, start, end, page: doc.currentPageIndex, disputed: false },
      label: label, note: userRole,
      relationships: { latency: { text: '', page: 0 }, date: { text: '', page: 0 }, time: { text: '', page: 0 }, frequency: { text: '', page: 0 }, temporal_sequence: { text: '', page: 0 } },
    };
    if (type === 'LLM' || type === 'BERT') {
      const existingAI = doc.annotations.find(a => 
        a.textContext.start === start && 
        a.textContext.end === end && 
        (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) && 
        (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert') || a.note.toUpperCase().includes('IMPORTED'))
      );
      if (existingAI) {
        const updatedAI = { ...existingAI, note: `${existingAI.note} | VERIFIED BY ${userRole}` };
        dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAI, historyType: 'verify' } });
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
    const humanAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && (a.note.toUpperCase() === userRole.toUpperCase()));
    const aiAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert') || a.note.toUpperCase().includes('IMPORTED')) && a.note.toUpperCase().includes('VERIFIED'));
    if (aiAnno) {
      const revertedAiNote = aiAnno.note.split(' | VERIFIED BY')[0];
      const revertedAi = { ...aiAnno, note: revertedAiNote };
      dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: revertedAi } });
      if (humanAnno) dispatch({ type: DocActionTypes.REMOVE_ANNOTATION, payload: { annotation: humanAnno } });
    }
    setLlmPopup(prev => ({ ...prev, visible: false }));
    setSelectedTermContext(null);
  };

  const onClickAnnotation = (text: string, start: number, end: number, x: number, y: number, note?: string, label?: string) => {
    let type: 'LLM' | 'BERT' | 'SME' | 'NEW' = 'NEW';
    let isVerified = false;
    if (note) {
      const upperNote = note.toUpperCase();
      const isLLM = upperNote.includes('LLM') || upperNote.includes('LLAMA');
      const isBERT = upperNote.includes('BERT');
      const isAI = isLLM || isBERT || upperNote.includes('AI') || upperNote.includes('IMPORTED');
      
      if (isAI) { 
        if (isBERT || upperNote.includes('IMPORTED')) type = 'BERT';
        else type = 'LLM';
        isVerified = upperNote.includes('VERIFIED'); 
      } 
      else { type = 'SME'; }
    }
    setLlmPopup({ visible: true, x, y, text, start, end, type, label, isVerified, note });
    if (label) setSelectedPopupLabel(label);
  };

  const onClickLinkAnnotation = (a: Annotation) => {
    if (isReadOnly) return;
    const targetType = currentRelationType || 'latency';
    if (currentAnnotationRelation?.textContext.start === a.textContext.start) {
      setCurrentAnnotationRelation(null);
      setCurrentRelationType('');
    } else {
      setCurrentAnnotationRelation(a);
      setCurrentRelationType(targetType);
    }
  };

  useEffect(() => {
    if (overrideId) {
      getCaseById(overrideId).then(data => {
        if (!data) return;
        dispatch({ type: DocActionTypes.LOAD, payload: { ...data, fileName: overrideId } });
      });
    }
  }, [overrideId]);

  useEffect(() => {
    if (doc.annotations) {
      const labels = new Set(['DRUG', 'AE', 'MEDICAL HISTORY', 'LAB', 'TEMPORAL', 'AGE', 'SEX', 'COD', 'DIAGNOSTIC']);
      doc.annotations.forEach(a => labels.add(a.label.toUpperCase()));
      const arr = Array.from(labels).sort();
      setAnnotationOptions(Object.fromEntries(arr.map(l => [l, l])));
      setOptionColors(generateOptionColors(arr));
      setActiveLabelFilters(prev => {
        const newFilters = [...prev];
        let changed = false;
        arr.forEach(l => { if (!newFilters.includes(l)) { newFilters.push(l); changed = true; } });
        return changed ? newFilters : prev;
      });
    }
  }, [doc.annotations]);

  useEffect(() => {
    const terms = doc.annotations
      .filter(a => {
        const normalized = labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase();
        return TEMPORAL_LABELS.has(normalized);
      })
      .sort((a, b) => (a.textContext.start || 0) - (b.textContext.start || 0));
    setTemporalTerms(terms);
  }, [doc.annotations]);

  useEffect(() => {
    const loadGuidelines = async () => {
      try {
        const res = await fetch(`${API_BASE}/annotation-guidelines`);

        if (!res.ok) throw new Error('Guidelines fetch failed');
        const data: AnnotationGuideline[] = await res.json();
        setAnnotationGuidelines(data);
      } catch (err) {
        console.error('Unable to load annotation guidelines', err);
      }
    };
    loadGuidelines();
  }, []);

  return (
    <div className="app-container h-screen overflow-hidden flex flex-col bg-slate-50 text-slate-900 antialiased">
      
      {/* --- Unified Header --- */}
      <header className="bg-white border-b border-slate-200 h-14 px-6 flex items-center justify-between shadow-sm z-30 shrink-0">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 bg-purple-500 rounded-full shadow-[0_0_8px_rgba(168,85,247,0.5)]"></div>
            <h1 className="text-sm font-bold text-slate-900 tracking-widest uppercase">ICSR Annotation Tool</h1>
          </div>

              <div className="h-6 w-px bg-slate-200"></div>

              <div className="flex items-center gap-4">
                <button 
                  onClick={handleLlmAnnotate} 
                  disabled={isReadOnly || isProcessingLlm}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-bold uppercase tracking-wider transition-colors ${isProcessingLlm ? 'bg-indigo-50 text-indigo-400' : 'hover:bg-indigo-50 text-indigo-600'}`}
                  title="Run LLM Annotation"
                >
                  <IconSparkles /> {isProcessingLlm ? 'LLM Working...' : 'LLM Annotate'}
                </button>
                <button 
                  onClick={handleBertAnnotate} 
                  disabled={isReadOnly || isProcessingBert}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded text-[11px] font-bold uppercase tracking-wider transition-colors ${isProcessingBert ? 'bg-teal-50 text-teal-400' : 'hover:bg-teal-50 text-teal-600'}`}
                  title="Run BERT Annotation"
                >
                  <IconRobot /> {isProcessingBert ? 'BERT Working...' : 'BERT Annotate'}
                </button>

                <div className="h-4 w-px bg-slate-200"></div>

                <button 
                  onClick={handleIcsrExport} 
                  className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 rounded text-[11px] font-bold text-slate-500 uppercase tracking-wider transition-colors"
                  title="Download JSON for manual import"
                >
                  <IconExport /> Download JSON
                </button>
            {!isReadOnly && (
              <button onClick={() => handleSave(false)} className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-[11px] font-bold uppercase tracking-wider shadow-sm transition-colors">
                <IconSave /> Save
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-6">
          <div className="text-right border-r border-slate-200 pr-6">
            <p className="text-[10px] font-bold text-slate-900 leading-none uppercase">{userRole}</p>
            <p className="text-[8px] text-slate-400 font-bold uppercase tracking-tighter mt-0.5">ICSR Integrator</p>
          </div>

          <button onClick={() => window.close()} className="flex items-center gap-2 px-4 py-1.5 border border-slate-200 hover:bg-red-50 hover:text-red-600 rounded text-[11px] font-bold text-slate-500 uppercase tracking-wider transition-all">
            <IconExit /> Close
          </button>
        </div>
      </header>

      {/* --- Main Area --- */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        
        {/* Left Sidebar */}
        <aside className="w-[400px] flex flex-col border-r border-slate-200 bg-white shrink-0 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={() => setShowRejected(!showRejected)} className={`text-[9px] font-bold uppercase px-2 py-1 rounded transition-colors ${showRejected ? 'bg-red-50 text-red-600' : 'text-slate-400 hover:text-slate-600'}`}>
                {showRejected ? 'Hiding Rejected' : 'Show Rejected'}
              </button>
            </div>
          </div>

          <div className="flex-[3] overflow-hidden border-b border-slate-100">
            {relationshipBuilderMode ? (
              <div className="flex flex-col h-full p-4">
                <div className="flex justify-between items-center mb-4 gap-3">
                  {currentAnnotationRelation && (
                    <div className="text-[10px] font-bold text-blue-600 px-3 py-1.5 rounded bg-blue-50 border border-blue-100 uppercase tracking-tight">
                      Active: {currentAnnotationRelation.textContext.text}
                    </div>
                  )}
                </div>
                <div className="flex-1 overflow-y-auto">
                  <RelationshipBuilderPanel
                    annotations={filteredLinkAnnotations}
                    handleSelectCell={(a, type) => {
                      if (isReadOnly) return;
                      setSelectedTermContext(null);
                      if (currentAnnotationRelation?.textContext.start === a.textContext.start && currentRelationType === type) {
                        setCurrentAnnotationRelation(null);
                        setCurrentRelationType('');
                      } else {
                        setCurrentAnnotationRelation(a);
                        setCurrentRelationType(type);
                      }
                    }}
                    currentAnnotation={currentAnnotationRelation}
                    currentRelationshipType={currentRelationType}
                    isReadOnly={isReadOnly}
                    temporalTerms={temporalTerms}
                    currentAnnotationIsPrimary={isPrimaryEntitySelected}
                    selectedTermContext={selectedTermContext}
                  />
                </div>
              </div>
            ) : (
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
                pageData={currentPageData || ""}
              />
            )}
          </div>
          
          <div className="flex-[2] overflow-hidden bg-slate-50/20">
            <ActionHistoryPanel 
              history={doc.actionHistory}
              optionColors={optionColors}
              onUndo={(id) => !isReadOnly && dispatch({ type: DocActionTypes.UNDO_ACTION, payload: { actionId: id } })}
            />
          </div>
        </aside>

        <div className="flex flex-1 min-w-0 overflow-hidden">

          {/* Center Canvas */}
          <main className="flex-1 flex flex-col min-h-0 overflow-hidden bg-white">
            <div className="px-8 py-3 border-b border-slate-100 bg-white shrink-0">
              <div className="flex flex-wrap items-center gap-4 sm:justify-between">
                <div className="flex flex-wrap items-center gap-3 min-w-0 flex-1">
                  <div className="flex items-center gap-3 bg-slate-100 rounded-full px-3 py-1 shrink-0">
                    <button onClick={() => setRelationshipBuilderMode(false)} className={`px-3 py-0.5 rounded-full text-[10px] font-bold transition-all ${!relationshipBuilderMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>STANDARD</button>
                    <button onClick={() => setRelationshipBuilderMode(true)} className={`px-3 py-0.5 rounded-full text-[10px] font-bold transition-all ${relationshipBuilderMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>LINK MODE</button>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Layers:</span>
                    <div className="flex bg-slate-100 p-0.5 rounded-full gap-0.5">
                      {['Human', 'LLM', 'BERT'].map(layer => (
                      <button
                        key={layer}
                        onClick={() => handleLayerToggle(layer)}
                        className={`px-3 py-0.5 rounded-full text-[9px] font-bold uppercase transition-all ${activeLayers.includes(layer) ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                      >
                        {layer}
                      </button>
                    ))}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Theme:</span>
                  <div className="flex bg-slate-100 p-0.5 rounded-full gap-0.5">
                    {['light', 'dark', 'soft'].map(t => (
                    <button
                      key={t}
                      onClick={() => setTheme(t as any)}
                      className={`px-3 py-0.5 rounded-full text-[9px] font-bold uppercase transition-all ${theme === t ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                    >
                      {t}
                    </button>
                  ))}
                  </div>
                </div>
              </div>
              <div className="text-[10px] font-bold text-slate-300 uppercase tracking-tighter whitespace-nowrap mt-3">
                ICSR ID: {overrideId || 'Ad-hoc'}
              </div>
            </div>

            {relationshipBuilderMode ? (
              <div className="flex-1 flex flex-col overflow-hidden">
                <div className={`flex-1 overflow-y-auto p-12 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-950' : theme === 'soft' ? 'bg-[#eee8d5]' : 'bg-slate-50/30'}`}>
                  <div className={`max-w-4xl mx-auto shadow-sm border min-h-full transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
                    <PageDisplayBuilder
                      annotations={filteredLinkAnnotations}
                      currentPage={doc.currentPageIndex}
                      pageData={currentPageData || ''}
                      currentAnnotationRelation={currentAnnotationRelation}
                      optionColors={{...optionColors, ...linkModeColors}}
                      handleTextSelection={handleTextSelection}
                      userRole={userRole as any}
                      isReadOnly={isReadOnly}
                      onClickAnnotation={onClickLinkAnnotation}
                      theme={theme}
                      selectedTermContext={selectedTermContext}
                      temporalTerms={temporalTerms}
                      showTemporalHighlights={relationshipBuilderMode}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className={`flex-1 overflow-y-auto p-12 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-950' : theme === 'soft' ? 'bg-[#eee8d5]' : 'bg-slate-50/30'}`}>
                <div className={`max-w-4xl mx-auto shadow-sm border min-h-full pb-32 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
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
                    theme={theme}
                  />
                </div>
              </div>
            )}
          </main>
        </div>
      </div>

      {unifiedContextMenu.visible && !isReadOnly && (
        <UnifiedContextMenuDisplay
          contextMenu={unifiedContextMenu}
          annotationOptions={annotationOptions}
          optionColors={optionColors}
          annotationGuidelines={annotationGuidelines}
          addAnnotation={handleAddAnnotation}
          handleAddRelationship={(opt) => {
             if (isReadOnly || !currentAnnotationRelation || !currentRelationType) return;

             const updated = { ...currentAnnotationRelation, relationships: { ...currentAnnotationRelation.relationships, [currentRelationType]: opt === 'Set' ? { text: selectedText, page: doc.currentPageIndex, start: unifiedContextMenu.start, end: unifiedContextMenu.end } : { text: '', page: 0, start: 0, end: 0 } } };
             dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updated, historyType: 'verify' } });
             setUnifiedContextMenu(prev => ({ ...prev, visible: false }));
          }}

          closeContextMenu={() => setUnifiedContextMenu(prev => ({ ...prev, visible: false }))}
        />
      )}

      {saveSuccess && (
        <div className="fixed bottom-4 right-4 bg-green-100 border border-green-300 text-green-700 px-4 py-2 rounded shadow-lg text-sm">
          ✓ Changes saved successfully
        </div>
      )}

      <LLMAnnotationPopup
        x={llmPopup.x} y={llmPopup.y} visible={llmPopup.visible && !isReadOnly} text={llmPopup.text}
        annotationOptions={annotationOptions} type={llmPopup.type}
        userRole={(() => { if (!llmPopup.note) return userRole; const n = llmPopup.note.toUpperCase(); return (['SME1', 'SME2', 'ADJUDICATOR'].includes(n)) ? 'DevUser' : llmPopup.note; })()}
        selectedLabel={llmPopup.label || ''} isVerified={llmPopup.isVerified}
        onAdd={handleLlmAddAnnotation}
        onUnverify={() => handleUnverifyAnnotation(llmPopup.start, llmPopup.end, llmPopup.label || '')}
        onReject={() => handleRejectAnnotation(llmPopup.start, llmPopup.end, llmPopup.label || '')}
        onRemove={() => handleRejectAnnotation(llmPopup.start, llmPopup.end, llmPopup.label || '')}
        onClose={() => { setLlmPopup(prev => ({ ...prev, visible: false })); setSelectedTermContext(null); }}
        isReadOnly={isReadOnly}
      />
    </div>
  );
}
