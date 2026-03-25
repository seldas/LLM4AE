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
import { getHistoryFile, getCaseById, saveAnnotationsToDb } from '../lib/api';
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
  overrideProject?: string;
  overrideId?: string;
}

// Icons
const IconSave = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg>;
const IconExport = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>;
const IconExit = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>;

export default function Annotate_Panel({ overrideProject, overrideId}: Props) {
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
  const [activeLayers, setActiveLayers] = useState<string[]>(['Human', 'AI']);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [userRole, setUserRole] = useState<string>("Anonymous");
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
      const displayName = u.full_name || u.username;
      setUserRole(displayName);
    }
  }, []);

  const [relationshipBuilderMode, setRelationshipBuilderMode] = useState(false);
  const [showAllLinkRows, setShowAllLinkRows] = useState(false);
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
    type?: 'AI' | 'SME' | 'NEW'; label?: string; isVerified?: boolean;
    note?: string;
  }>({ visible: false, x: 0, y: 0, text: '', start: 0, end: 0 });

  const currentPageData = doc.pages[doc.currentPageIndex] || null;

  // Filter Annotations for Display
  const visibleAnnotations = useMemo(() => {
    const enriched = doc.annotations.map(a => {
      const note = (a.note || "").toUpperCase();
      const isAI = note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT') || note.includes('AI');
      const isVerified = note.includes('VERIFIED');
      let priority = 3; 
      if (!isAI) priority = 1;
      else if (!isVerified) priority = 2;
      else priority = 3;
      const normalizedLabel = labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase();
      return { ...a, priority, normalizedLabel };
    });

    let filtered = enriched.filter(a => {
      const note = (a.note || "").toUpperCase();
      if (note.includes('REJECTED') && !showRejected) return false;
      const isPureAI = a.priority === 2;
      const isHumanLayer = a.priority === 1 || a.priority === 3;
      if (isPureAI && activeLayers.includes('AI')) return true;
      if (isHumanLayer && activeLayers.includes('Human')) return true;
      return false;
    });

    const positionMap: Record<string, typeof enriched[0]> = {};
    filtered.sort((a, b) => a.priority - b.priority).forEach(ann => {
      const key = `${ann.textContext.start}-${ann.textContext.end}`;
      if (!positionMap[key]) positionMap[key] = ann;
    });
    return Object.values(positionMap);
  }, [doc.annotations, activeLayers, showRejected]);

  const filteredLinkAnnotations = useMemo(() => {
    return visibleAnnotations.filter(a => {
      const label = a.label.toUpperCase();
      const note = a.note.toUpperCase();
      const isPureAI = (note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT') || note.includes('AI')) && !note.includes('VERIFIED');
      const isHuman = !isPureAI;
      const isAEDrug = ['AE', 'SYMPTOM', 'SIGN', 'DRUG', 'SDRUG', 'CDRUG'].includes(label);
      return isHuman && isAEDrug;
    });
  }, [visibleAnnotations]);

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
          curr_folder: overrideProject ?? 'Playground',
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
    if (hasUnsavedChanges) setShowFinishConfirm(true);
    else window.close();
  };

  const handleLayerToggle = (layer: string) => {
    setActiveLayers(prev => prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]);
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
      worksheet.addRow({ text: anno.textContext.text, label: anno.label, start: anno.textContext.start, end: anno.textContext.end, page: anno.textContext.page + 1, note: anno.note });
    });
    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const id = overrideId || 'unknown';
    anchor.download = `Annotation_${id}_${timestamp}.xlsx`;
    anchor.click();
    window.URL.revokeObjectURL(url);
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
    const existingAI = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert')));
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
    if (type === 'AI') {
      const existingAI = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert')));
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
    const humanAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && (a.note.toUpperCase().includes('SME') || a.note.toUpperCase().includes('MJ.L') || a.note.toUpperCase().includes('K.L') || a.note.toUpperCase().includes('ADJUDICATOR')));
    const aiAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert')) && a.note.toUpperCase().includes('VERIFIED'));
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
    let type: 'AI' | 'SME' | 'NEW' = 'NEW';
    let isVerified = false;
    if (note) {
      const upperNote = note.toUpperCase();
      const isAI = upperNote.includes('LLM') || upperNote.includes('AI') || upperNote.includes('LLAMA') || upperNote.includes('BERT');
      if (isAI) { type = 'AI'; isVerified = upperNote.includes('VERIFIED'); } 
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
    if (overrideProject && overrideId) {
      getCaseById(overrideId, overrideProject).then(data => {
        if (!data) return;
        dispatch({ type: DocActionTypes.LOAD, payload: { ...data, fileName: overrideId } });
      });
    }
  }, [overrideProject, overrideId]);

  useEffect(() => {
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
  }, [doc.annotations]);

  return (
    <div className="app-container h-screen overflow-hidden flex flex-col bg-slate-50 text-slate-900 antialiased">
      
      {/* --- Unified Header --- */}
      <header className="bg-white border-b border-slate-200 h-14 px-6 flex items-center justify-between shadow-sm z-30 shrink-0">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
            <h1 className="text-sm font-bold text-slate-900 tracking-widest uppercase">LLM4AE</h1>
          </div>

              <div className="h-6 w-px bg-slate-200"></div>

              <div className="flex items-center gap-4">
                <button 
                  onClick={async () => {
                    try {
                      await handleExport();
                    } catch (error) {
                      console.error("Export failed:", error);
                    }
                  }} 
                  className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 rounded text-[11px] font-bold text-slate-500 uppercase tracking-wider transition-colors"
                >
                  <IconExport /> Export
                </button>
            {!isReadOnly && (
              <button onClick={() => handleSave(false)} className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-[11px] font-bold uppercase tracking-wider shadow-sm transition-colors">
                <IconSave /> Save
              </button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* User Display */}
          {isLoggedIn && currentUser && (
            <div className="flex items-center gap-3 border-r border-slate-200 pr-6">
              <div className="w-7 h-7 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300">
                {currentUser.username.charAt(0).toUpperCase()}
              </div>
              <div className="text-right">
                <p className="text-[10px] font-bold text-slate-900 leading-none uppercase">{currentUser.username === 'guest' ? 'Anonymous' : (currentUser.full_name || currentUser.username)}</p>
                <p className="text-[8px] text-slate-400 font-bold uppercase tracking-tighter mt-0.5">{currentUser.username === 'guest' ? 'Guest' : 'Annotator'}</p>
              </div>
            </div>
          )}

          <button onClick={handleFinish} className="flex items-center gap-2 px-4 py-1.5 border border-slate-200 hover:bg-red-50 hover:text-red-600 rounded text-[11px] font-bold text-slate-500 uppercase tracking-wider transition-all">
            <IconExit /> {isReadOnly ? 'Close' : 'Exit'}
          </button>
        </div>
      </header>

      {/* --- Main Area --- */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* Left Sidebar */}
        <aside className="w-[400px] flex flex-col border-r border-slate-200 bg-white shrink-0 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Visibility:</span>
                <div className="flex bg-slate-200/50 p-0.5 rounded gap-0.5">
                  {['Human', 'AI'].map(layer => (
                    <button key={layer} onClick={() => handleLayerToggle(layer)} className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase transition-all ${activeLayers.includes(layer) ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}>
                      {layer}
                    </button>
                  ))}
                </div>
              </div>
              <button onClick={() => setShowRejected(!showRejected)} className={`text-[9px] font-bold uppercase px-2 py-1 rounded transition-colors ${showRejected ? 'bg-red-50 text-red-600' : 'text-slate-400 hover:text-slate-600'}`}>
                {showRejected ? 'Hiding Rejected' : 'Show Rejected'}
              </button>
            </div>
          </div>

          <div className="flex-[3] border-b border-slate-100 overflow-hidden">
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
          </div>
          
          <div className="flex-[2] overflow-hidden bg-slate-50/20">
            <ActionHistoryPanel 
              history={doc.actionHistory}
              optionColors={optionColors}
              onUndo={(id) => !isReadOnly && dispatch({ type: DocActionTypes.UNDO_ACTION, payload: { actionId: id } })}
            />
          </div>
        </aside>

        {/* Center Canvas */}
        <main className="flex-1 flex flex-col overflow-hidden bg-white">
          <div className="px-8 py-3 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3 bg-slate-100 rounded-full px-3 py-1 shrink-0">
                <button onClick={() => setRelationshipBuilderMode(false)} className={`px-3 py-0.5 rounded-full text-[10px] font-bold transition-all ${!relationshipBuilderMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>STANDARD</button>
                <button onClick={() => setRelationshipBuilderMode(true)} className={`px-3 py-0.5 rounded-full text-[10px] font-bold transition-all ${relationshipBuilderMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>LINK MODE</button>
              </div>

              <div className="flex gap-1.5 items-center">
                <span className="text-[10px] font-bold text-slate-400 uppercase mr-1">Data:</span>
                {['Demographic', 'Products', 'Outcomes'].map(v => (
                  <button key={v} onClick={() => setMetaView(metaView === v.toLowerCase() ? 'none' : v.toLowerCase() as any)} className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all border ${metaView === v.toLowerCase() ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-400 border-slate-200 hover:border-slate-300'}`}>{v}</button>
                ))}
              </div>
            </div>


            <div className="text-[10px] font-bold text-slate-300 uppercase tracking-tighter">
              Record ID: {overrideId || 'Ad-hoc'}
            </div>
          </div>

          {relationshipBuilderMode ? (
            <div className="flex-1 flex flex-col overflow-hidden">
              <div className="flex-1 overflow-y-auto p-12 bg-slate-50/30">
                <div className="max-w-4xl mx-auto bg-white shadow-sm border border-slate-200 min-h-full">
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
                  />
                </div>
              </div>
              <div className="h-[350px] overflow-y-auto p-8 bg-white border-t border-slate-200 shadow-[0_-4px_12px_rgba(0,0,0,0.03)]">
                <div className="max-w-5xl mx-auto">
                  <div className="flex justify-between items-center mb-6">
                    <button onClick={() => setShowAllLinkRows(!showAllLinkRows)} className={`px-4 py-1.5 rounded text-[10px] font-bold transition-all border uppercase tracking-wider ${showAllLinkRows ? 'bg-blue-600 text-white border-blue-600 shadow-lg shadow-blue-100' : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300 shadow-sm'}`}>
                      {showAllLinkRows ? '✓ Displaying All Entries' : 'Show Complete Inventory'}
                    </button>
                    {currentAnnotationRelation && (
                      <div className="text-[10px] font-bold text-blue-600 px-3 py-1.5 rounded bg-blue-50 border border-blue-100 uppercase tracking-tight">Active: {currentAnnotationRelation.textContext.text}</div>
                    )}
                  </div>
                  <RelationshipBuilderPanel
                    annotations={showAllLinkRows ? filteredLinkAnnotations : (currentAnnotationRelation ? [currentAnnotationRelation] : [])}
                    handleSelectCell={(a, type) => {
                      if (isReadOnly) return;
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
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-12 bg-slate-50/30">
              <div className="max-w-4xl mx-auto bg-white shadow-sm border border-slate-200 min-h-full pb-32">
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
              </div>
            </div>
          )}

          {/* Bottom Drawer: Metadata */}
          {metaView !== 'none' && (
            <div className="h-1/3 bg-slate-900 text-slate-300 border-t border-slate-800 overflow-y-auto p-8 animate-in slide-in-from-bottom-full duration-300 shadow-2xl">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xs font-bold text-white uppercase tracking-[0.2em]">{metaView} Reference</h3>
                <button onClick={() => setMetaView('none')} className="text-slate-500 hover:text-white font-bold p-2 transition-colors">✕</button>
              </div>
              <div className="prose prose-invert prose-sm max-w-none bg-slate-800/50 p-8 rounded border border-slate-700/50 shadow-inner leading-relaxed" dangerouslySetInnerHTML={{ __html: doc.meta[metaView] || 'No data available' }} />
            </div>
          )}
        </main>
      </div>

      {/* --- Modals & Context --- */}
      {showFinishConfirm && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded shadow-2xl max-w-sm w-full p-8 border border-slate-200">
            <div className="text-center">
              <h3 className="text-lg font-bold text-slate-900 mb-2 uppercase tracking-tight">Unsaved Session</h3>
              <p className="text-sm text-slate-500 mb-8 font-medium leading-relaxed">System has detected pending modifications. How would you like to proceed?</p>
              <div className="grid grid-cols-1 gap-2">
                <button onClick={() => handleSave(true)} className="bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded text-xs font-bold uppercase tracking-widest transition-all shadow-md">Commit & Exit</button>
                <button onClick={() => window.close()} className="bg-white border border-slate-200 hover:bg-red-50 hover:text-red-600 text-slate-500 py-2.5 rounded text-xs font-bold uppercase tracking-widest transition-all">Discard & Exit</button>
                <button onClick={() => setShowFinishConfirm(false)} className="mt-4 text-[10px] font-bold text-slate-400 hover:text-slate-600 uppercase tracking-widest">Back to Review</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {unifiedContextMenu.visible && !isReadOnly && (
        <UnifiedContextMenuDisplay
          contextMenu={unifiedContextMenu} annotationOptions={annotationOptions} optionColors={optionColors}
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
