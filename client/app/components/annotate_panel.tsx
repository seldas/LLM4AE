// annotate_panel.tsx
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

const PRIMARY_ENTITY_LABELS = new Set(['AE','SDRUG','CDRUG','ODRUG','TREATMENT','SDRUG','CDrug','SDrug','Treatment']);
const TEMPORAL_LABELS = new Set(['TEMPORAL','DATE','TIME','DURATION','RELATIVE','LATENCY']);

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
  const [activeLayers, setActiveLayers] = useState<string[]>(['Human', 'LLM', 'BERT']);
  const [theme, setTheme] = useState<'light' | 'dark' | 'soft'>('light');
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [userRole, setUserRole] = useState<string>("Anonymous");
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isReadOnly, setIsReadOnly] = useState(false);
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
      const raw = meta[key];
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
        const hasRows = raw && typeof raw === 'object' && Array.isArray(raw.rows) && raw.rows.length > 0;
        const hasCategories =
          raw &&
          typeof raw === 'object' &&
          raw.categories &&
          Object.values(raw.categories).some((items: any) => Array.isArray(items) && items.length > 0);
        if (hasRows || hasCategories) {
          entries.push({ key, label, type: 'outcomes-structured', data: raw });
          return;
        }
      }
      if (typeof raw === 'string' && raw.trim()) {
        entries.push({ key, label, type: 'legacy', html: raw.trim() });
      }
    });
    return entries;
  }, [doc.meta]);

  const renderDemographicStructured = (entries: any[]): ReactNode => {
    const sanitized = entries?.filter(Boolean) || [];
    if (!sanitized.length) {
      return <p className="text-sm text-slate-500 italic">No demographic data available.</p>;
    }
    return (
      <div className="space-y-4">
        {sanitized.map((entry, index) => {
          const lowerLabel = entry.label?.toLowerCase() || '';
          const isMedicalHistory = lowerLabel.includes('medical history');
          const isAttachment = lowerLabel.includes('attachment');
          return (
            <div key={`${entry.label}-${index}`} className="bg-white border border-slate-200 rounded-[1.5rem] p-4">
              {entry.type === 'list' ? (
                <details
                  className="space-y-3"
                  open={!isMedicalHistory && !isAttachment}
                >
                  <summary className="text-[9px] uppercase tracking-[0.4em] text-slate-400 cursor-pointer">
                    {entry.label}
                  </summary>
                  <div className="space-y-1 text-sm text-slate-700">
                    {(entry.items || []).map((item: string, idx: number) => (
                      <p key={idx} className="leading-snug flex items-start gap-1">
                        <span className="text-slate-400">•</span>
                        <span>{item}</span>
                      </p>
                    ))}
                  </div>
                </details>
              ) : (
                <>
                  <p className="text-[9px] uppercase tracking-[0.4em] text-slate-400 mb-2">{entry.label}</p>
                  <p className="text-sm text-slate-700">{entry.value}</p>
                </>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const renderProductsStructured = (data: any): ReactNode => {
    const groups = Array.isArray(data?.groups) ? data.groups : [];
    if (!groups.length) {
      return <p className="text-sm text-slate-500 italic">No product data available.</p>;
    }
    return (
      <div className="space-y-4">
        {groups.map((group: any) => (
          <div key={group.role} className="space-y-3">
            <div className="text-[10px] uppercase tracking-[0.3em] text-slate-500">{group.role} Products</div>
            <div className="space-y-2">
              {(group.items || []).map((item: any, index: number) => (
                <div key={`${group.role}-${index}`} className="border border-slate-200 rounded-[1.5rem] bg-white">
                  <div className="px-4 py-3 border-b border-slate-100">
                    <p className="text-sm font-semibold text-slate-900">{item.display_name}</p>
                  </div>
                  <div className="px-4 py-3 space-y-1 text-[12px] text-slate-700">
                    {(item.fields || []).map((field: any) => (
                      <div key={`${field.label}-${field.value}`} className="flex justify-between">
                        <span className="text-[10px] uppercase tracking-[0.3em] text-slate-400">{field.label}</span>
                        <span className="font-semibold text-slate-800">{field.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderOutcomesStructured = (data: any): ReactNode => {
    const rows = Array.isArray(data?.rows) ? data.rows : [];
    if (!rows.length) {
      return <p className="text-sm text-slate-500 italic">No outcomes data available.</p>;
    }

    const formatColonSegments = (value?: string) =>
      (value || '')
        .split(':')
        .map(segment => segment.trim())
        .filter(Boolean);

    const buildPaths = (row: any) => {
      const segments = {
        soc: formatColonSegments(row.soc),
        hlgt: formatColonSegments(row.hlgt),
        hlt: formatColonSegments(row.hlt),
        pt: formatColonSegments(row.pt),
        llt: formatColonSegments(row.llt),
      };
      const maxSegments = Math.max(
        segments.soc.length,
        segments.hlgt.length,
        segments.hlt.length,
        segments.pt.length,
        segments.llt.length,
        1
      );
      return Array.from({ length: maxSegments }, (_, idx) => ({
        soc: segments.soc[idx] || '',
        hlgt: segments.hlgt[idx] || '',
        hlt: segments.hlt[idx] || '',
        pt: segments.pt[idx] || '',
        llt: segments.llt[idx] || '',
      }));
    };

    const renderRowsList = () => (
      <div className="space-y-4">
        {rows.map((row: any, idx: number) => (
          <div
            key={row.term_id ? `term-${row.term_id}-${idx}` : `term-${idx}`}
            className="px-4 py-3 space-y-2 text-[12px] text-slate-700"
          >
              <p><span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">SOC:</span> {formatColonSegments(row.soc).join(' / ') || '—'}</p>
              <p><span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">HLGT:</span> {formatColonSegments(row.hlgt).join(' / ') || '—'}</p>
              <p><span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">HLT:</span> {formatColonSegments(row.hlt).join(' / ') || '—'}</p>
              <p><span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">PT:</span> {formatColonSegments(row.pt).join(' / ') || '—'}</p>
              <p><span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">LLT:</span> {formatColonSegments(row.llt).join(' / ') || '—'}</p>
          </div>
        ))}
      </div>
    );

    return (
      <div className="space-y-2">
        {renderRowsList()}
      </div>
    );
  };

  const renderMetaEntryContent = (entry: MetaEntry): ReactNode => {
    if (!entry) return null;
    switch (entry.type) {
      case 'demographic-structured':
        return renderDemographicStructured(entry.data);
      case 'products-structured':
        return renderProductsStructured(entry.data);
      case 'outcomes-structured':
        return renderOutcomesStructured(entry.data);
      case 'legacy':
      default:
        return <div className="max-w-none break-words" dangerouslySetInnerHTML={{ __html: entry.html || '' }} />;
    }
  };

  const activeMetaEntry = useMemo(() => availableMetaEntries.find(entry => entry.key === metaView) || null, [availableMetaEntries, metaView]);

  useEffect(() => {
    if (metaView !== 'none' && !availableMetaEntries.some(entry => entry.key === metaView)) {
      setMetaView('none');
    }
  }, [availableMetaEntries, metaView]);

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
    const enriched = doc.annotations.map(a => {
      const note = (a.note || "").toUpperCase();
      const isLLM = note.includes('LLM') || note.includes('LLAMA');
      const isBERT = note.includes('BERT');
      const isAI = isLLM || isBERT || note.includes('AI');
      const isVerified = note.includes('VERIFIED');
      
      let layer = 'Human';
      let priority = 1; // Lower number = Higher priority in our final pick

      if (isLLM && !isVerified) {
        layer = 'LLM';
        priority = 2;
      } else if (isBERT && !isVerified) {
        layer = 'BERT';
        priority = 3;
      } else if (isAI && !isVerified) {
        layer = 'LLM'; // Default generic AI to LLM for now
        priority = 2;
      } else {
        layer = 'Human'; // Human or Verified AI
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

    // Display Priority: Human(1) > LLM(2) > BERT(3)
    const positionMap: Record<string, typeof enriched[0]> = {};
    // Sort by priority DESC so that higher priority (smaller number) overwrites in the map
    filtered.sort((a, b) => b.priority - a.priority).forEach(ann => {
      const key = `${ann.textContext.start}-${ann.textContext.end}`;
      positionMap[key] = ann;
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
    if (type === 'LLM' || type === 'BERT') {
      const existingAI = doc.annotations.find(a => 
        a.textContext.start === start && 
        a.textContext.end === end && 
        (a.label.toUpperCase() === label.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === label.toUpperCase()) && 
        (a.note.toUpperCase().includes('LLM') || a.note.toUpperCase().includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert'))
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
    const humanAnno = doc.annotations.find(a => a.textContext.start === start && a.textContext.end === end && (a.label.toUpperCase() === labelStr.toUpperCase() || (labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()) === labelStr.toUpperCase()) && (a.note.toUpperCase().includes('SME') || a.note.toUpperCase().includes('MJ.L') || a.note.toUpperCase().includes('K.L') || a.note.toUpperCase().includes('ADJUDICATOR') || a.note.toUpperCase() === userRole.toUpperCase()));
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
    let type: 'LLM' | 'BERT' | 'SME' | 'NEW' = 'NEW';
    let isVerified = false;
    if (note) {
      const upperNote = note.toUpperCase();
      const isLLM = upperNote.includes('LLM') || upperNote.includes('LLAMA');
      const isBERT = upperNote.includes('BERT');
      const isAI = isLLM || isBERT || upperNote.includes('AI');
      
      if (isAI) { 
        if (isBERT) type = 'BERT';
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
        const res = await fetch(`${BASE_PATH}/annotator_api/api/annotation-guidelines`);
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
              <div className="flex flex-wrap items-center gap-1.5 mt-3">
                <span className="text-[10px] font-bold text-slate-400 uppercase mr-1">Data:</span>
                {availableMetaEntries.length > 0 ? (
                  availableMetaEntries.map(entry => (
                    <button
                      key={entry.key}
                      onClick={() => setMetaView(metaView === entry.key ? 'none' : entry.key)}
                      className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all border ${metaView === entry.key ? 'bg-slate-900 text-white border-slate-900' : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'}`}
                    >
                      {entry.label}
                    </button>
                  ))
                ) : (
                  <span className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500">No metadata</span>
                )}
              </div>
              <div className="text-[10px] font-bold text-slate-300 uppercase tracking-tighter whitespace-nowrap mt-3">
                Record ID: {overrideId || 'Ad-hoc'}
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

          {/* Metadata Side Panel */}
          <aside className="w-[360px] shrink-0 flex flex-col border-l border-slate-200 bg-slate-50/60">
          <div className="px-6 py-5 border-b border-slate-200 flex items-start justify-between gap-3">
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-600">Meta Inventory</p>
                <p className="text-[11px] font-semibold text-slate-800">{activeMetaEntry ? activeMetaEntry.label : 'Select metadata to preview'}</p>
              </div>
              <button
                onClick={() => setMetaView('none')}
                className="w-8 h-8 rounded-full bg-white text-slate-500 hover:text-slate-900 transition-colors flex items-center justify-center"
                aria-label="Close metadata panel"
              >
                ×
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {activeMetaEntry ? (
                <div className="bg-white border border-slate-200 rounded-[2rem] shadow-sm p-5 text-slate-900">
                  {renderMetaEntryContent(activeMetaEntry)}
                </div>
              ) : (
                <div className="text-sm text-slate-500 uppercase tracking-[0.35em] text-center">
                  Choose a data source from the top controls
                </div>
              )}
            </div>
          </aside>
        </div>
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
