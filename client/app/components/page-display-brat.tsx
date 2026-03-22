import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Annotation } from "../lib/interfaces";

interface Props {
  annotations: Annotation[];
  updateAnnotationNote: (
    start: number,
    end: number,
    text: string,
    label: string,
    addNote: string,
  ) => void;
  currentPage: number;
  pageData: string;
  optionColors: { [key: string]: string };
  handleTextSelection: () => void;
  activeLabelFilters: string[];
  disableFilter?: boolean;
  userRole: string;
  annotationSet: string;  
  onClickAnnotation?: (text: string, start: number, end: number, x: number, y: number, note?: string, label?: string) => void;
  selectedTermContext: { text: string; start: number; end: number } | null;
  setSelectedTermContext: (context: { text: string; start: number; end: number } | null) => void;
  isReadOnly?: boolean;
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function getNodeAndOffsetForIndex(rootNode: Node, index: number): { node: Node; offset: number } | null {
  let stack: ChildNode[] = [rootNode as ChildNode];
  let count = 0;

  while (stack.length > 0) {
    const node = stack.shift();
    if (!node) continue;

    if (node.nodeType === Node.TEXT_NODE) {
      const text = node.textContent || "";
      if (count + text.length >= index) {
        return { node, offset: index - count };
      }
      count += text.length;
    } else if (node.hasChildNodes()) {
      stack = Array.from(node.childNodes).concat(stack);
    }
  }
  return null;
}

function darkenHSLColor(hsl: string): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hsl;

  const h = parseInt(match[1], 10);
  const s = parseInt(match[2], 10);
  const l = parseInt(match[3], 10);

  const newS = 70;
  const newL = 35;
  return `hsl(${h}, ${newS}%, ${newL}%, 1)`;
}

function PageDisplay({
  annotations,
  updateAnnotationNote,
  pageData,
  optionColors,
  handleTextSelection,
  activeLabelFilters,
  disableFilter = false,
  userRole,
  annotationSet,
  onClickAnnotation,
  selectedTermContext,
  setSelectedTermContext,
  isReadOnly
}: Props) {
  const textRef = useRef<HTMLPreElement>(null);
  const [highlightBoxes, setHighlightBoxes] = useState<any[]>([]);
  const [hoveredBox, setHoveredBox] = useState<null | { start: number; end: number }>(null);
  const [lineCount, setLineCount] = useState(0);
  
  const [discrepancyPopup, setDiscrepancyPopup] = useState<null | {
    box: any;
    x: number;
    y: number;
  }>(null);
  
  const reasons = ["Exceed", "Incomplete", "Wrong Label Type", "Others"];
  const [selectedReason, setSelectedReason] = useState("");

  const processedPageData = useMemo(() => {
    if (!pageData) return "";
    const chars = Array.from(pageData);
    const inAnnotation = new Array(chars.length).fill(false);

    annotations.forEach((annotation) => {
      const start = annotation.textContext?.start;
      const end = annotation.textContext?.end;
      if (typeof start === 'number' && typeof end === 'number') {
        for (let i = start; i < end; i++) {
          if (i >= 0 && i < inAnnotation.length) {
            inAnnotation[i] = true;
          }
        }
      }
    });

    for (let i = 0; i < chars.length; i++) {
      if (inAnnotation[i] && chars[i] === ' ') {
        chars[i] = '\u00A0';
      }
    }

    return chars.join('');
  }, [pageData, annotations]);

  const updateLineCount = useCallback(() => {
    const container = textRef.current;
    if (!container) return;
    const style = window.getComputedStyle(container);
    const lh = parseFloat(style.lineHeight);
    const height = container.offsetHeight; 
    const paddingTop = parseFloat(style.paddingTop);
    const paddingBottom = parseFloat(style.paddingBottom);
    if (lh > 0) {
      const visualLines = Math.round((height - paddingTop - paddingBottom) / lh);
      setLineCount(visualLines);
    }
  }, []);

  const getAnnotatorDisplay = (note: string) => {
    const upperNote = note.toUpperCase();
    if (['SME1', 'SME2', 'ADJUDICATOR'].includes(upperNote)) return 'DevUser';
    return note;
  };

  const computeHighlightBoxes = useCallback(() => {
    const container = textRef.current;
    if (!container) return;

    const containerRect = container.getBoundingClientRect();
    const boxes: any[] = [];

    const labelOccurrences: Record<string, number> = {};

    annotations.forEach((annotation) => {
      const { start, end } = annotation.textContext;
      if (typeof start !== 'number' || typeof end !== 'number') return;

      const label = annotation.label.toUpperCase();
      if (!disableFilter && !activeLabelFilters.includes(label)) return;

      const startInfo = getNodeAndOffsetForIndex(container, start);
      const endInfo = getNodeAndOffsetForIndex(container, end);

      if (startInfo && endInfo) {
        try {
          const range = document.createRange();
          range.setStart(startInfo.node, startInfo.offset);
          range.setEnd(endInfo.node, endInfo.offset);
          const rects = range.getClientRects();

          const key = `${start}-${end}`;
          labelOccurrences[key] = (labelOccurrences[key] || 0) + 1;
          const stackIndex = labelOccurrences[key] - 1;

          for (const r of rects) {
            boxes.push({
              top: r.top - containerRect.top,
              left: r.left - containerRect.left,
              width: r.width,
              height: r.height,
              label: annotation.label,
              note: annotation.note,
              color: optionColors[label] || "rgba(255,255,0,0.4)",
              start,
              end,
              stackIndex,
            });
          }
        } catch (e) {
          console.error("Box compute failed", e);
        }
      }
    });

    setHighlightBoxes(boxes);
  }, [annotations, activeLabelFilters, optionColors, disableFilter]);

  useEffect(() => {
    computeHighlightBoxes();
    updateLineCount();
  }, [computeHighlightBoxes, updateLineCount, pageData]);

  useEffect(() => {
    const container = textRef.current;
    if (!container || !container.parentElement) return;
    const observer = new ResizeObserver(() => {
      computeHighlightBoxes();
      updateLineCount();
    });
    observer.observe(container.parentElement);
    observer.observe(container);
    return () => observer.disconnect();
  }, [computeHighlightBoxes, updateLineCount]);

  const handleAccept = (acceptedAnno: Annotation, otherAnno?: Annotation) => {
    updateAnnotationNote(
      acceptedAnno.textContext.start!,
      acceptedAnno.textContext.end!,
      acceptedAnno.textContext.text,
      acceptedAnno.label,
      `VERIFIED BY ${userRole}${selectedReason ? ': ' + selectedReason : ''}`
    );
    setDiscrepancyPopup(null);
    setSelectedReason("");
  };

  return (
    <div className="page flex" style={{ margin: "20px auto" }} onMouseUp={() => !isReadOnly && handleTextSelection()}>
      {/* Visual Gutter */}
      <div 
        className="flex-shrink-0 text-right pr-4 text-gray-300 select-none font-mono text-xs border-r border-gray-100" 
        style={{ width: '50px', lineHeight: '3.5rem', paddingTop: '14px' }}
      >
        {Array.from({ length: lineCount }).map((_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>

      <div className="relative flex-1 min-w-0">
        <pre
          className="text-block font-mono whitespace-pre-wrap"
          ref={textRef}
          style={{ padding: "14px", whiteSpace: "pre-wrap", wordWrap: "break-word", position: "relative", lineHeight: "3.5rem", zIndex: 1, margin: 0 }}
        >
          {processedPageData}
        </pre>

        {highlightBoxes.map((box, i) => {
          const isSelected = selectedTermContext?.start === box.start;
          const isHovered = hoveredBox?.start === box.start && hoveredBox?.end === box.end;
          const isAI = box.note.toUpperCase().includes('AI') || box.note.toUpperCase().includes('LLM') || box.note.toLowerCase().includes('llama') || box.note.toLowerCase().includes('bert');
          const isVerified = box.note.toUpperCase().includes('VERIFIED');
          
          const stackOffset = box.stackIndex * 4;

          return (
            <div
              key={i}
              onMouseEnter={() => setHoveredBox({ start: box.start, end: box.end })}
              onMouseLeave={() => setHoveredBox(null)}
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                if (onClickAnnotation) {
                  onClickAnnotation(pageData.substring(box.start, box.end), box.start, box.end, rect.left + window.scrollX, rect.top + window.scrollY, box.note, box.label);
                } else {
                  setSelectedTermContext({
                    text: pageData.substring(box.start, box.end),
                    start: box.start,
                    end: box.end,
                  });
                }
              }}
              style={{
                position: "absolute",
                top: (box.top ?? 0) + stackOffset - 2,
                left: (box.left ?? 0) - 2,
                width: (box.width ?? 0) + 4,
                height: (box.height ?? 0) + 4,
                backgroundColor: isSelected ? "rgba(59, 130, 246, 0.2)" : box.color,
                opacity: isSelected ? 1 : 0.4,
                zIndex: isSelected ? 10 : 2,
                pointerEvents: "auto",
                borderRadius: "4px",
                border: isSelected ? "2px solid #2563eb" : isVerified ? "1px solid #059669" : "none",
                boxShadow: isHovered ? "0 0 0 2px rgba(0,0,0,0.1)" : "none",
                cursor: "pointer",
                transition: "all 0.1s ease-out",
              }}
            >
              {(isHovered || isSelected) && (
                <div
                  style={{
                    position: "absolute",
                    top: "-1.8em",
                    left: 0,
                    backgroundColor: darkenHSLColor(box.color),
                    color: "#fff",
                    fontSize: "10px",
                    fontWeight: 800,
                    padding: "2px 6px",
                    borderRadius: "4px",
                    whiteSpace: "nowrap",
                    zIndex: 20,
                    boxShadow: "0 2px 4px rgba(0,0,0,0.2)",
                    textTransform: "uppercase",
                    display: "flex",
                    gap: "4px",
                    alignItems: "center"
                  }}
                >
                  <span>{box.label}</span>
                  <span style={{ opacity: 0.8, fontSize: '8px' }}>•</span>
                  <span>{getAnnotatorDisplay(box.note)}</span>
                  {isAI && <span>🤖</span>}
                  {isVerified && <span>✓</span>}
                </div>
              )}
            </div>
          );
        })}

        {/* Discrepancy Popup UI (if needed in future, cleaned for now) */}
      </div>
    </div>
  );
}

export default PageDisplay;
