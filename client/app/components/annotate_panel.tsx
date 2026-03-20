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
  }; 
  
  // Layer Management
  const [activeLayers, setActiveLayers] = useState<string[]>(['SME1', 'AI']); // Default layers
  const [userRole, setUserRole] = useState<"SME1" | "SME2" | "Adjudicator">("SME1");
  const [metaView, setMetaView] = useState<'none' | 'demographic' | 'products' | 'outcomes'>('none');

  const [relationshipBuilderMode, setRelationshipBuilderMode] = useState(false);
  const [currentAnnotationRelation, setCurrentAnnotationRelation] = useState<Annotation | null>(null);
  const [currentRelationType, setCurrentRelationType] = useState<keyof AnnotationRelationships | ''>('');
  
  const [annotationOptions, setAnnotationOptions] = useState<AnnotationOptions>({});
  const [optionColors, setOptionColors] = useState<{ [key: string]: string }>({});
  const [activeLabelFilters, setActiveLabelFilters] = useState<string[]>([]);
  
  const [unifiedContextMenu, setUnifiedContextMenu] = useState<{
          visible: boolean; x: number; y: number;
          type: 'annotation' | 'relationship' | 'verification';
          options?: string[]; start?: number; end?: number;
        }>({ visible: false, x: 0, y: 0, type: 'annotation' });

  const [llmPopup, setLlmPopup] = useState({ visible: false, x: 0, y: 0, text: '', start: 0, end: 0 });
  const [selectedPopupLabel, setSelectedPopupLabel] = useState('');
  const [selectedTermContext, setSelectedTermContext] = useState<{ text: string; start: number; end: number } | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const currentPageData = doc.pages[doc.currentPageIndex] || null;

  // Filter and Normalize Annotations for Display
  const visibleAnnotations = useMemo(() => {
    return doc.annotations.filter(a => {
      const note = a.note.toUpperCase();
      const isSme1 = (note.includes('SME1') || note.includes('MJ.L')) && activeLayers.includes('SME1');
      const isSme2 = (note.includes('SME2') || note.includes('K.L')) && activeLayers.includes('SME2');
      const isAI = (note.includes('LLM') || note.includes('llama') || note.includes('BERT')) && activeLayers.includes('AI');
      const isAdj = note.includes('ADJUDICATOR') && activeLayers.includes('ADJ');
      
      return isSme1 || isSme2 || isAI || isAdj;
    }).map(a => ({
      ...a,
      label: labelNormalizer[a.label.toUpperCase()] || a.label.toUpperCase()
    }));
  }, [doc.annotations, activeLayers]);

  const handleSave = async (shouldClose = false) => {
      try {
        await saveAnnotationsToDb({
          fileName: overrideFileName || doc.saveFileName,
          curr_folder: overrideFolder ?? 'Playground',
          pages: doc.pages,
          annotations: doc.annotations,
          meta: doc.meta,
        });
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 2000);
        if (shouldClose) window.close();
      } catch (error: any) {
        alert(`❌ Failed to save: ${error.message}`);
      }
  };

  const handleLayerToggle = (layer: string) => {
    setActiveLayers(prev => 
      prev.includes(layer) ? prev.filter(l => l !== layer) : [...prev, layer]
    );
  };

  // Selection Logic
  const handleTextSelection = () => {
      const selection = window.getSelection();
      if (!selection || !selection.toString().trim()) return;
    
      const text = selection.toString().trim();
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
      const newAnnotation: Annotation = {
        textContext: {
          text: selectedText,
          page: doc.currentPageIndex,
          start: unifiedContextMenu.start as number,
          end: unifiedContextMenu.end as number,
          disputed: false,
        },
        label,
        note: userRole,
        relationships: { latency: {text:'',page:0}, date: {text:'',page:0}, time: {text:'',page:0}, frequency: {text:'',page:0}, temporal_sequence: {text:'',page:0} },
      };
      dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation } });
      setUnifiedContextMenu(prev => ({ ...prev, visible: false }));
  };

  const handleLlmAddAnnotation = () => {
    const { start, end, text } = llmPopup;
    const label = selectedPopupLabel;
    
    const newAnnotation: Annotation = {
      textContext: {
        text,
        start,
        end,
        page: doc.currentPageIndex,
        disputed: false,
      },
      label: label,
      note: userRole, // Add as the current user
      relationships: {
        latency: { text: '', page: 0 },
        date: { text: '', page: 0 },
        time: { text: '', page: 0 },
        frequency: { text: '', page: 0 },
        temporal_sequence: { text: '', page: 0 },
      },
    };
  
    dispatch({ type: DocActionTypes.ADD_ANNOTATION, payload: { annotation: newAnnotation } });
    setLlmPopup((prev) => ({ ...prev, visible: false }));
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
    const labels = new Set(['DRUG', 'AE', 'MEDICAL HISTORY', 'LAB', 'TEMPORAL']);
    doc.annotations.forEach(a => labels.add(a.label.toUpperCase()));
    const arr = Array.from(labels).sort();
    setAnnotationOptions(Object.fromEntries(arr.map(l => [l, l])));
    setOptionColors(generateOptionColors(arr));
    if (activeLabelFilters.length === 0) setActiveLabelFilters(arr);
  }, [doc.annotations]);

  return (
    <div className="app-container h-screen overflow-hidden flex flex-col bg-gray-100">
      
      {/* 🟢 NEW TOP BANNER */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shadow-sm z-30">
        <div className="flex items-center gap-8">
          <div>
            <span className="text-[10px] font-black text-gray-400 uppercase tracking-tighter">Annotate</span>
            <h1 className="text-sm font-bold text-gray-800 -mt-1 truncate max-w-xs">{overrideFileName}</h1>
          </div>

          {/* Layer Toggles */}
          <div className="flex items-center bg-gray-100 rounded-xl p-1 gap-1">
            {['SME1', 'SME2', 'AI', 'ADJ'].map(layer => (
              <button
                key={layer}
                onClick={() => handleLayerToggle(layer)}
                className={`px-3 py-1.5 rounded-lg text-[11px] font-black transition-all ${
                  activeLayers.includes(layer) 
                  ? 'bg-white text-blue-600 shadow-sm ring-1 ring-black/5' 
                  : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                {layer}
              </button>
            ))}
          </div>

          {/* Metadata Toggles */}
          <div className="flex items-center gap-2 border-l border-gray-200 pl-6">
            <span className="text-[10px] font-bold text-gray-400 uppercase">View Data:</span>
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

        <div className="flex items-center gap-3">
          <button
            onClick={() => setRelationshipBuilderMode(!relationshipBuilderMode)}
            className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
              relationshipBuilderMode ? 'bg-orange-500 text-white shadow-lg' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {relationshipBuilderMode ? '✕ Exit Link Mode' : '⛓ Link Mode'}
          </button>
          
          <div className="h-8 w-px bg-gray-200 mx-2" />

          <button onClick={() => handleSave(false)} className="text-xs font-bold text-gray-600 hover:text-black">Save</button>
          <button onClick={() => handleSave(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-xs font-bold shadow-md transition-all">
            Finish
          </button>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden">
        {/* Left Side: Summary */}
        <div className="w-80 flex-shrink-0">
          <AnnotationPanel
            annotations={visibleAnnotations}
            annotationOptions={annotationOptions}
            setAnnotationOptions={setAnnotationOptions}
            optionColors={optionColors}
            setOptionColors={setOptionColors}
            handleRemoveAnnotation={(a) => dispatch({ type: DocActionTypes.REMOVE_ANNOTATION, payload: { annotation: a } })}
            activeLabelFilters={activeLabelFilters}
            setActiveLabelFilters={setActiveLabelFilters}
            selectedTermContext={selectedTermContext}
            setSelectedTermContext={setSelectedTermContext}
            handleExtendMatch={() => {}}
          />
        </div>

        {/* Center: Narrative */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          <div className="flex-1 overflow-y-auto p-12">
            <div className="max-w-4xl mx-auto relative">
              
              {/* Role Switcher (Sticky Mini) */}
              <div className="absolute -left-20 top-0 flex flex-col gap-2">
                <span className="text-[9px] font-bold text-gray-400 uppercase text-center">My Role</span>
                {['SME1', 'SME2', 'Adjudicator'].map(r => (
                  <button
                    key={r}
                    onClick={() => {
                      setUserRole(r as any);
                      if (r === 'Adjudicator' && !activeLayers.includes('ADJ')) handleLayerToggle('ADJ');
                    }}
                    className={`w-12 h-12 rounded-full text-[10px] font-black border-2 transition-all flex items-center justify-center ${
                      userRole === r ? 'bg-indigo-600 border-indigo-600 text-white shadow-lg scale-110' : 'bg-white border-gray-100 text-gray-400 hover:border-gray-300'
                    }`}
                  >
                    {r === 'Adjudicator' ? 'ADJ' : r}
                  </button>
                ))}
              </div>

              {relationshipBuilderMode ? (
                <PageDisplayBuilder
                  annotations={visibleAnnotations}
                  currentPage={doc.currentPageIndex}
                  pageData={currentPageData}
                  currentAnnotationRelation={currentAnnotationRelation}
                  optionColors={optionColors}
                  handleTextSelection={handleTextSelection}
                  userRole={userRole as any}
                />
              ) : (
                <PageDisplay
                  annotations={visibleAnnotations}
                  updateAnnotationNote={() => {}}
                  userRole={userRole as any}
                  currentPage={doc.currentPageIndex}
                  pageData={currentPageData}
                  optionColors={optionColors}
                  handleTextSelection={handleTextSelection}
                  activeLabelFilters={activeLabelFilters}
                  disableFilter={false}
                  annotationSet="SME"
                  onClickAnnotation={(text, start, end, x, y) => setLlmPopup({ visible: true, x, y, text, start, end })}
                  selectedTermContext={selectedTermContext}
                  setSelectedTermContext={setSelectedTermContext}
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
                  setCurrentAnnotationRelation(a);
                  setCurrentRelationType(type);
                }}
                currentAnnotation={currentAnnotationRelation}
                currentRelationshipType={currentRelationType}
              />
          </div>
        )}
      </main>

      {unifiedContextMenu.visible && (
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
        x={llmPopup.x} y={llmPopup.y} visible={llmPopup.visible} text={llmPopup.text}
        annotationOptions={annotationOptions}
        selectedLabel={selectedPopupLabel}
        onChangeLabel={setSelectedPopupLabel}
        onAdd={handleLlmAddAnnotation}
        onClose={() => setLlmPopup(prev => ({ ...prev, visible: false }))}
      />
    </div>
  );
}
