// annotate_panel.tsx
'use client';

import { useState, useReducer, useEffect, useRef, useMemo, JSX, ReactNode } from 'react';
import { io } from 'socket.io-client';
import { docReducer, initialDocState, DocActionTypes, LoadDocAction } from '../lib/doc-reducer';
import {
  Annotation,
  AnnotationOptions,
  AnnotationRelationships,
  TextContext,
  AnnotationGuideline
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

  const [relationshipBuilderMode, setRelationshipBuilderMode] = useState(false);
  const [currentRelationType, setCurrentRelationType] = useState<keyof AnnotationRelationships | null>(null);
  const [currentAnnotationRelation, setCurrentAnnotationRelation] = useState<Annotation | null>(null);

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
    type?: string;
    note?: string;
    isVerified?: boolean;
  }>({ visible: false, x: 0, y: 0, text: '', start: 0, end: 0 });

  const [unifiedContextMenu, setUnifiedContextMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    start: number | null;
    end: number | null;
  }>({ visible: false, x: 0, y: 0, start: null, end: null });

  const [selectedPopupLabel, setSelectedPopupLabel] = useState<string>('');
  const [selectedTermContext, setSelectedTermContext] = useState<TextContext | null>(null);
  const [annotationGuidelines, setAnnotationGuidelines] = useState<AnnotationGuideline[]>([]);

  useEffect(() => {
    async function loadData() {
      if (!overrideId) return;
      const data = await getCaseById(overrideId);
      if (data) {
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

  const linkModeColors = {
      'Latency': '#6366f1',
      'Duration': '#8b5cf6',
      'Frequency': '#ec4899',
      'Route': '#10b981',
      'Dose': '#f59e0b',
      'Verification': '#14b8a6',
      'Condition': '#64748b'
  };

  const filteredLinkAnnotations = useMemo(() => {
    if (!relationshipBuilderMode) return [];
    return doc.annotations.filter(a => activeLayers.includes(a.note.includes('LLM') ? 'LLM' : a.note.includes('BERT') ? 'BERT' : 'Human'));
  }, [doc.annotations, activeLayers, relationshipBuilderMode]);

  const temporalTerms = useMemo(() => {
    return doc.annotations.filter(a => TEMPORAL_LABELS.has(a.label.toUpperCase()));
  }, [doc.annotations]);

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

  const handleTextSelection = (e?: any) => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length > 0) {
      const range = selection.getRangeAt(0);
      const text = selection.toString();
      setSelectedText(text);

      if (e) {
        setUnifiedContextMenu({
          visible: true,
          x: e.clientX,
          y: e.clientY,
          start: 0, // Injected by PageDisplay
          end: 0    // Injected by PageDisplay
        });
      }
    }
  };

  const onClickAnnotation = (anno: Annotation, x: number, y: number) => {
    const isAi = anno.note.includes('LLM') || anno.note.includes('BERT') || anno.note.includes('AI');
    const isVerified = anno.note.includes('VERIFIED');

    setLlmPopup({
      visible: true,
      x, y,
      text: anno.textContext.text,
      start: anno.textContext.start ?? 0,
      end: anno.textContext.end ?? 0,
      label: anno.label,
      type: anno.label,
      note: anno.note,
      isVerified
    });
    setSelectedTermContext(anno.textContext);
  };

  const onClickLinkAnnotation = (anno: Annotation) => {
      if (currentRelationType && currentAnnotationRelation) {
          // Use the ID of the target annotation for the relationship
          const updated = { 
            ...currentAnnotationRelation, 
            relationships: { 
              ...currentAnnotationRelation.relationships, 
              [currentRelationType]: anno.id 
            } 
          };
          dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updated, historyType: 'verify' } });
          setCurrentRelationType(null);
      } else {
          setCurrentAnnotationRelation(anno);
      }
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
      // Incremental saving is done during actions. 
      // This is now more of a "Commit" or "Sync" if we had a local buffer.
      // For now, we'll just show success since actions are synced.
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      if (shouldClose) window.close();
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

  const [presenceUsers, setPresenceUsers] = useState<string[]>([]);

  // Websocket status updates and presence
  useEffect(() => {
    if (!overrideId || !currentUser) return;
    
    // Connect to the socket through the proxy
    const socketPath = API_BASE.replace(/\/api$/, '') + '/socket.io';
    const socket = io(window.location.origin, { 
      path: socketPath,
      transports: ['websocket', 'polling']
    });
    
    // Join the case room for presence tracking
    socket.emit('join_case', {
        case_id: parseInt(overrideId),
        user_id: currentUser.id,
        username: currentUser.full_name || currentUser.username
    });

    socket.on('presence_update', (data: { case_id: number, users: string[] }) => {
        if (data.case_id === parseInt(overrideId)) {
            setPresenceUsers(data.users);
        }
    });

    socket.on('status_update', async (update: { case_id: number, llm_status?: string, bert_status?: string }) => {
      if (update.case_id === parseInt(overrideId)) {
        console.log("Received status update via websocket:", update);
        if (update.llm_status === 'Done' || update.bert_status === 'Done' || update.llm_status === 'working' || update.bert_status === 'working') {
           // Reload case data to get latest status and annotations
           const data = await getCaseById(overrideId);
           if (data) {
             dispatch({ type: DocActionTypes.LOAD, payload: data as LoadDocAction['payload'] });
           }
        }
      }
    });

    return () => {
      socket.emit('leave_case', {
          case_id: parseInt(overrideId),
          user_id: currentUser.id
      });
      socket.disconnect();
    };
  }, [overrideId, API_BASE, currentUser]);

  return (
    <div className="app-container h-screen overflow-hidden flex flex-col bg-slate-50 text-slate-900 antialiased">

      {/* --- Unified Header --- */}
      <header className="bg-white border-b border-slate-200 h-14 px-6 flex items-center justify-between shadow-sm z-30 shrink-0">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2.5">
            <div className="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
            <h1 className="text-sm font-bold text-slate-900 tracking-widest uppercase">LLM4AE</h1>
          </div>

          <div className="flex items-center gap-4">
            <button
                onClick={handleExport}
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
          {/* User Display - Hide in Temporary Mode */}
          {isLoggedIn && currentUser && !isTemporaryMode && (
            <div className="flex items-center gap-3 border-r border-slate-200 pr-6">
              <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center border border-slate-200 overflow-hidden">
                <span className="text-xs font-bold text-slate-500">{currentUser.username?.[0].toUpperCase()}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-bold text-slate-900 leading-none">{currentUser.full_name || currentUser.username}</span>
                <span className="text-[9px] font-medium text-slate-400 mt-0.5 uppercase tracking-tighter">{isReadOnly ? 'Viewer' : 'Expert Annotator'}</span>
              </div>
            </div>
          )}

          <button onClick={() => window.close()} className="flex items-center gap-2 px-3 py-1.5 hover:bg-red-50 text-red-600 hover:text-red-700 rounded text-[11px] font-bold uppercase tracking-wider transition-all">
            <IconExit /> Close
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-80 bg-white border-r border-slate-200 flex flex-col shrink-0">
          <div className="p-5 border-b border-slate-100 bg-slate-50/50">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Document</h2>
              <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-tighter ${isReadOnly ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'}`}>
                {isReadOnly ? 'Read Only' : 'Editing'}
              </span>
            </div>
            <div className="space-y-1">
              <div className="text-sm font-bold text-slate-900 truncate">CASE ID: {overrideId || 'None'}</div>
              <div className="text-[10px] font-medium text-slate-400 uppercase tracking-tight flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 bg-slate-300 rounded-full"></span>
                Project: {overrideProject || 'tempo'}
              </div>
            </div>
            
            {/* AI Tools */}
            {!isReadOnly && (
              <div className="mt-5 grid grid-cols-2 gap-2">
                <button
                  onClick={handleLlmAnnotate}
                  disabled={isProcessingLlm || doc.status.llm_status === 'working'}
                  className="flex items-center justify-center gap-2 py-2 px-3 rounded bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-[10px] font-bold uppercase tracking-wider transition-all disabled:opacity-50 border border-indigo-100"
                >
                  <IconSparkles /> vLLM
                </button>
                <button
                  onClick={handleBertAnnotate}
                  disabled={isProcessingBert || doc.status.bert_status === 'working'}
                  className="flex items-center justify-center gap-2 py-2 px-3 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-[10px] font-bold uppercase tracking-wider transition-all disabled:opacity-50 border border-emerald-100"
                >
                  <IconRobot /> BERT
                </button>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="flex border-b border-slate-100">
               <button className="flex-1 py-3 text-[10px] font-bold text-blue-600 uppercase tracking-widest border-b-2 border-blue-600">Annotations</button>
               <button className="flex-1 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-widest hover:text-slate-600">History</button>
            </div>
            <div className="flex-1 overflow-y-auto">
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
            </div>
          </div>
        </aside>

        {/* Main Workspace */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          {/* Sub-Header: Toolbar */}
          <div className="h-12 bg-white border-b border-slate-200 px-6 flex items-center justify-between z-20 shrink-0">
            <div className="flex items-center gap-8">
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Metadata:</span>
                <div className="flex gap-1">
                  {availableMetaEntries.map(entry => (
                    <button
                      key={entry.key}
                      onClick={() => setMetaView(metaView === entry.key ? 'none' : entry.key)}
                      className={`px-3 py-1 rounded text-[9px] font-bold uppercase transition-all ${metaView === entry.key ? 'bg-blue-600 text-white shadow-sm' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'}`}
                    >
                      {entry.label}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="h-4 w-px bg-slate-200"></div>

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Mode:</span>
                  <div className="flex bg-slate-100 p-0.5 rounded-full">
                    <button onClick={() => setRelationshipBuilderMode(false)} className={`px-3 py-0.5 rounded-full text-[10px] font-bold transition-all ${!relationshipBuilderMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>STANDARD</button>
                    <button onClick={() => setRelationshipBuilderMode(true)} className={`px-3 py-0.5 rounded-full text-[10px] font-bold transition-all ${relationshipBuilderMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-400'}`}>LINK MODE</button>
                  </div>
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
            </div>

            <div className="flex items-center gap-4">
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
          </div>

          <main className="flex-1 flex flex-col overflow-hidden">
            {/* Conflict Warning Banner */}
            {presenceUsers.length > 1 && (
              <div className="bg-amber-50 border-b border-amber-200 px-6 py-2 flex items-center gap-3 animate-in fade-in slide-in-from-top duration-500">
                <div className="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center">
                    <svg className="w-3 h-3 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
                </div>
                <div className="flex-1">
                    <p className="text-[11px] font-bold text-amber-800">
                        SIMULTANEOUS EDITING: {presenceUsers.filter(u => u !== (currentUser?.full_name || currentUser?.username)).join(', ')} {presenceUsers.length > 2 ? 'are' : 'is'} also viewing this case.
                    </p>
                    <p className="text-[9px] text-amber-600 font-medium">To avoid overwriting changes, please coordinate with other editors.</p>
                </div>
              </div>
            )}

            {/* Metadata Overlay */}
            {metaView !== 'none' && (
              <div className="absolute top-0 left-0 right-0 max-h-[40%] bg-white border-b border-slate-200 shadow-xl z-10 overflow-y-auto animate-in slide-in-from-top duration-300">
                <div className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-xs font-bold text-slate-900 uppercase tracking-widest">
                      {availableMetaEntries.find(e => e.key === metaView)?.label} Information
                    </h3>
                    <button onClick={() => setMetaView('none')} className="text-slate-400 hover:text-slate-600">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                  </div>
                  <div className="prose prose-slate prose-sm max-w-none">
                    {(() => {
                      const entry = availableMetaEntries.find(e => e.key === metaView);
                      if (!entry) return null;
                      if (entry.type === 'legacy') return <div dangerouslySetInnerHTML={{ __html: entry.html || '' }} />;
                      return <pre className="bg-slate-50 p-4 rounded text-[10px] overflow-x-auto">{JSON.stringify(entry.data, null, 2)}</pre>;
                    })()}
                  </div>
                </div>
              </div>
            )}

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
                <div className="h-48 bg-white border-t border-slate-200 z-10">
                   <RelationshipBuilderPanel
                     currentAnnotation={currentAnnotationRelation}
                     onSelectRelationType={setCurrentRelationType}
                     activeRelationType={currentRelationType}
                     allAnnotations={doc.annotations}
                     onRemoveRelation={(type) => {
                       if (!currentAnnotationRelation) return;
                       const updated = { 
                         ...currentAnnotationRelation, 
                         relationships: { 
                           ...currentAnnotationRelation.relationships, 
                           [type]: undefined 
                         } 
                       };
                       // Filter out the undefined key before sending to DB if necessary, 
                       // but for state it's fine.
                       dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updated, historyType: 'verify' } });
                     }}
                   />
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
        
        {/* Right Sidebar - Action History */}
        <aside className="w-72 bg-white border-l border-slate-200 flex flex-col shrink-0">
           <div className="p-4 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Action History</h2>
              <span className="px-2 py-0.5 bg-slate-100 rounded text-[9px] font-bold text-slate-500">{doc.actionHistory.length}</span>
           </div>
           <div className="flex-1 overflow-y-auto">
             <ActionHistoryPanel 
               history={doc.actionHistory} 
               onUndo={(id) => dispatch({ type: DocActionTypes.UNDO_ACTION, payload: { actionId: id } })}
               optionColors={optionColors}
             />
           </div>

        </aside>
      </div>

      {unifiedContextMenu.visible && !isReadOnly && (
        <UnifiedContextMenuDisplay
          contextMenu={unifiedContextMenu}
          annotationOptions={annotationOptions}
          optionColors={optionColors}
          annotationGuidelines={annotationGuidelines}
          addAnnotation={handleAddAnnotation}
          handleAddRelationship={async (opt) => {
             if (isReadOnly || !currentAnnotationRelation || !currentRelationType) return;

             if (opt === 'Set') {
                // To maintain data integrity, relationships MUST point to an annotation ID.
                // Check if an annotation exists at this range, or create one.
                let target = doc.annotations.find(a => 
                    a.textContext.start === unifiedContextMenu.start && 
                    a.textContext.end === unifiedContextMenu.end
                );

                if (!target) {
                    try {
                        const response = await createAnnotation({
                          case_id: parseInt(overrideId || '0'),
                          label: 'TEMPORAL', // Default label for relationship targets
                          start: unifiedContextMenu.start as number,
                          end: unifiedContextMenu.end as number,
                          text: selectedText,
                          note: userRole
                        });
                        target = {
                          id: response.id,
                          label: 'TEMPORAL',
                          textContext: {
                            text: selectedText,
                            start: unifiedContextMenu.start as number,
                            end: unifiedContextMenu.end as number,
                            page: doc.currentPageIndex
                          },
                          note: userRole,
                          relationships: {}
                        };
                        dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: target, historyType: 'add' } });
                    } catch (err) {
                        console.error("Failed to create target annotation:", err);
                        return;
                    }
                }

                if (target) {
                    const updated = { 
                      ...currentAnnotationRelation, 
                      relationships: { 
                        ...currentAnnotationRelation.relationships, 
                        [currentRelationType]: target.id 
                      } 
                    };
                    dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updated, historyType: 'verify' } });
                }
             } else {
                // Clear the relationship
                const updated = { 
                    ...currentAnnotationRelation, 
                    relationships: { 
                        ...currentAnnotationRelation.relationships, 
                        [currentRelationType]: undefined 
                    } 
                };
                dispatch({ type: DocActionTypes.UPDATE_ANNOTATION, payload: { annotation: updated, historyType: 'verify' } });
             }
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
