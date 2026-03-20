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
  const termRefs = useRef<Record<string, HTMLLIElement | null>>({});
  const [collapsedTerms, setCollapsedTerms] = useState<Record<string, boolean>>({});

  // Grouping Logic: Text -> Label -> Occurrences
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

    const groups: Record<string, Record<string, Annotation[]>> = {};
    
    filtered.forEach(ann => {
      const textKey = ann.textContext.text.toLowerCase();
      const labelKey = ann.label;
      if (!groups[textKey]) groups[textKey] = {};
      if (!groups[textKey][labelKey]) groups[textKey][labelKey] = [];
      groups[textKey][labelKey].push(ann);
    });

    return groups;
  }, [props.annotations, props.activeLabelFilters, filterKeyword]);

  useEffect(() => {
    const selectedTerm = props.selectedTermContext?.text.toLowerCase();
    if (selectedTerm && termRefs.current[selectedTerm]) {
        termRefs.current[selectedTerm]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [props.selectedTermContext]);
    
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

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {Object.keys(groupedData).length > 0 ? (
          Object.entries(groupedData)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([text, labels]) => {
              const isCollapsed = collapsedTerms[text] ?? true;
              return (
                <div key={text} className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                  {/* Term Header */}
                  <div className="flex items-center justify-between p-2.5 bg-gray-50/50">
                    <div className="flex items-center gap-2 min-w-0">
                      <button 
                        onClick={() => setCollapsedTerms(prev => ({ ...prev, [text]: !isCollapsed }))}
                        className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors"
                      >
                        {isCollapsed ? '▶' : '▼'}
                      </button>
                      <span className="font-bold text-xs text-gray-700 truncate" title={text}>
                        {text}
                      </span>
                    </div>
                    <button
                      onClick={() => props.handleExtendMatch(Object.values(labels)[0][0])}
                      className="text-[10px] font-black text-blue-600 hover:bg-blue-50 px-2 py-1 rounded-md transition-colors whitespace-nowrap"
                    >
                      TAG ALL
                    </button>
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
                          
                          <div className="grid grid-cols-1 gap-1 ml-1">
                            {instances.sort((a,b) => (a.textContext.start||0) - (b.textContext.start||0)).map((ann, idx) => (
                              <div 
                                key={idx}
                                onClick={() => props.setSelectedTermContext({
                                  text: ann.textContext.text,
                                  start: ann.textContext.start ?? 0,
                                  end: ann.textContext.end ?? 0,
                                })}
                                className={`group flex items-center justify-between p-1.5 rounded-md cursor-pointer transition-all ${
                                  props.selectedTermContext?.start === ann.textContext.start ? 'bg-blue-50 ring-1 ring-blue-200' : 'hover:bg-gray-50'
                                }`}
                              >
                                <span className="text-[10px] font-mono text-gray-400">
                                  pos: {ann.textContext.start}
                                </span>
                                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      props.handleRemoveAnnotation(ann);
                                    }}
                                    className="text-red-400 hover:text-red-600"
                                  >
                                    🗑️
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
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
