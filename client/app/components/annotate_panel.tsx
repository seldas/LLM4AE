// annotate_panel.tsx
'use client';

import { useState, useReducer, useEffect, useRef, useMemo, JSX, ReactNode } from 'react';
import { docReducer, initialDocState, DocActionTypes, LoadDocAction } from '../lib/doc-reducer';
import {
  Annotation,
  AnnotationOptions,
  TextContext,
  AnnotationGuideline,
  ContextMenu
} from '../lib/interfaces';
import { getHistoryFile, getCaseById, createAnnotation, updateAnnotation, deleteAnnotation, getCaseAnnotations } from '../lib/api';
import {  
  escapeRegExp,
  generateOptionColors,
  API_BASE
} from '../lib/util';

import ExcelJS from 'exceljs';
import UnifiedContextMenuDisplay from '../components/context-menus/unified-context-menu';
import AnnotationPanel from '../components/annotation-panel';
import PageDisplay from '../components/page-display-brat';
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
const IconJSON = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"/></svg>;
const IconExcel = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>;
const IconExit = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>;
const IconSparkles = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>;
const IconRobot = () => <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/></svg>;

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
  const [activeLayers, setActiveLayers] = useState<string[]>(['Human', 'LLM', 'BERT']);
  const [theme, setTheme] = useState<'light' | 'dark' | 'soft'>('light');
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [userRole, setUserRole] = useState<string>("Anonymous");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
  const [isTemporaryMode, setIsTemporaryMode] = useState(false);

  const [activeLeftTab, setActiveLeftTab] = useState<'annotations' | 'history'>('annotations');
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);

  const [isProcessingLlm, setIsProcessingLlm] = useState(false);
  const [isProcessingBert, setIsProcessingBert] = useState(false);

  const META_DATA_OPTIONS: Array<{ key: 'demographic' | 'products' | 'outcomes'; label: string }> = [
    { key: 'demographic', label: 'Demographic' },
    { key: 'products', label: 'Products' },
    { key: 'outcomes', label: 'Outcomes' },
  ];
  type MetaEntryType = 'demographic-structured' | 'products-structured' | 'outcomes-structured' | 'legacy';
  interface MetaEntry {
    key: 'demographic' | 'products' | 'outcomes';
    label: string;
    type: MetaEntryType;
    html?: string;
    data?: any;
  }
  const [metaView, setMetaView] = useState<'none' | 'demographic' | 'products' | 'outcomes'>('none');
  const availableMetaEntries = useMemo(() => {
    const meta = doc.meta || {};
    const entries: MetaEntry[] = [];
    META_DATA_OPTIONS.forEach(({ key, label }) => {
      const raw = (meta as any)[key];
      if (key === 'demographic') {
        if (Array.isArray(raw) && raw.length) {
          entries.push({ key, label, type: 'demographic-structured', data: raw });
          return;
        }
      } else if (key === 'products') {
        if (raw && typeof raw === 'object' && Array.isArray(raw.groups) && raw.groups.length) {
          entries.push({ key, label, type: 'products-structured', data: raw });
          return;
        }
      } else if (key === 'outcomes') {
        if (Array.isArray(raw) && raw.length) {
          entries.push({ key, label, type: 'outcomes-structured', data: raw });
          return;
        }
      }
      
      if (raw && typeof raw === 'string' && raw.trim()) {
        entries.push({ key, label, type: 'legacy', html: raw });
      }
    });
    return entries;
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
        // If no project provided, it's temporary mode from AskMyFAERS
        if (!overrideProject) {
            setIsTemporaryMode(true);
            setUserRole("ICSR_Annotator");
        } else {
            setUserRole("Anonymous");
        }
    }
  }, [overrideProject]);

  const [activeLabelFilters, setActiveLabelFilters] = useState<string[]>([]);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [showFinishConfirm, setShowFinishConfirm] = useState(false);
  const [llmPopup, setLlmPopup] = useState<{
    visible: boolean;
    x: number;
    y: number;
    text: string;
    start: number;
    end: number;
    label?: string;
    type?: 'LLM' | 'BERT' | 'SME' | 'NEW';
    note?: string;
    isVerified?: boolean;
  }>({ visible: false, x: 0, y: 0, text: '', start: 0, end: 0 });

  const [unifiedContextMenu, setUnifiedContextMenu] = useState<ContextMenu>({
    visible: false,
    x: 0,
    y: 0,
    type: 'annotation',
    start: undefined,
    end: undefined
  });

  const [selectedPopupLabel, setSelectedPopupLabel] = useState<string>('');
  const [selectedTermContext, setSelectedTermContext] = useState<TextContext | null>(null);
  const [annotationGuidelines, setAnnotationGuidelines] = useState<AnnotationGuideline[]>([]);

  useEffect(() => {
    async function loadData() {
      if (!overrideId) return;
      console.log(`Fetching data for case ID: ${overrideId}`);
      const data = await getCaseById(overrideId);
      if (data) {
        console.log(`Loaded case data. Annotations count: ${data.annotations?.length || 0}`);
        dispatch({ type: DocActionTypes.LOAD, payload: data as LoadDocAction['payload'] });
        
        // Lazy load more annotations if total_annotations > initially loaded (500)
        if (data.total_annotations > 500) {
          const total = data.total_annotations;
          const limit = 500;
          for (let offset = 500; offset < total; offset += limit) {
            const moreAnnos = await getCaseAnnotations(parseInt(overrideId), limit, offset);
            if (moreAnnos) {
              dispatch({ type: DocActionTypes.APPEND_ANNOTATIONS, payload: { annotations: moreAnnos } });
            }
          }
        }
      }
    }
    loadData();
  }, [overrideId, overrideProject]);

  const currentPageData = useMemo(() => doc.pages[doc.currentPageIndex] || '', [doc.pages, doc.currentPageIndex]);

  // Structured Metadata Renderer
  const renderStructuredMeta = (entry: MetaEntry) => {
    if (entry.type === 'legacy') return <div dangerouslySetInnerHTML={{ __html: entry.html || '' }} className="prose prose-slate prose-sm max-w-none" />;
    
    const data = entry.data;
    if (!data) return null;

    if (entry.key === 'demographic') {
      return (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {data.map((item: any, i: number) => {
            const value = item.value || 'N/A';
            const isUrl = typeof value === 'string' && (value.startsWith('http://') || value.startsWith('https://'));
            return (
              <div key={i} className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                <div className="text-[9px] font-bold text-slate-400 uppercase tracking-tight">{item.label || 'Field'}</div>
                <div className="text-xs font-bold text-slate-700 mt-1">
                  {isUrl ? (
                    <a href={value} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center gap-1">
                      <span>Click to Open</span>
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>
                  ) : (
                    value
                  )}
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    if (entry.key === 'products') {
      return (
        <div className="space-y-6">
          {(data.groups || []).map((group: any, i: number) => (
            <div key={i} className="border border-slate-100 rounded-xl overflow-hidden bg-white shadow-sm">
              <div className="bg-slate-50 px-4 py-2 border-b border-slate-100 flex items-center justify-between">
                <h4 className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{group.role || 'Product Group'}</h4>
                <span className="text-[9px] font-bold px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">{group.products?.length || 0} ITEMS</span>
              </div>
              <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {(group.products || []).map((prod: any, j: number) => (
                  <div key={j} className="p-3 bg-slate-50/50 rounded-lg border border-slate-100/50">
                    <div className="text-xs font-bold text-slate-800">{prod.name}</div>
                    {prod.details && <div className="text-[10px] text-slate-500 mt-1 leading-relaxed italic">{prod.details}</div>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      );
    }

    if (entry.key === 'outcomes') {
      return (
        <div className="flex flex-wrap gap-2">
          {data.map((outcome: string, i: number) => (
            <span key={i} className="px-3 py-1.5 bg-red-50 text-red-700 border border-red-100 rounded-full text-[10px] font-bold uppercase tracking-tight">
              {outcome}
            </span>
          ))}
        </div>
      );
    }

    return <pre className="bg-slate-50 p-4 rounded text-[10px] overflow-x-auto">{JSON.stringify(data, null, 2)}</pre>;
  };

  const annotationOptions: AnnotationOptions[] = useMemo(() => [
    { label: 'AE', color: '#ef4444' },
    { label: 'SDRUG', color: '#3b82f6' },
    { label: 'CDRUG', color: '#8b5cf6' },
    { label: 'ODRUG', color: '#6366f1' },
    { label: 'TREATMENT', color: '#10b981' },
    { label: 'DIAGNOSTIC', color: '#f59e0b' },
    { label: 'MEDICAL HISTORY', color: '#ec4899' },
    { label: 'TEMPORAL', color: '#64748b' },
    { label: 'AGE', color: '#14b8a6' },
    { label: 'SEX', color: '#f43f5e' },
    { label: 'CAUSE OF DEATH', color: '#44403c' },
  ], []);

  const optionColors = useMemo(() => {
    const colors: Record<string, string> = {};
    annotationOptions.forEach(opt => { colors[opt.label] = opt.color; });
    return colors;
  }, [annotationOptions]);

  const visibleAnnotations = useMemo(() => {
    return doc.annotations.filter(a => {
      const isLlm = a.note.includes('LLM');
      const isBert = a.note.includes('BERT');
      if (isLlm && !activeLayers.includes('LLM')) return false;
      if (isBert && !activeLayers.includes('BERT')) return false;
      if (!isLlm && !isBert && !activeLayers.includes('Human')) return false;
      return true;
    });
  }, [doc.annotations, activeLayers]);

  const handleTextSelection = (e?: any, startOffset?: number, endOffset?: number) => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length > 0) {
      const text = selection.toString();
      setSelectedText(text);

      if (e) {
        setUnifiedContextMenu({
          visible: true,
          x: e.clientX,
          y: e.clientY,
          type: 'annotation',
          start: startOffset,
          end: endOffset
        });
      }
    }
  };

  const onClickAnnotation = (anno: Annotation, x: number, y: number) => {
    const isLlm = anno.note.includes('LLM');
    const isBert = anno.note.includes('BERT');
    const isVerified = anno.note.includes('VERIFIED');

    setLlmPopup({
      visible: true,
      x, y,
      text: anno.textContext.text,
      start: anno.textContext.start ?? 0,
      end: anno.textContext.end ?? 0,
      label: anno.label,
      type: isLlm ? 'LLM' : isBert ? 'BERT' : 'SME',
      note: anno.note,
      isVerified
    });
    setSelectedTermContext(anno.textContext);
  };

  useEffect(() => {
    setHasUnsavedChanges(doc.actionHistory.length > 0);
  }, [doc.actionHistory.length]);

  const handleSave = async (shouldClose = false) => {
      // Incremental saving is done during actions. 
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      if (shouldClose) window.close();
  };

  const handleExportJSON = () => {
    const dataStr = JSON.stringify(doc.annotations, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const id = overrideId || 'unknown';
    anchor.download = `annotations_${id}_${timestamp}.json`;
    anchor.click();
    window.URL.revokeObjectURL(url);
  };

  const handleExportExcel = async () => {
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
          start: anno.textContext.start ?? 0, 
          end: anno.textContext.end ?? 0, 
          page: (anno.textContext.page ?? 0) + 1, 
          note: anno.note 
      });
    });
    const buffer = await workbook.xlsx.writeBuffer();
    const blob = new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const id = overrideId || 'unknown';
    anchor.download = `annotations_${id}_${timestamp}.xlsx`;
    anchor.click();
    window.URL.revokeObjectURL(url);
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
        body: JSON.stringify({ id: overrideId })
      });
      if (!res.ok) throw new Error('Failed to start LLM annotation');
      alert("LLM Annotation started. It will refresh automatically when done.");
    } catch (err) {
      console.error(err);
      alert("Error starting LLM annotation");
    } finally {
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
        body: JSON.stringify({ id: overrideId })
      });
      if (!res.ok) throw new Error('Failed to start BERT annotation');
      alert("BERT Annotation started. It will refresh automatically when done.");
    } catch (err) {
      console.error(err);
      alert("Error starting BERT annotation");
    } finally {
      setIsProcessingBert(false);
    }
  };

  const handleAddAnnotation = async (label: string) => {
      if (isReadOnly) return;
      try {
        const response = await createAnnotation({
          case_id: parseInt(overrideId || '0'),
          label: label,
          start: unifiedContextMenu.start as number,
          end: unifiedContextMenu.end as number,
          text: selectedText,
          note: userRole
        });
        const newAnnotation: Annotation = {
          id: response.id,
          label,
          textContext: {
            text: selectedText,
            start: unifiedContextMenu.start as number,
            end: unifiedContextMenu.end as number,
            page: doc.currentPageIndex
          },
          note: userRole,
          relationships: {}
        };
        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation, historyType: 'add' } });
        setUnifiedContextMenu(prev => ({ ...prev, visible: false }));
      } catch (err) {
        console.error("Add error:", err);
      }
  };

  const handleVerifyAnnotation = async (start: number, end: number, text: string, label: string) => {
    if (isReadOnly) return;
    const existingAI = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert') || a.note.toUpperCase().includes('IMPORTED')));
    if (existingAI && existingAI.id) {
      try {
        const newNote = `${existingAI.note} | VERIFIED BY ${userRole}`;
        await updateAnnotation(existingAI.id, { note: newNote });

        const updatedAI = { ...existingAI, note: newNote };
        dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAI, historyType: 'verify' } });

        const response = await createAnnotation({
          case_id: parseInt(overrideId || '0'),
          label: label,
          start, end, text,
          note: userRole
        });
        const humanAnnotation: Annotation = {
          id: response.id,
          label,
          textContext: { text, start, end, page: doc.currentPageIndex },
          note: userRole,
          relationships: {}
        };
        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: humanAnnotation, historyType: 'verify' } });
        setLlmPopup(prev => ({ ...prev, visible: false }));
        setSelectedTermContext(null);
      } catch (err) {
        console.error("Verify error:", err);
      }
    }
  };

  const handleRejectAnnotation = async (start: number, end: number, label: string) => {
    if (isReadOnly) return;
    const existing = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()));
    if (existing && existing.id) {
      try {
        const newNote = `${existing.note} | REJECTED BY ${userRole}`;
        await updateAnnotation(existing.id, { note: newNote });

        const updatedAnnotation = { ...existing, note: newNote };
        dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAnnotation, historyType: 'reject' } });
        setLlmPopup(prev => ({ ...prev, visible: false }));
        setSelectedTermContext(null);
      } catch (err) {
        console.error("Reject error:", err);
      }
    }
  };

  const handleLlmAddAnnotation = async (labelOverride?: string) => {
    if (isReadOnly) return;
    const { start, end, text } = llmPopup;
    const label = labelOverride || selectedPopupLabel;

    try {
        const response = await createAnnotation({
          case_id: parseInt(overrideId || '0'),
          label: label,
          start, end, text,
          note: userRole
        });
        const newAnnotation: Annotation = {
          id: response.id,
          label,
          textContext: { text, start, end, page: doc.currentPageIndex },
          note: userRole,
          relationships: {}
        };

        if (label === llmPopup.label) {
          const existingAI = doc.annotations.find(a => 
            a.textContext.start === start && a.textContext.end === end && 
            (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) &&
            (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert') || a.note.toUpperCase().includes('IMPORTED'))
          );
          if (existingAI && existingAI.id) {
            const newNote = `${existingAI.note} | VERIFIED BY ${userRole}`;
            await updateAnnotation(existingAI.id, { note: newNote });
            const updatedAI = { ...existingAI, note: newNote };
            dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updatedAI, historyType: 'verify' } });
          }
        }
        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation, historyType: 'add' } });
        setLlmPopup(prev => ({ ...prev, visible: false }));
        setSelectedTermContext(null);
    } catch (err) {
      console.error("Add from popup error:", err);
    }
  };

  const handleUnverifyAnnotation = async (start: number, end: number, labelStr: string) => {
    if (isReadOnly) return;
    const humanAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && a.note === userRole);
    const aiAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert') || a.note.toUpperCase().includes('IMPORTED')) && a.note.toUpperCase().includes('VERIFIED'));

    try {
        if (aiAnno && aiAnno.id) {
          const revertedAiNote = aiAnno.note.split(' | VERIFIED BY')[0];
          await updateAnnotation(aiAnno.id, { note: revertedAiNote });
          const revertedAi = { ...aiAnno, note: revertedAiNote };
          dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: revertedAi } });
        }
        if (humanAnno && humanAnno.id) {
          await deleteAnnotation(humanAnno.id);
          dispatch({ type: DocActionTypes.REMOVE_ANNOTATION, payload: { annotation: humanAnno } });
        }
        setLlmPopup(prev => ({ ...prev, visible: false }));
        setSelectedTermContext(null);
    } catch (err) {
      console.error("Unverify error:", err);
    }
  };

  useEffect(() => {
    async function loadGuidelines() {
      try {
        const res = await fetch(`${API_BASE}/annotation-guidelines`);
        if (res.ok) setAnnotationGuidelines(await res.json());
      } catch (err) { console.error("Guidelines load fail:", err); }
    }
    loadGuidelines();
  }, []);

  const handleRefresh = async () => {
    if (!overrideId) return;
    const data = await getCaseById(overrideId);
    if (data) {
      dispatch({ type: DocActionTypes.LOAD, payload: data as LoadDocAction['payload'] });
    }
  };

  return (
    <div className={`app-container h-screen overflow-hidden flex flex-col transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-950 text-slate-100' : theme === 'soft' ? 'bg-[#eee8d5] text-[#657b83]' : 'bg-slate-50 text-slate-900'} antialiased`}>

      {/* --- Unified Header --- */}
      <header className={`border-b h-14 px-4 sm:px-6 flex items-center justify-between shadow-sm z-30 shrink-0 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
        <div className="flex items-center gap-3 sm:gap-8">
          <button 
            onClick={() => setLeftSidebarOpen(!leftSidebarOpen)}
            className={`p-1.5 rounded-lg transition-colors ${theme === 'dark' ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'}`}
            title="Toggle Sidebar"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
          </button>

          <div className="flex items-center gap-2.5">
            <div className="w-2.5 h-2.5 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
            <h1 className="text-sm font-black tracking-widest uppercase hidden sm:block">LLM4AE</h1>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <button
                onClick={handleExportJSON}
                className={`flex items-center gap-2 px-2 sm:px-3 py-1.5 rounded text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-colors ${theme === 'dark' ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'}`}
                title="Download Annotations as JSON"
            >
                <IconJSON /> <span className="hidden xs:inline">JSON</span>
            </button>
            <button
                onClick={handleExportExcel}
                className={`flex items-center gap-2 px-2 sm:px-3 py-1.5 rounded text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-colors ${theme === 'dark' ? 'hover:bg-slate-800 text-slate-400' : 'hover:bg-slate-100 text-slate-500'}`}
                title="Download Annotations as Excel"
            >
                <IconExcel /> <span className="hidden xs:inline">Excel</span>
            </button>
          </div>
        </div>

        <div className="flex items-center gap-3 sm:gap-6">
          {/* User Display */}
          {isLoggedIn && currentUser && !isTemporaryMode && (
            <div className={`hidden md:flex items-center gap-3 border-r pr-6 ${theme === 'dark' ? 'border-slate-800' : theme === 'soft' ? 'border-[#eee8d5]' : 'border-slate-200'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center border overflow-hidden ${theme === 'dark' ? 'bg-slate-800 border-slate-700 text-slate-400' : 'bg-slate-100 border-slate-200 text-slate-500'}`}>
                <span className="text-xs font-bold">{currentUser.username?.[0].toUpperCase()}</span>
              </div>
              <div className="flex flex-col">
                <span className={`text-[10px] font-bold leading-none ${theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}`}>{currentUser.full_name || currentUser.username}</span>
                <span className="text-[9px] font-medium text-slate-400 mt-0.5 uppercase tracking-tighter">{isReadOnly ? 'Viewer' : 'Expert'}</span>
              </div>
            </div>
          )}

          <button onClick={() => window.close()} className="flex items-center gap-2 px-3 py-1.5 hover:bg-red-50 text-red-600 hover:text-red-700 rounded text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-all">
            <IconExit /> <span className="hidden xs:inline">Close</span>
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar */}
        <aside className={`${leftSidebarOpen ? 'w-80 sm:w-85' : 'w-0'} bg-white border-r flex flex-col shrink-0 transition-all duration-300 overflow-hidden z-40 shadow-xl sm:shadow-none absolute sm:relative h-full sm:h-auto ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
          <div className={`p-4 sm:p-5 border-b shrink-0 ${theme === 'dark' ? 'border-slate-800 bg-slate-900/50' : theme === 'soft' ? 'border-[#eee8d5] bg-[#fdf6e3]/50' : 'border-slate-100 bg-slate-50/50'}`}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Document</h2>
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-tighter ${isReadOnly ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                {isReadOnly ? 'Read Only' : 'Editing'}
              </span>
            </div>
            <div className="space-y-1">
              <div className={`text-sm font-black truncate ${theme === 'dark' ? 'text-slate-200' : 'text-slate-900'}`}>CASE: {overrideId || 'None'}</div>
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></span>
                Project: {overrideProject || 'tempo'}
              </div>
            </div>
            
            {/* AI Tools */}
            {!isReadOnly && (
              <div className="mt-5 grid grid-cols-2 gap-2">
                <button
                  onClick={handleLlmAnnotate}
                  disabled={isProcessingLlm || doc.status.llm_status === 'working'}
                  className="flex items-center justify-center gap-2 py-2 px-3 rounded bg-indigo-600 hover:bg-indigo-700 text-white text-[10px] font-bold uppercase tracking-wider transition-all disabled:opacity-50 shadow-sm"
                >
                  <IconSparkles /> vLLM
                </button>
                <button
                  onClick={handleBertAnnotate}
                  disabled={isProcessingBert || doc.status.bert_status === 'working'}
                  className="flex items-center justify-center gap-2 py-2 px-3 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-[10px] font-bold uppercase tracking-wider transition-all disabled:opacity-50 shadow-sm"
                >
                  <IconRobot /> BERT
                </button>
              </div>
            )}
            <div className="mt-2">
                <button
                  onClick={handleRefresh}
                  className={`w-full flex items-center justify-center gap-2 py-2 px-3 rounded border text-[10px] font-bold uppercase tracking-wider transition-all shadow-sm ${theme === 'dark' ? 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700' : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'}`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                  Sync Status
                </button>
            </div>
          </div>

          <div className="flex-1 overflow-hidden flex flex-col">
            <div className={`flex border-b ${theme === 'dark' ? 'border-slate-800' : theme === 'soft' ? 'border-[#eee8d5]' : 'border-slate-100'}`}>
               <button 
                 onClick={() => setActiveLeftTab('annotations')}
                 className={`flex-1 py-3 text-[10px] font-black uppercase tracking-widest transition-all ${activeLeftTab === 'annotations' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/10' : 'text-slate-400 hover:text-slate-600'}`}
               >
                 Annotations
               </button>
               <button 
                 onClick={() => setActiveLeftTab('history')}
                 className={`flex-1 py-3 text-[10px] font-black uppercase tracking-widest transition-all ${activeLeftTab === 'history' ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50/10' : 'text-slate-400 hover:text-slate-600'}`}
               >
                 History
               </button>
            </div>
            
            <div className="flex-1 overflow-y-auto custom-scrollbar">
              {activeLeftTab === 'annotations' ? (
                <AnnotationPanel
                  annotations={doc.annotations}
                  currentPage={doc.currentPageIndex}
                  optionColors={optionColors}
                  onFilterChange={setActiveLabelFilters}
                  activeLayers={activeLayers}
                  isReadOnly={isReadOnly}
                  pageData={currentPageData}
                  selectedTermContext={selectedTermContext}
                  setSelectedTermContext={setSelectedTermContext}
                  handleRemoveAnnotation={(ann) => handleRejectAnnotation(ann.textContext.start ?? 0, ann.textContext.end ?? 0, ann.label)}
                />
              ) : (
                <ActionHistoryPanel 
                  history={doc.actionHistory} 
                  onUndo={(id) => dispatch({ type: DocActionTypes.UNDO_ACTION, payload: { actionId: id } })}
                  optionColors={optionColors}
                />
              )}
            </div>
          </div>
        </aside>

        {/* Backdrop for mobile */}
        {leftSidebarOpen && (
          <div 
            className="sm:hidden fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-30"
            onClick={() => setLeftSidebarOpen(false)}
          ></div>
        )}

        {/* Main Workspace */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Sub-Header: Toolbar */}
          <div className={`h-12 border-b px-4 sm:px-6 flex items-center justify-between z-20 shrink-0 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
            <div className="flex items-center gap-4 sm:gap-8 overflow-x-auto no-scrollbar py-2">
              <div className="flex items-center gap-1.5 shrink-0">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hidden xs:inline">Metadata:</span>
                <div className="flex gap-1">
                  {availableMetaEntries.map(entry => (
                    <button
                      key={entry.key}
                      onClick={() => setMetaView(metaView === entry.key ? 'none' : entry.key)}
                      className={`px-2.5 py-1 rounded text-[9px] font-bold uppercase transition-all shadow-sm ${metaView === entry.key ? 'bg-blue-600 text-white' : (theme === 'dark' ? 'bg-slate-800 text-slate-400 hover:bg-slate-700' : 'bg-slate-100 text-slate-500 hover:bg-slate-200')}`}
                    >
                      {entry.label}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="h-4 w-px bg-slate-200 shrink-0 hidden xs:block"></div>

              <div className="flex items-center gap-4 shrink-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hidden lg:inline">Layers:</span>
                  <div className={`flex p-0.5 rounded-lg border gap-0.5 ${theme === 'dark' ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                    {['Human', 'LLM', 'BERT'].map(layer => (
                    <button
                      key={layer}
                      onClick={() => handleLayerToggle(layer)}
                      className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase transition-all ${activeLayers.includes(layer) ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                    >
                      {layer}
                    </button>
                  ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 shrink-0">
                <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest hidden xl:inline">Theme:</span>
                    <div className={`flex p-0.5 rounded-lg border gap-0.5 ${theme === 'dark' ? 'bg-slate-950 border-slate-800' : 'bg-slate-50 border-slate-200'}`}>
                        {['light', 'dark', 'soft'].map(t => (
                        <button
                            key={t}
                            onClick={() => setTheme(t as any)}
                            className={`px-2 py-0.5 rounded-md text-[9px] font-bold uppercase transition-all ${theme === t ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}
                        >
                            {t}
                        </button>
                        ))}
                    </div>
                </div>
            </div>
          </div>

          <main className="flex-1 flex flex-col overflow-hidden relative">
            {/* Metadata Overlay */}
            {metaView !== 'none' && (
              <>
                <div 
                  className="absolute inset-0 z-10" 
                  onClick={() => setMetaView('none')}
                ></div>
                <div className={`absolute top-0 left-0 right-0 max-h-[60%] shadow-2xl z-20 overflow-y-auto animate-in slide-in-from-top duration-300 border-b ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
                  <div className="p-4 sm:p-8">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </div>
                        <div>
                            <h3 className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] leading-none mb-1">Case Metadata</h3>
                            <div className={`text-lg font-black uppercase tracking-tight ${theme === 'dark' ? 'text-slate-100' : 'text-slate-800'}`}>
                                {availableMetaEntries.find(e => e.key === metaView)?.label} Information
                            </div>
                        </div>
                    </div>
                    <button 
                      onClick={() => setMetaView('none')} 
                      className={`p-2 rounded-full transition-colors ${theme === 'dark' ? 'hover:bg-slate-800 text-slate-500' : 'hover:bg-slate-100 text-slate-400'}`}
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                  </div>
                  
                  <div className="animate-in fade-in zoom-in-95 duration-300">
                    {(() => {
                      const entry = availableMetaEntries.find(e => e.key === metaView);
                      if (!entry) return null;
                      return renderStructuredMeta(entry);
                    })()}
                  </div>
                </div>
              </div>
            </>
          )}

            <div className={`flex-1 overflow-y-auto p-4 sm:p-8 lg:p-12 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-950' : theme === 'soft' ? 'bg-[#eee8d5]' : 'bg-slate-50/30'}`}>
              <div className={`max-w-4xl mx-auto shadow-xl border min-h-full pb-32 transition-colors duration-300 ${theme === 'dark' ? 'bg-slate-900 border-slate-800' : theme === 'soft' ? 'bg-[#fdf6e3] border-[#eee8d5]' : 'bg-white border-slate-200'}`}>
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
                  onAnnotationClick={onClickAnnotation}
                  selectedTermContext={selectedTermContext}
                  setSelectedTermContext={setSelectedTermContext}
                  isReadOnly={isReadOnly}
                  theme={theme}
                />
              </div>
            </div>
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
          handleAddRelationship={() => {}}
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
