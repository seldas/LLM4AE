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
}: Props) => {
  const textRef = useRef<HTMLPreElement>(null);
  const [highlightBoxes, setHighlightBoxes] = useState<any[]>([]);
  const [hoveredBox, setHoveredBox] = useState<null | { start: number; end: number }>(null);
  const [lineCount, setLineCount] = useState(0);

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

      const addBox = (start: number, end: number, label: string, color: string, isRelation: boolean, note?: string) => {
        const startInfo = getNodeAndOffsetForIndex(container, start);
        const endInfo = getNodeAndOffsetForIndex(container, end);
        if (startInfo && endInfo) {
          try {
            const range = document.createRange();
            range.setStart(startInfo.node, startInfo.offset);
            range.setEnd(endInfo.node, endInfo.offset);
            const rects = range.getClientRects();
            for (const r of rects) {
              boxes.push({
                top: r.top - containerRect.top,
                left: r.left - containerRect.left,
                width: r.width,
                height: r.height,
                label, color, isRelation, start, end, note
              });
            }
          } catch (e) {}
        }
      };

      if (!currentAnnotationRelation) {
        annotations.forEach(ann => {
          const color = optionColors[ann.label] || "hsl(60, 100%, 50%)";
          addBox(ann.textContext.start, ann.textContext.end, ann.label, color, false, ann.note);
        });
      } else {
        const color = optionColors[currentAnnotationRelation.label] || "hsl(60, 100%, 50%)";
        addBox(currentAnnotationRelation.textContext.start, currentAnnotationRelation.textContext.end, currentAnnotationRelation.label, color, false, currentAnnotationRelation.note);
        Object.entries(currentAnnotationRelation.relationships).forEach(([relType, relCtx]) => {
          if (relCtx.start === relCtx.end) return;
          addBox(relCtx.start, relCtx.end, relType, color, true);
        });
      }
      setHighlightBoxes(boxes);
  }, [annotations, currentAnnotationRelation, optionColors]);

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
      <div className="flex-shrink-0 text-right pr-4 text-slate-300 select-none font-mono text-[10px] border-r border-slate-100" style={{ width: '50px', lineHeight: '3.5rem', paddingTop: '14px' }}>
        {Array.from({ length: lineCount }).map((_, i) => <div key={i}>{i + 1}</div>)}
      </div>

      <div className="relative flex-1 min-w-0">
        <pre className="text-block font-mono whitespace-pre-wrap text-slate-800" ref={textRef} style={{ padding: "14px", whiteSpace: "pre-wrap", wordWrap: "break-word", position: "relative", lineHeight: "3.5rem", zIndex: 1, margin: 0 }}>
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
              onMouseEnter={() => setHoveredBox({ start: box.start, end: box.end })}
              onMouseLeave={() => setHoveredBox(null)}
              onClick={() => {
                if (box.isRelation) return;
                const ann = annotations.find(a => a.textContext.start === box.start && a.textContext.end === box.end);
                if (ann) onClickAnnotation?.(ann);
              }}
              style={{
                position: "absolute",
                top: (box.top ?? 0) - 2,
                left: (box.left ?? 0) - 2,
                width: (box.width ?? 0) + 4,
                height: (box.height ?? 0) + 4,
                backgroundColor: box.isRelation ? "transparent" : (isPureAI ? "transparent" : getTransparentColor(box.color, 0.15)),
                opacity: 1,
                zIndex: 2,
                pointerEvents: "auto",
                borderRadius: "4px",
                borderBottom: box.isRelation
                  ? `2px solid ${darkenHSLColor(box.color)}`
                  : (isPureAI ? `2px dashed ${darkenHSLColor(box.color)}` : "none"),
                boxShadow: isHovered
                  ? "0 0 6px 2px rgba(0,0,0,0.1)"
                  : "none",
                cursor: "pointer",
                transition: "all 0.2s ease-in-out",
              }}
            >
              {(box.label || box.note) && (
                <div
                  style={{
                    position: "absolute",
                    top: "-1.8em",
                    left: 0,
                    display: "flex",
                    alignItems: "center",
                    flexWrap: "wrap",
                    backgroundColor: darkenHSLColor(box.color),
                    color: "#fff",
                    fontSize: "9px",
                    fontWeight: 600,
                    padding: "1px 5px",
                    borderRadius: "3px",
                    whiteSpace: "nowrap",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.2)",
                    maxWidth: "100%",
                    gap: "0.25em",
                    textTransform: "uppercase",
                  }}
                >
                  <span>{box.label}</span>
                  {isPureAI && <span className="bg-white/20 px-1 rounded-[2px] text-[7px] ml-0.5">AI</span>}
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
