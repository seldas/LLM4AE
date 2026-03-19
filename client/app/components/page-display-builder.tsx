import React, { useEffect, useRef, useState, useCallback } from "react";
import { Annotation, TextContext } from "../lib/interfaces";

interface Props {
  annotations: Annotation[];
  currentPage: number;  
  pageData: string;  
  currentAnnotationRelation: Annotation | null;
  optionColors: { [key: string]: string };
  handleTextSelection: () => void;
  userRole: string; 
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

function darkenHSLColor(hsl: string, factor = 0.5): string {
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return hsl;

  const h = parseInt(match[1], 10);
  const s = parseInt(match[2], 10);
  const l = parseInt(match[3], 10);

  // Apply multiplicative darkening (e.g., 0.5 = 50% of original lightness)
  const newL = Math.max(0, Math.round(l * factor));
  return `hsl(${h}, ${s}%, ${newL}%)`;
}


const PageDisplayBuilder = ({
  annotations,
  pageData,  
  currentAnnotationRelation,
  optionColors,
  handleTextSelection,
  userRole,
}: Props) => {
  const textRef = useRef<HTMLPreElement>(null);
  const [selectedBox, setSelectedBox] = useState<{ start: number; end: number } | null>(null);  
  const [highlightBoxes, setHighlightBoxes] = useState<any[]>([]);
  const [hoveredBox, setHoveredBox] = useState<null | { start: number; end: number }>(null);
    
  const computeHighlightBoxes = useCallback(() => {
      const container = textRef.current;
      if (!container || !currentAnnotationRelation) return;
    
      const containerRect = container.getBoundingClientRect();
      const boxes: any[] = [];
    
      const color = optionColors[currentAnnotationRelation.label] || "rgba(255,255,0,0.4)";
      const main = currentAnnotationRelation.textContext;
      if (typeof main.start !== 'number' || typeof main.end !== 'number') return;
      const startInfo = getNodeAndOffsetForIndex(container, main.start);
      const endInfo = getNodeAndOffsetForIndex(container, main.end);
    
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
              label: currentAnnotationRelation.label,
              color,
              isRelation: false,
              ...main,
            });
          }
        } catch (e) {
          console.warn("Main entity render failed", e);
        }
      }
    
      // Render related terms
      Object.entries(currentAnnotationRelation.relationships).forEach(([relType, relCtx]) => {
        if (relCtx.start === relCtx.end) return;
    
        const relStartInfo = getNodeAndOffsetForIndex(container, relCtx.start);
        const relEndInfo = getNodeAndOffsetForIndex(container, relCtx.end);
        if (relStartInfo && relEndInfo) {
          try {
            const range = document.createRange();
            range.setStart(relStartInfo.node, relStartInfo.offset);
            range.setEnd(relEndInfo.node, relEndInfo.offset);
            const rects = range.getClientRects();
            for (const r of rects) {
              boxes.push({
                top: r.top - containerRect.top,
                left: r.left - containerRect.left,
                width: r.width,
                height: r.height,
                label: relType,
                color: optionColors[currentAnnotationRelation.label] || "rgba(200,200,255,0.3)",
                isRelation: true,
                ...relCtx,
              });
            }
          } catch (e) {
            console.warn("Relationship render failed", e);
          }
        }
      });
    
      setHighlightBoxes(boxes);
  }, [currentAnnotationRelation, optionColors]);


  // Call once on mount and on updates
  useEffect(() => {
    computeHighlightBoxes();
  }, [computeHighlightBoxes]);

  // 🔁 Recompute when window resizes
  useEffect(() => {
    const container = textRef.current;
    if (!container || !container.parentElement) return;

    const observer = new ResizeObserver(() => {
      computeHighlightBoxes();
    });

    observer.observe(container.parentElement); // monitor size changes to the parent

    return () => {
      observer.disconnect();
    };
  }, [computeHighlightBoxes]);

  return (
    <div
      className="page relative"
      style={{ margin: "20px auto", position: "relative" }}
      onMouseUp={handleTextSelection}
    >
      <pre
        className="text-block font-mono whitespace-pre-wrap"
        ref={textRef}
        style={{ padding: "14px", whiteSpace: "pre-wrap", wordWrap: "break-word", position: "relative", lineHeight: "3.5", zIndex: 1 }}
      >
        {pageData}
      </pre>

      {highlightBoxes.map((box, i) => {
          const isHovered = hoveredBox?.start === box.start && hoveredBox?.end === box.end;
        
          return (
            <div
              key={i}
              onMouseEnter={() => setHoveredBox({ start: box.start, end: box.end })}
              onMouseLeave={() => setHoveredBox(null)}
              style={{
                position: "absolute",
                top: (box.top ?? 0) + (box.stackOffset ?? 0) - 2,
                left: (box.left ?? 0) - 2,
                width: (box.width ?? 0) + 4,
                height: (box.height ?? 0) + 4,
                backgroundColor: box.isRelation ? "transparent" : box.color,
                opacity: box.isRelation ? 1 : 0.4,
                zIndex: 2,
                pointerEvents: "auto",
                borderRadius: "6px",
                padding: "2px",
                border: box.isRelation
                  ? `2px solid ${darkenHSLColor(box.color)}`
                  : "none",
                boxShadow: isHovered
                  ? "0 0 6px 2px rgba(0,0,0,0.3)"
                  : "none",
                cursor: "pointer",
                transition: "all 0.2s ease-in-out",
              }}
            >
              {(box.label || box.note) && (
                <div
                  style={{
                    position: "absolute",
                    top: "-1.6em",
                    left: 0,
                    display: "flex",
                    alignItems: "center",
                    flexWrap: "wrap",
                    backgroundColor: darkenHSLColor(box.color),
                    color: "#fff",
                    fontSize: "0.6em",
                    fontWeight: 600,
                    padding: "2px 6px",
                    borderRadius: "6px",
                    whiteSpace: "nowrap",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.25)",
                    maxWidth: "100%",
                    gap: "0.25em",
                    textTransform: "uppercase",
                  }}
                >
                  <span>{userRole === "Adjudicator" && box.note}</span>
                  <span>{userRole !== "Adjudicator" && box.label}</span>
                </div>
              )}
            </div>
          );
      })}

    </div>
  );
};

export default PageDisplayBuilder;
