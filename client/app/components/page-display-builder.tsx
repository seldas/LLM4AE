import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Annotation, TextContext } from "../lib/interfaces";

interface Props {
  annotations: Annotation[];
  currentPage: number;  
  pageData: string;  
  currentAnnotationRelation: Annotation | null;
  optionColors: { [key: string]: string };
  handleTextSelection: () => void;
  userRole: string; 
  onClickAnnotation?: (anno: Annotation) => void;
  isReadOnly?: boolean;
  theme?: 'light' | 'dark' | 'soft';
  selectedTermContext?: { text: string; start: number; end: number } | null;
  temporalTerms?: Annotation[];
  showTemporalHighlights?: boolean;
}

function getNodeAndOffsetForIndex(rootNode: Node, index: number): { node: Node; offset: number } | null {
  let stack: ChildNode[] = [rootNode as ChildNode];
  let count = 0;
  while (stack.length > 0) {
    const node = stack.shift();
    if (!node) continue;
    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent || "";
      if (count + text.length >= index) return { node, offset: index - count };
      count += text.length;
    } else if (node.hasChildNodes()) {
      stack = Array.from(node.childNodes).concat(stack);
    }
  }
  return null;
}

function darkenHSLColor(hsl: string, factor = 0.5): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hsl;
  const h = parseInt(match[1], 10);
  const s = parseInt(match[2], 10);
  return `hsl(${h}, ${s}%, 35%)`;
}

function getTransparentColor(hsl: string, alpha: number = 0.15): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hsl;
  return `hsla(${match[1]}, ${match[2]}%, ${match[3]}%, ${alpha})`;
}

const PageDisplayBuilder = ({
  annotations,
  pageData,  
  currentAnnotationRelation,
  optionColors,
  handleTextSelection,
  onClickAnnotation,
  isReadOnly,
  theme = 'light',
  selectedTermContext,
  temporalTerms,
  showTemporalHighlights
}: Props) => {
  const textRef = useRef<HTMLPreElement>(null);
  const [highlightBoxes, setHighlightBoxes] = useState<any[]>([]);
  const [hoveredBox, setHoveredBox] = useState<null | { start: number; end: number }>(null);
  const [lineCount, setLineCount] = useState(0);

  const themeStyles = {
    light: {
      text: 'text-slate-800',
      lineNumbers: 'text-slate-300 border-slate-100',
      boxBorder: '#000'
    },
    dark: {
      text: 'text-slate-100',
      lineNumbers: 'text-slate-600 border-slate-800',
      boxBorder: '#fff'
    },
    soft: {
      text: 'text-[#657b83]',
      lineNumbers: 'text-[#93a1a1] border-[#eee8d5]',
      boxBorder: '#586e75'
    }
  };

  const currentTheme = themeStyles[theme];

  const getAnnotatorDisplay = (note: string) => {
    const upperNote = note.toUpperCase();
    if (['SME1', 'SME2', 'ADJUDICATOR'].includes(upperNote)) return 'DevUser';
    return note;
  };

  const processedPageData = useMemo(() => {
    if (!pageData) return "";
    const chars = Array.from(pageData);
    const inAnnotation = new Array(chars.length).fill(false);
    annotations.forEach((a) => {
      const {start, end} = a.textContext;
      if (typeof start === 'number' && typeof end === 'number') {
        for (let i = start; i < end; i++) if (i >= 0 && i < inAnnotation.length) inAnnotation[i] = true;
      }
    });
    for (let i = 0; i < chars.length; i++) if (inAnnotation[i] && chars[i] === ' ') chars[i] = '\u00A0';
    return chars.join('');
  }, [pageData, annotations]);

  const updateLineCount = useCallback(() => {
    const container = textRef.current;
    if (!container) return;
    const style = window.getComputedStyle(container);
    const lh = parseFloat(style.lineHeight);
    if (lh > 0) setLineCount(Math.round(container.offsetHeight / lh));
  }, []);
    
  const computeHighlightBoxes = useCallback(() => {
      const container = textRef.current;
      if (!container) return;
      const containerRect = container.getBoundingClientRect();
      const boxes: any[] = [];

      const addBox = (start: number, end: number, label: string, color: string, isRelation: boolean, note: string = "", isSelected: boolean = false, isFirstBox: boolean = true, annotation?: Annotation) => {
        const startInfo = getNodeAndOffsetForIndex(container, start);
        const endInfo = getNodeAndOffsetForIndex(container, end);
        if (startInfo && endInfo) {
          try {
            const range = document.createRange();
            range.setStart(startInfo.node, startInfo.offset);
            range.setEnd(endInfo.node, endInfo.offset);
            const rects = range.getClientRects();
            for (let idx = 0; idx < rects.length; idx++) {
              const r = rects[idx];
              boxes.push({
                top: r.top - containerRect.top,
                left: r.left - containerRect.left,
                width: r.width,
                height: r.height,
                label, color, isRelation, start, end, note, isSelected,
                isFirstBox: isFirstBox && idx === 0
                , annotationRef: annotation
              });
            }
          } catch (e) {}
        }
      };

      if (!currentAnnotationRelation) {
        annotations.forEach(ann => {
          const color = optionColors[ann.label.toUpperCase()] || "hsl(210, 10%, 50%)";
          addBox(ann.textContext.start ?? 0, ann.textContext.end ?? 0, ann.label, color, false, ann.note, false, true, ann);
        });
      } else {
        const color = optionColors[currentAnnotationRelation.label.toUpperCase()] || "hsl(210, 10%, 50%)";
        addBox(currentAnnotationRelation.textContext.start ?? 0, currentAnnotationRelation.textContext.end ?? 0, currentAnnotationRelation.label, color, false, currentAnnotationRelation.note, true, true, currentAnnotationRelation);

        Object.entries(currentAnnotationRelation.relationships).forEach(([relType, relCtx]) => {
          if (relCtx.start === relCtx.end) return;
           addBox(relCtx.start ?? 0, relCtx.end ?? 0, relType, color, true, "", false);
        });
      }

      if (showTemporalHighlights && temporalTerms?.length) {
        const seen = new Set<string>();
        temporalTerms.forEach(term => {
          const start = term.textContext.start ?? 0;
          const end = term.textContext.end ?? 0;
          if (end <= start) return;
          const key = `${start}-${end}`;
          if (seen.has(key)) return;
          seen.add(key);
          const color = optionColors[term.label.toUpperCase()] || "hsl(48, 95%, 70%)";
          addBox(start, end, term.label, color, false, term.note || "", false, true, term);
        });
      }

      if (selectedTermContext && (!currentAnnotationRelation || selectedTermContext.start !== currentAnnotationRelation.textContext.start || selectedTermContext.end !== currentAnnotationRelation.textContext.end)) {
        addBox(selectedTermContext.start, selectedTermContext.end, "Temporal", "hsl(48, 95%, 70%)", false, "", true);
      }

      setHighlightBoxes(boxes);
    }, [annotations, currentAnnotationRelation, optionColors, selectedTermContext, temporalTerms, showTemporalHighlights]);

  useEffect(() => {
    computeHighlightBoxes();
    updateLineCount();
  }, [computeHighlightBoxes, updateLineCount, pageData]);

  useEffect(() => {
    const container = textRef.current;
    if (!container || !container.parentElement) return;
    const observer = new ResizeObserver(() => { computeHighlightBoxes(); updateLineCount(); });
    observer.observe(container.parentElement);
    observer.observe(container);
    return () => observer.disconnect();
  }, [computeHighlightBoxes, updateLineCount]);

  return (
    <div className="page flex" style={{ margin: "20px auto" }} onMouseUp={() => !isReadOnly && handleTextSelection()}>
      <div className={`flex-shrink-0 text-right pr-4 select-none font-mono text-[10px] border-r ${currentTheme.lineNumbers}`} style={{ width: '50px', lineHeight: '3.5rem', paddingTop: '14px' }}>
        {Array.from({ length: lineCount }).map((_, i) => <div key={i}>{i + 1}</div>)}
      </div>

      <div className="relative flex-1 min-w-0">
        <pre className={`text-block font-mono whitespace-pre-wrap ${currentTheme.text}`} ref={textRef} style={{ padding: "14px", whiteSpace: "pre-wrap", wordWrap: "break-word", position: "relative", lineHeight: "3.5rem", zIndex: 1, margin: 0 }}>
          {processedPageData}
        </pre>

      {highlightBoxes.map((box, i) => {
          const isHovered = hoveredBox?.start === box.start && hoveredBox?.end === box.end;
          const note = (box.note || "").toUpperCase();
          const isAI = note.includes('AI') || note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT');
          const isVerified = note.includes('VERIFIED');
          const isPureAI = isAI && !isVerified;

          return (
            <div
              key={i}
              id={`ann-match-${box.start}`}
              onMouseEnter={() => setHoveredBox({ start: box.start, end: box.end })}
              onMouseLeave={() => setHoveredBox(null)}
              onClick={() => {
                if (box.isRelation) return;
                const annotation = box.annotationRef ?? annotations.find(a => a.textContext.start === box.start && a.textContext.end === box.end);
                if (annotation) onClickAnnotation?.(annotation);
              }}
              style={{
                position: "absolute",
                top: (box.top ?? 0) - 2,
                left: (box.left ?? 0) - 2,
                width: (box.width ?? 0) + 4,
                height: (box.height ?? 0) + 4,
                backgroundColor: box.isRelation || isPureAI ? "transparent" : (box.isSelected ? getTransparentColor(box.color, 0.3) : getTransparentColor(box.color, 0.15)),
                opacity: 1,
                zIndex: box.isSelected ? 10 : 2,
                pointerEvents: "auto",
                borderRadius: "4px",
                borderBottom: box.isRelation
                  ? `2px solid ${darkenHSLColor(box.color)}`
                  : (isPureAI ? `2px dashed ${darkenHSLColor(box.color)}` : (box.isSelected ? `2px solid ${currentTheme.boxBorder}` : "none")),
                boxShadow: isHovered
                  ? "0 0 6px 2px rgba(0,0,0,0.1)"
                  : "none",
                cursor: "pointer",
                transition: "all 0.1s ease-out",
              }}
            >
              {box.isFirstBox && box.label && (
                <div
                  style={{
                    position: "absolute",
                    top: box.isSelected ? "-2.2em" : "-1.8em",
                    left: 0,
                    display: "flex",
                    alignItems: "center",
                    backgroundColor: box.isSelected ? "#000" : darkenHSLColor(box.color),
                    color: box.isSelected ? "#fde047" : "#fff",
                    fontSize: box.isSelected ? "11px" : "9px",
                    fontWeight: 900,
                    padding: box.isSelected ? "2px 8px" : "1px 5px",
                    borderRadius: "4px",
                    whiteSpace: "nowrap",
                    boxShadow: box.isSelected ? "0 4px 6px rgba(0,0,0,0.3)" : "0 1px 3px rgba(0,0,0,0.2)",
                    textTransform: "uppercase",
                    gap: "3px",
                    zIndex: box.isSelected ? 50 : 20,
                    border: box.isSelected ? "1px solid #fde047" : "none",
                    transition: "all 0.2s ease-in-out",
                  }}
                >
                  <span>{box.label}</span>
                  {box.note && (
                    <>
                      <span style={{ opacity: 0.6, fontSize: '7px' }}>|</span>
                      <span>{getAnnotatorDisplay(box.note)}</span>
                    </>
                  )}
                  {isPureAI && <span className="bg-white/20 px-1 rounded-[2px] text-[7px] font-black">AI</span>}
                  {isVerified && <span className="text-emerald-300">✓</span>}
                </div>
              )}
            </div>
          );
      })}
      </div>
    </div>
  );
};

export default PageDisplayBuilder;
