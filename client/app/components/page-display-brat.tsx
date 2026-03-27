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
  theme?: 'light' | 'dark' | 'soft';
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

function darkenHSLColor(hsl: string): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hsl;
  const h = parseInt(match[1], 10);
  const s = parseInt(match[2], 10);
  return `hsl(${h}, ${s}%, 35%, 1)`;
}

function getTransparentColor(hsl: string, alpha: number = 0.15): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hsl;
  return `hsla(${match[1]}, ${match[2]}%, ${match[3]}%, ${alpha})`;
}

function PageDisplay({
  annotations,
  pageData,
  optionColors,
  handleTextSelection,
  activeLabelFilters,
  disableFilter = false,
  onClickAnnotation,
  selectedTermContext,
  setSelectedTermContext,
  isReadOnly,
  theme = 'light'
}: Props) {
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
          for (let idx = 0; idx < rects.length; idx++) {
            const r = rects[idx];
            boxes.push({
              top: r.top - containerRect.top,
              left: r.left - containerRect.left,
              width: r.width,
              height: r.height,
              label: annotation.label,
              note: annotation.note,
              color: optionColors[label] || "hsl(60, 100%, 50%)",
              start, end,
              isFirstBox: idx === 0
            });
          }
        } catch (e) {}
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
          const isSelected = selectedTermContext?.start === box.start;
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
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                if (onClickAnnotation) onClickAnnotation(pageData.substring(box.start, box.end), box.start, box.end, rect.left + window.scrollX, rect.top + window.scrollY, box.note, box.label);
                else setSelectedTermContext({ text: pageData.substring(box.start, box.end), start: box.start, end: box.end });
              }}
              style={{
                position: "absolute",
                top: (box.top ?? 0) - 2,
                left: (box.left ?? 0) - 2,
                width: (box.width ?? 0) + 4,
                height: (box.height ?? 0) + 4,
                backgroundColor: isPureAI ? "transparent" : (isSelected ? getTransparentColor(box.color, 0.3) : getTransparentColor(box.color, 0.15)),
                opacity: 1,
                zIndex: isSelected ? 10 : 2,
                pointerEvents: "auto",
                borderRadius: "4px",
                borderBottom: isPureAI 
                  ? `2px dashed ${darkenHSLColor(box.color)}` 
                  : (isSelected ? `2px solid ${currentTheme.boxBorder}` : isVerified ? "1px solid #059669" : "none"),
                cursor: "pointer",
                transition: "all 0.1s ease-out",
              }}
            >
              {box.isFirstBox && (
                <div
                  style={{
                    position: "absolute",
                    top: isSelected ? "-2.2em" : "-1.8em",
                    left: 0,
                    backgroundColor: isSelected ? "#000" : darkenHSLColor(box.color),
                    color: isSelected ? "#fde047" : "#fff", // yellow-300 for selected
                    fontSize: isSelected ? "11px" : "9px",
                    fontWeight: 900,
                    padding: isSelected ? "2px 8px" : "1px 5px",
                    borderRadius: "4px",
                    whiteSpace: "nowrap",
                    zIndex: isSelected ? 50 : 20,
                    boxShadow: isSelected ? "0 4px 6px rgba(0,0,0,0.3)" : "0 1px 3px rgba(0,0,0,0.2)",
                    textTransform: "uppercase",
                    display: "flex",
                    gap: "3px",
                    alignItems: "center",
                    transition: "all 0.2s ease-in-out",
                    border: isSelected ? "1px solid #fde047" : "none"
                  }}
                >
                  <span>{box.label}</span>
                  <span style={{ opacity: 0.6, fontSize: '7px' }}>|</span>
                  <span>{getAnnotatorDisplay(box.note)}</span>
                  {isPureAI && <span className="bg-white/20 px-1 rounded-[2px] text-[7px] ml-0.5 font-black">AI</span>}
                  {isVerified && <span className="text-emerald-300">✓</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PageDisplay;
