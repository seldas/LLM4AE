import { useState, useEffect, useRef } from "react";
import Image from 'next/image';
import { Annotation, AnnotationOptions } from "../lib/interfaces";
import { termMapper } from "../lib/terms";
import ToggleHighlightIcon from '../highlight_all.svg';
import removeIcon from '../remove2.svg';

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
  const [newLabel, setNewLabel] = useState('');
  const termRefs = useRef<Record<string, HTMLLIElement | null>>({});
  const [collapsedTerms, setCollapsedTerms] = useState<Record<string, boolean>>({});

  const filteredAnnotations = props.annotations.filter(annotation => {
    const matchesLabel = props.activeLabelFilters
      .map((l) => l.toLowerCase())
      .includes(annotation.label.toLowerCase());
    const matchesKeyword = filterKeyword
      ? annotation.textContext.text.toLowerCase().includes(filterKeyword.toLowerCase())
      : true;
    return matchesLabel && matchesKeyword;
  });

  const handleAddNewLabel = () => {
    const trimmed = newLabel.trim();
    if (!trimmed || props.annotationOptions[trimmed]) return;

    const updatedOptions = { ...props.annotationOptions, [trimmed]: trimmed };
    const updatedColors = { ...props.optionColors, [trimmed]: `hsl(${Math.floor(Math.random() * 360)}, 50%, 85%)` };

    props.setAnnotationOptions(updatedOptions);
    props.setOptionColors(updatedColors);
    props.setActiveLabelFilters([...props.activeLabelFilters, trimmed]);
    setNewLabel('');
  };

  const grouped = filteredAnnotations.reduce((acc, ann) => {
      const key = ann.textContext.text.toLowerCase();
      if (!acc[key]) acc[key] = [];
      acc[key].push(ann);
      return acc;
  }, {} as Record<string, Annotation[]>);
    
  useEffect(() => {
      const allLabels = Object.keys(props.annotationOptions);
      props.setActiveLabelFilters(allLabels);
  }, [props.annotationOptions]);

  useEffect(() => {
    const selectedTerm = props.selectedTermContext?.text.toLowerCase();
    if (selectedTerm && termRefs.current[selectedTerm]) {
        termRefs.current[selectedTerm]?.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
        });
    }
  }, [props.selectedTermContext]);
    
  return (
    <div className="annotation-panel">
      <h2 className="panel-title">📌 Annotations Summary</h2>

      {/* Unified Filter Panel */}
      <div className="filter-panel">
        
        {/* Keyword Filter */}
        <div className="filter-row">
          <label htmlFor="keyword" className="filter-label">Keyword:</label>
          <input
            id="keyword"
            type="text"
            value={filterKeyword}
            onChange={(e) => setFilterKeyword(e.target.value)}
            placeholder="Search by keyword"
            className="filter-input"
          />
        </div>
      </div>

      {/* Annotation List */}
      <div className="annotation-summary-panel">
        {props.annotations.length > 0 ? (
          <ul className="annotation-list" style={{ maxWidth: '320px', margin: '0 auto' }}>
              {Object.entries(grouped)
                .sort(([termA], [termB]) => termA.localeCompare(termB))
                .map(([term, annotations]) => {
                  const isSelectedGroup =
                    props.selectedTermContext?.text.toLowerCase() === term;
                  const isCollapsed = collapsedTerms[term] ?? false;

                  if (!termRefs.current[term]) {
                    termRefs.current[term] = null;
                  }
            
                  return (
                    <li
                      key={term}
                      ref={(el) => {
                        termRefs.current[term] = el;
                      }}
                      className={`rounded-lg px-3 py-2 mb-4 shadow-sm ${isSelectedGroup ? 'bg-yellow-100' : 'bg-white'}`}
                    >
                      <div className="flex items-center justify-between border-b border-gray-200 pb-1 mb-1">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() =>
                              setCollapsedTerms((prev) => ({
                                ...prev,
                                [term]: !prev[term],
                              }))
                            }
                            className="text-xs text-gray-600 hover:text-black"
                            title={isCollapsed ? "Expand" : "Collapse"}
                          >
                            {isCollapsed ? '▶' : '▼'}
                          </button>

                          <span
                            className="font-semibold text-sm bg-gray-100 px-2 py-1 rounded shadow-inner max-w-[100px] truncate text-gray-800"
                            title={term}
                          >
                            {term}
                          </span>
                        </div>

                        <button
                          onClick={() => props.handleExtendMatch(annotations[0])}
                          className="text-xs text-sky-700 font-medium bg-sky-100 hover:bg-sky-200 px-2 py-1 rounded shadow"
                          title="Annotate all occurrences of this term"
                        >
                          🔎Tag All
                        </button>
                      </div>

                      {!isCollapsed && (
                        <ul className="ml-3 space-y-1 text-xs">
                          {annotations
                            .sort((a, b) => (a.textContext.start ?? 0) - (b.textContext.start ?? 0))
                            .map((a, i) => {
                              const isSelected =
                                props.selectedTermContext?.start === a.textContext.start &&
                                props.selectedTermContext?.end === a.textContext.end &&
                                props.selectedTermContext?.text.toLowerCase() === a.textContext.text.toLowerCase();

                              return (
                                <li
                                  key={i}
                                  className={`flex items-center justify-between rounded-md px-2 py-1 cursor-pointer ${isSelected ? 'bg-blue-100' : 'hover:bg-gray-50'}`}
                                  onClick={() =>
                                    props.setSelectedTermContext({
                                      text: a.textContext.text,
                                      start: a.textContext.start ?? 0,
                                      end: a.textContext.end ?? 0,
                                    })
                                  }
                                >
                                  <span
                                    className="text-[11px] font-medium px-1.5 py-0.5 rounded text-white"
                                    style={{ backgroundColor: props.optionColors[a.label] }}
                                  >
                                    {a.note?.toLowerCase().includes("verified") ? "[V] " : ""}
                                    {a.note.split(',')[0]} | {a.label}
                                  </span>

                                  <span className="text-[11px] text-gray-500 px-1">
                                    ({a.textContext.start}, {a.textContext.end})
                                  </span>

                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      props.handleRemoveAnnotation(a);
                                    }}
                                    className="text-gray-400 hover:text-red-600 text-sm"
                                    title="Remove"
                                  >
                                    🗑️
                                  </button>
                                </li>
                              );
                            })}
                        </ul>
                      )}
                    </li>
                  );
                })}
          </ul>
        ) : (
          <p>No annotations yet.</p>
        )}
      </div>
    </div>
  );
};

export default AnnotationPanel;
