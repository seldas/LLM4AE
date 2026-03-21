import { useState, useEffect, useRef, useMemo } from "react";
import { Annotation, AnnotationOptions } from "../lib/interfaces";

interface Props {
  annotations: Annotation[];
  annotationOptions: AnnotationOptions;
  setAnnotationOptions: (opts: AnnotationOptions) => void;
  optionColors: { [key: string]: string };
  setOptionColors: (colors: { [key: string]: string }) => void;
  handleRemoveAnnotation: (annotation: Annotation) => void;
  activeLabelFilters: string[]; 
  setActiveLabelFilters: (labels: string[]) => void;
  selectedTermContext: { text: string; start: number; end: number } | null;  
  setSelectedTermContext: (context: { text: string; start: number; end: number } | null) => void;  
  handleExtendMatch: (annotation: Annotation) => void;  
}

const AnnotationPanel = (props: Props) => {
  const [filterKeyword, setFilterKeyword] = useState('');
  const termRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});
  const [collapsedTerms, setCollapsedTerms] = useState<Record<string, boolean>>({});

  const getCategory = (label: string): string => {
    const l = label.toUpperCase();
    if (['AGE', 'SEX', 'GENDER', 'RACE', 'ETHNICITY', 'BIRTH', 'DEMOGRAPHIC'].includes(l)) return 'DEMOGRAPHICS';
    if (['AE', 'SYMPTOM', 'SIGN', 'COD', 'CAUSE OF DEATH', 'Symptom', 'Sign'].some(s => l.includes(s.toUpperCase()))) return 'ADVERSE EVENTS';
    if (['MEDICAL HISTORY', 'BSYM', 'MHX', 'DIAGNOSTIC', 'R/O', 'MH'].some(s => l.includes(s.toUpperCase()))) return 'MEDICAL HISTORY';
    if (['DRUG', 'VACCINE', 'LAB', 'TREATMENT', 'PROCEDURE', 'DEVICE', 'MEDICATION'].some(s => l.includes(s.toUpperCase()))) return 'INTERVENTIONS';
    if (['TEMPORAL', 'DATE', 'TIME', 'DURATION', 'RELATIVE', 'LATENCY', 'FREQUENCY', 'TEMPORAL SEQUENCE'].some(s => l.includes(s.toUpperCase()))) return 'TEMPORAL';
    return 'OTHER';
  };

  // Grouping Logic: Category -> Text -> Label -> Occurrences
  const groupedData = useMemo(() => {
    const filtered = props.annotations.filter(annotation => {
      const matchesLabel = props.activeLabelFilters
        .map((l) => l.toLowerCase())
        .includes(annotation.label.toLowerCase());
      const matchesKeyword = filterKeyword
        ? annotation.textContext.text.toLowerCase().includes(filterKeyword.toLowerCase())
        : true;
      return matchesLabel && matchesKeyword;
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
  }, [props.annotations, props.activeLabelFilters, filterKeyword]);

  useEffect(() => {
    const selectedTerm = props.selectedTermContext?.text.toLowerCase();
    if (selectedTerm) {
      // Find which category this term belongs to and expand it
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
    <div className="annotation-panel flex flex-col h-full bg-gray-50 border-r border-gray-200">
      <div className="p-4 border-b border-gray-200 bg-white">
        <h2 className="text-sm font-black text-gray-800 uppercase tracking-widest mb-3 flex items-center gap-2">
          <span className="text-lg">📋</span> Summary
        </h2>
        <div className="relative">
          <input
            type="text"
            value={filterKeyword}
            onChange={(e) => setFilterKeyword(e.target.value)}
            placeholder="Search annotations..."
            className="w-full pl-8 pr-3 py-2 text-xs border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-400 focus:border-transparent outline-none transition-all"
          />
          <span className="absolute left-2.5 top-2 text-gray-400">🔍</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {Object.keys(groupedData).length > 0 ? (
          Object.entries(groupedData)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([category, terms]) => {
              const isCatCollapsed = collapsedCategories[category] ?? true;
              return (
                <div key={category} className="space-y-2">
                  <button 
                    onClick={() => setCollapsedCategories(prev => ({ ...prev, [category]: !isCatCollapsed }))}
                    className="flex items-center gap-2 w-full text-left group hover:bg-gray-100/50 p-1 rounded-md transition-colors"
                  >
                    <span className={`text-[10px] text-gray-400 group-hover:text-gray-600 transition-transform duration-200 ${isCatCollapsed ? '' : 'rotate-90'}`}>
                      ▶
                    </span>
                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-wider">
                      {category} <span className="ml-1 opacity-50">({Object.keys(terms).length})</span>
                    </span>
                    <div className="flex-1 border-t border-gray-200 ml-2"></div>
                  </button>

                  {!isCatCollapsed && (
                    <div className="space-y-3 ml-2 border-l-2 border-gray-100 pl-2">
                      {Object.entries(terms)
                        .sort(([a], [b]) => a.localeCompare(b))
                        .map(([text, labels]) => {
                          const isCollapsed = collapsedTerms[text] ?? true;
                          return (
                            <div 
                              key={text} 
                              ref={(el) => {if (el) termRefs.current[text] = el;}}
                              className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden"
                            >
                              {/* Term Header */}
                              <div className="flex items-center justify-between bg-gray-50/50 hover:bg-gray-100/50 transition-colors">
                                <button 
                                  onClick={() => setCollapsedTerms(prev => ({ ...prev, [text]: !isCollapsed }))}
                                  className="flex items-center gap-2 min-w-0 p-2.5 flex-1 text-left"
                                >
                                  <span className={`text-[10px] text-gray-400 transition-transform duration-200 ${isCollapsed ? '' : 'rotate-90'}`}>
                                    ▶
                                  </span>
                                  <span className="font-bold text-xs text-gray-700 truncate" title={text}>
                                    {text}
                                  </span>
                                </button>
                                <div className="pr-2">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      props.handleExtendMatch(Object.values(labels)[0][0]);
                                    }}
                                    className="text-[10px] font-black text-blue-600 hover:bg-blue-100 px-2 py-1 rounded-md transition-colors whitespace-nowrap"
                                  >
                                    TAG ALL
                                  </button>
                                </div>
                              </div>

                              {/* Labels and Occurrences */}
                              {!isCollapsed && (
                                <div className="p-2 space-y-2">
                                  {Object.entries(labels).map(([label, instances]) => (
                                    <div key={label} className="space-y-1">
                                      <div className="flex items-center justify-between">
                                        <span 
                                          className="text-[10px] font-black px-2 py-0.5 rounded text-white shadow-sm"
                                          style={{ backgroundColor: props.optionColors[label] || '#999' }}
                                        >
                                          {label} <span className="ml-1 opacity-70">×{instances.length}</span>
                                        </span>
                                      </div>
                                      
                                      <div className="flex flex-wrap gap-1.5 ml-1">
                                        {instances.sort((a,b) => (a.textContext.start||0) - (b.textContext.start||0)).map((ann, idx) => {
                                          const isAI = ann.note.toUpperCase().includes('AI') || ann.note.toUpperCase().includes('LLM') || ann.note.toLowerCase().includes('llama') || ann.note.toLowerCase().includes('bert');
                                          const isSME = ann.note.toUpperCase().includes('SME');
                                          const isVerified = ann.note.toUpperCase().includes('VERIFIED');
                                          const isSelected = props.selectedTermContext?.start === ann.textContext.start;

                                          let pillClass = isSelected 
                                            ? 'bg-blue-600 border-blue-600 text-white shadow-md' 
                                            : isVerified 
                                              ? 'bg-emerald-50 border-emerald-200 text-emerald-700 hover:border-emerald-400' 
                                              : isAI 
                                                ? 'bg-orange-50 border-orange-200 text-orange-700 hover:border-orange-400' 
                                                : 'bg-indigo-50 border-indigo-200 text-indigo-700 hover:border-indigo-400';

                                          return (
                                            <div 
                                              key={idx}
                                              onClick={() => props.setSelectedTermContext({
                                                text: ann.textContext.text,
                                                start: ann.textContext.start ?? 0,
                                                end: ann.textContext.end ?? 0,
                                              })}
                                              className={`group relative flex items-center gap-1.5 px-2 py-1 rounded-full border cursor-pointer transition-all ${pillClass}`}
                                            >
                                              <span className={`text-[9px] font-bold ${isSelected ? 'text-blue-100' : 'opacity-60'}`}>
                                                {isAI ? '🤖' : isVerified ? '👤✓' : '👤'} #{ann.textContext.start}
                                              </span>
                                              
                                              <button
                                                onClick={(e) => {
                                                  e.stopPropagation();
                                                  props.handleRemoveAnnotation(ann);
                                                }}
                                                className={`text-[10px] opacity-0 group-hover:opacity-100 transition-opacity ${
                                                  isSelected ? 'text-white' : 'text-red-400 hover:text-red-600'
                                                }`}
                                              >
                                                ✕
                                              </button>
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
          <div className="text-center py-10">
            <span className="text-3xl grayscale opacity-30">🔍</span>
            <p className="text-xs text-gray-400 mt-2">No matching annotations</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnnotationPanel;
