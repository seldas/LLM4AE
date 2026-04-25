import { useState, useEffect, useRef, useMemo, useCallback, Dispatch, SetStateAction } from "react";
import { Annotation, AnnotationOptions, TextContext } from "../lib/interfaces";
import { escapeRegExp } from "../lib/util";

interface Props {
  annotations: Annotation[];
  currentPage?: number;
  optionColors: { [key: string]: string };
  onFilterChange: (labels: string[]) => void;
  activeLayers: string[];
  isReadOnly?: boolean;
  pageData?: string;
  selectedTermContext?: TextContext | null;  
  setSelectedTermContext?: (context: TextContext | null) => void;  
  handleRemoveAnnotation?: (annotation: Annotation) => void;
}

const AnnotationPanel = (props: Props) => {
  const [filterKeyword, setFilterKeyword] = useState('');
  const termRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});
  const [collapsedTerms, setCollapsedTerms] = useState<Record<string, boolean>>({});

  const getTextOccurrences = useCallback((text: string) => {
    if (!props.pageData || !text) return 0;
    try {
      const regex = new RegExp(escapeRegExp(text), 'gi');
      return (props.pageData.match(regex) || []).length;
    } catch (e) {
      return 0;
    }
  }, [props.pageData]);

  const getCategory = (label: string): string => {
    const l = label.toUpperCase();
    if (['AGE', 'SEX', 'GENDER', 'RACE', 'ETHNICITY', 'BIRTH', 'DEMOGRAPHIC'].includes(l)) return 'DEMOGRAPHICS';
    if (['AE', 'SYMPTOM', 'SIGN', 'COD', 'CAUSE OF DEATH'].some(s => l.includes(s))) return 'ADVERSE EVENTS';
    if (['MEDICAL HISTORY', 'BSYM', 'MHX', 'DIAGNOSTIC', 'R/O', 'MH'].some(s => l.includes(s))) return 'MEDICAL HISTORY';
    if (['DRUG', 'VACCINE', 'LAB', 'TREATMENT', 'PROCEDURE', 'DEVICE', 'MEDICATION'].some(s => l.includes(s))) return 'INTERVENTIONS';
    if (['TEMPORAL', 'DATE', 'TIME', 'DURATION', 'RELATIVE', 'LATENCY', 'FREQUENCY', 'TEMPORAL SEQUENCE'].some(s => l.includes(s))) return 'TEMPORAL';
    return 'OTHER';
  };

  const groupedData = useMemo(() => {
    const filtered = props.annotations.filter(ann => {
      // Layer filtering
      const note = (ann.note || "").toUpperCase();
      const isLlm = note.includes('LLM');
      const isBert = note.includes('BERT');
      if (isLlm && !props.activeLayers.includes('LLM')) return false;
      if (isBert && !props.activeLayers.includes('BERT')) return false;
      if (!isLlm && !isBert && !props.activeLayers.includes('Human')) return false;

      // Keyword filtering
      const matchesKeyword = filterKeyword
        ? ann.textContext.text.toLowerCase().includes(filterKeyword.toLowerCase())
        : true;
      return matchesKeyword;
    });

    const groups: Record<string, Record<string, Record<string, Annotation[]>>> = {};
    
    filtered.forEach(ann => {
      const category = getCategory(ann.label);
      const textKey = ann.textContext.text.toLowerCase();
      const labelKey = ann.label;
      
      if (!groups[category]) groups[category] = {};
      if (!groups[category][textKey]) groups[category][textKey] = {};
      if (!groups[category][textKey][labelKey]) groups[category][textKey][labelKey] = [];
      groups[category][textKey][labelKey].push(ann);
    });

    return groups;
  }, [props.annotations, props.activeLayers, filterKeyword]);

  useEffect(() => {
    const selectedTerm = props.selectedTermContext?.text.toLowerCase();
    if (selectedTerm) {
      Object.entries(groupedData).forEach(([category, terms]) => {
        if (terms[selectedTerm]) {
          setCollapsedCategories(prev => ({ ...prev, [category]: false }));
          setCollapsedTerms(prev => ({ ...prev, [selectedTerm]: false }));
        }
      });
      if (termRefs.current[selectedTerm]) {
          termRefs.current[selectedTerm]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }, [props.selectedTermContext, groupedData]);
    
  return (
    <div className="annotation-panel flex flex-col h-full bg-slate-50 border-r border-slate-200 overflow-hidden font-sans">
      <div className="p-5 border-b border-slate-200 bg-white">
        <h2 className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4">Annotation Inventory</h2>
        <div className="relative group">
          <input
            type="text"
            value={filterKeyword}
            onChange={(e) => setFilterKeyword(e.target.value)}
            placeholder="Search within annotations..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded text-[12px] focus:bg-white focus:border-blue-500 outline-none transition-all placeholder:text-slate-300"
          />
          <span className="absolute left-3 top-2.5 text-slate-400">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
        {Object.keys(groupedData).length > 0 ? (
          Object.entries(groupedData)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([category, terms]) => {
              const isCatCollapsed = collapsedCategories[category] ?? true;
              return (
                <div key={category} className="space-y-3">
                  <button 
                    onClick={() => setCollapsedCategories(prev => ({ ...prev, [category]: !isCatCollapsed }))}
                    className="flex items-center gap-3 w-full text-left group"
                  >
                    <span className={`text-[8px] text-slate-300 transition-transform duration-200 ${isCatCollapsed ? '' : 'rotate-90'}`}>▶</span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest whitespace-nowrap">
                      {category} <span className="ml-1.5 text-slate-300">[{Object.keys(terms).length}]</span>
                    </span>
                    <div className="flex-1 border-t border-slate-100 ml-2"></div>
                  </button>

                  {!isCatCollapsed && (
                    <div className="space-y-4 ml-2 pl-4 border-l border-slate-100">
                      {Object.entries(terms)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([text, labels]) => {
                          const isCollapsed = collapsedTerms[text] ?? true;
                          return (
                            <div 
                              key={text} 
                              ref={(el) => {if (el) termRefs.current[text] = el;}}
                              className="bg-white rounded border border-slate-200 shadow-sm overflow-hidden"
                            >
                              <div className="flex items-center justify-between bg-slate-50/50 hover:bg-slate-100/50 transition-colors">
                                <button 
                                  onClick={() => setCollapsedTerms(prev => ({ ...prev, [text]: !isCollapsed }))}
                                  className="flex items-center gap-2 min-w-0 p-3 flex-1 text-left"
                                >
                                  <span className={`text-[8px] text-slate-300 transition-transform duration-200 ${isCollapsed ? '' : 'rotate-90'}`}>▶</span>
                                  <span className="font-bold text-[12px] text-slate-700 truncate" title={text}>
                                    {text}
                                  </span>
                                </button>
                                <div className="pr-3 flex items-center">
                                  {(() => {
                                    const allInstances = Object.values(labels).flat();
                                    const humanCount = allInstances.filter(a => {
                                      const note = (a.note || "").toUpperCase();
                                      return !(note.includes('AI') || note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT')) || note.includes('VERIFIED');
                                    }).length;
                                    const aiCount = allInstances.length - humanCount;
                                    const totalOccurrences = getTextOccurrences(text);

                                    return (
                                      <div 
                                        className="group/stats relative cursor-help flex items-center px-2 py-1 bg-slate-100 rounded text-[10px] font-mono text-slate-500 border border-slate-200 transition-colors hover:bg-slate-200"
                                      >
                                        <span className="text-indigo-600 font-bold">{humanCount}</span>
                                        <span className="mx-0.5 opacity-30">/</span>
                                        <span className="text-orange-600 font-bold">{aiCount}</span>
                                        <span className="mx-0.5 opacity-30">/</span>
                                        <span className="text-slate-400">{totalOccurrences}</span>

                                        <div className="absolute right-0 bottom-full mb-2 hidden group-hover/stats:block w-48 p-3 bg-slate-900 text-white text-[10px] rounded-lg shadow-xl z-[100] leading-relaxed animate-in fade-in slide-in-from-bottom-1 border border-slate-700">
                                          <p className="font-bold border-b border-white/10 pb-1.5 mb-1.5 uppercase tracking-wider">Concept Metrics</p>
                                          <div className="space-y-1.5">
                                            <div className="flex justify-between font-mono"><span className="text-indigo-300">HUMAN:</span> <span>{humanCount}</span></div>
                                            <div className="flex justify-between font-mono"><span className="text-orange-300">AI:</span> <span>{aiCount}</span></div>
                                            <div className="flex justify-between font-mono"><span className="text-slate-400">TOTAL MATCH:</span> <span>{totalOccurrences}</span></div>
                                          </div>
                                          <p className="mt-2 text-[9px] text-slate-400 border-t border-white/10 pt-1.5 italic">Human / AI / Narrative Occurrences</p>
                                        </div>
                                      </div>
                                    );
                                  })()}
                                </div>
                              </div>

                              {!isCollapsed && (
                                <div className="p-3 bg-white border-t border-slate-50 space-y-3">
                                  {Object.entries(labels).map(([label, instances]) => (
                                    <div key={label} className="space-y-2">
                                      <div className="flex items-center justify-between">
                                        <span 
                                          className="text-[9px] font-bold px-2 py-0.5 rounded text-white tracking-wide uppercase"
                                          style={{ backgroundColor: props.optionColors[label.toUpperCase()] || '#64748b' }}
                                        >
                                          {label} <span className="ml-1 opacity-60">×{instances.length}</span>
                                        </span>
                                      </div>
                                      
                                      <div className="flex flex-wrap gap-1.5">
                                        {instances.sort((a,b) => (a.textContext.start||0) - (b.textContext.start||0)).map((ann, idx) => {
                                          const note = (ann.note || "").toUpperCase();
                                          const isAI = note.includes('AI') || note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT');
                                          const isVerified = note.includes('VERIFIED');
                                          const isPureAI = isAI && !isVerified;
                                          const isSelected = props.selectedTermContext?.start === ann.textContext.start;

                                          return (
                                            <div 
                                              key={idx}
                                              onClick={() => {
                                                if (props.setSelectedTermContext) {
                                                    props.setSelectedTermContext({
                                                      text: ann.textContext.text,
                                                      start: ann.textContext.start ?? 0,
                                                      end: ann.textContext.end ?? 0,
                                                    });
                                                }
                                                // Jump to narrative position
                                                setTimeout(() => {
                                                  const element = document.getElementById(`ann-match-${ann.textContext.start}`);
                                                  if (element) {
                                                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                                  }
                                                }, 50);
                                              }}
                                              className={`group relative flex items-center gap-2 px-2.5 py-1 rounded border cursor-pointer transition-all ${
                                                isSelected 
                                                ? 'bg-slate-900 border-slate-900 text-white shadow-md z-10' 
                                                : isPureAI
                                                  ? 'bg-orange-50 border-orange-200 text-orange-700 hover:border-orange-400'
                                                  : 'bg-indigo-50 border-indigo-200 text-indigo-700 hover:border-indigo-400'
                                              }`}
                                            >
                                              <span className={`text-[9px] font-bold tracking-tight ${isSelected ? 'text-white' : ''}`}>
                                                {isPureAI ? 'AI' : 'OP'} #{ann.textContext.start}
                                                {isVerified && <span className="ml-1 text-emerald-500">✓</span>}
                                              </span>
                                              
                                              {!props.isReadOnly && props.handleRemoveAnnotation && (
                                                <button
                                                  onClick={(e) => {
                                                    e.stopPropagation();
                                                    props.handleRemoveAnnotation!(ann);
                                                  }}
                                                  className={`text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ${
                                                    isSelected ? 'text-white/60 hover:text-white' : 'text-slate-300 hover:text-red-500'
                                                  }`}
                                                >
                                                  ✕
                                                </button>
                                              )}
                                            </div>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              );
            })
        ) : (
          <div className="flex flex-col items-center justify-center py-20 text-slate-300 text-center">
            <svg className="w-10 h-10 mb-3 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>
            <p className="text-[11px] font-bold uppercase tracking-widest">No Matches</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnnotationPanel;
