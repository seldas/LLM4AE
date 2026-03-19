import React, { useEffect, useRef, useState, useCallback } from "react";
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
  onClickAnnotation?: (text: string, start: number, end: number, x: number, y: number) => void;
  selectedTermContext: { text: string; start: number; end: number } | null;
  setSelectedTermContext: (context: { text: string; start: number; end: number } | null) => void;
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

  // Apply multiplicative darkening (e.g., 0.5 = 50% of original lightness)
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
  setSelectedTermContext
}: Props) {
  const textRef = useRef<HTMLPreElement>(null);
  const [highlightBoxes, setHighlightBoxes] = useState<any[]>([]);
  const [hoveredBox, setHoveredBox] = useState<null | { start: number; end: number }>(null);
  const isSME = ["SME1", "SME2"].includes(userRole);
  const [discrepancyPopup, setDiscrepancyPopup] = useState<null | {
    box: any;
    x: number;
    y: number;
  }>(null);
  
  const reasons = ["Exceed", "Incomplete", "Wrong Label Type", "Others"];
  const [selectedReason, setSelectedReason] = useState("");
        
  const compareAnnotations = useCallback((sme1Annotations: Annotation[], sme2Annotations: Annotation[]) => {
    const differences: { 
      type: 'missing' | 'mismatch',
      sme1Annotation: Annotation, 
      sme2Annotation: Annotation 
    }[] = [];

    const processedPairs = new Set<string>();

    // Helper function to add a difference
    const addDifference = (type: 'missing' | 'mismatch', sme1Annotation: Annotation, sme2Annotation: Annotation) => {
      const key = `${sme1Annotation.textContext.start}-${sme1Annotation.textContext.end}`;
      if (!processedPairs.has(key)) {
        differences.push({type, sme1Annotation, sme2Annotation});
        processedPairs.add(key);
      }
    };

    // Check SME1 annotations
    sme1Annotations.forEach((sme1Annotation) => {
      const overlappingSme2Annotation = sme2Annotations.find((a) => {
        const start1 = sme1Annotation.textContext.start!;
        const end1 = sme1Annotation.textContext.end!;
        const start2 = a.textContext.start!;
        const end2 = a.textContext.end!;
        return !(end1 <= start2 || end2 <= start1);
      });

      if (!overlappingSme2Annotation) {
        addDifference('missing', sme1Annotation, sme1Annotation);
      } else if (
        sme1Annotation.textContext.text !== overlappingSme2Annotation.textContext.text || 
        sme1Annotation.textContext.start !== overlappingSme2Annotation.textContext.start || 
        sme1Annotation.textContext.end !== overlappingSme2Annotation.textContext.end ||
        sme1Annotation.label !== overlappingSme2Annotation.label
      ) {
        addDifference('mismatch', sme1Annotation, overlappingSme2Annotation);
      }
    });

    // Check SME2 annotations for missing ones
    sme2Annotations.forEach((sme2Annotation) => {
      const overlappingSme1Annotation = sme1Annotations.find((a) => {
        const start1 = sme2Annotation.textContext.start!;
        const end1 = sme2Annotation.textContext.end!;
        const start2 = a.textContext.start!;
        const end2 = a.textContext.end!;
        return !(end1 <= start2 || end2 <= start1);
      });

      if (!overlappingSme1Annotation) {
        addDifference('missing', sme2Annotation, sme2Annotation);
      }
    });
    return differences;
  }, []); 

  interface Difference {
    type: 'missing' | 'mismatch';
    sme1Annotation: Annotation;
    sme2Annotation: Annotation;
  }

  const [differences, setDifferences] = useState<Difference[]>([]);

  const computeHighlightBoxes = useCallback(() => {
    const container = textRef.current;
    if (!container) return;
    const containerRect = container.getBoundingClientRect();
    const boxes: any[] = [];

    // Create a map of all discrepancies for quick lookup
    const discrepancyMap = new Map<string, any>();
    const validDiscrepancyTypes = ['missing', 'mismatch'];
    differences.forEach((d) => {
      if (validDiscrepancyTypes.includes(d.type)) {
        const key = `${d.sme1Annotation.textContext.start}-${d.sme1Annotation.textContext.end}-${d.sme1Annotation.label}`;
        discrepancyMap.set(key, d);
      } else {
        console.log(`Filtered out difference of type: ${d.type}`);
      }
    });

    annotations.forEach((annotation) => {
      const { start, end, text } = annotation.textContext;
      if (start === undefined || end === undefined) return;
      if (!(disableFilter || activeLabelFilters.includes(annotation.label))) return;
      if (start === end) return;
  
      const key = `${start}-${end}-${annotation.label}`;
      const difference = discrepancyMap.get(key);
  
      const isDiscrepancy = !!difference;
      const isVerified = annotation.note.toLowerCase().includes("verified");
      const isWarned = annotation.note.toLowerCase().includes("warn");
  
      if (userRole === "Adjudicator" && isVerified) return;
      if (userRole === "Adjudicator" && isWarned) return;
  
      const startInfo = getNodeAndOffsetForIndex(container!, start);
      const endInfo = getNodeAndOffsetForIndex(container!, end);
      if (!startInfo || !endInfo) return;
  
      try {
        const range = document.createRange();
        range.setStart(startInfo.node, startInfo.offset);
        range.setEnd(endInfo.node, endInfo.offset);
        const rects = range.getClientRects();
        const color = optionColors[annotation.label] || "rgba(100,100,100,0.4)";
  
        for (const r of rects) {
          boxes.push({
            top: r.top - containerRect.top,
            left: r.left - containerRect.left,
            width: r.width,
            height: r.height,
            label: annotation.label,
            color,
            note: annotation.note,
            isRelation: false,
            isMatchHighlight: false,
            start,
            end,
            text,
            isDiscrepancy,
            isVerified,
            isWarned,
            discrepancyKey: isDiscrepancy ? key : undefined,
            discrepancyType: difference?.type,
          });
        }
      } catch (e) {
        console.warn("Render failed:", e);
      }
    });
     
    if (selectedTermContext?.text &&
      selectedTermContext.text.length > 0
    ) {
      const plainText = container.innerText || "";
      const term = selectedTermContext.text.toLowerCase();
      let match;
      const regex = new RegExp(`\\b${escapeRegExp(term)}\\b`, "gi");
    
      while ((match = regex.exec(plainText)) !== null) {
        const matchStart = match.index;
        const matchEnd = match.index + match[0].length;

        if (
          selectedTermContext &&
          selectedTermContext.start === matchStart &&
          selectedTermContext.end === matchEnd &&
          selectedTermContext.text === match[0]
        ) {
          continue;
        }
    
        const startInfo = getNodeAndOffsetForIndex(container, matchStart);
        const endInfo = getNodeAndOffsetForIndex(container, matchEnd);
    
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
                label: "Keyword",
                color: "rgba(255, 0, 0, 1)",
                note: "Keyword",
                isRelation: false,
                start: matchStart,
                end: matchEnd,
                text: match[0],
                isMatchHighlight: true,
              });
            }
          } catch (e) {
            console.warn("External match rendering failed", e);
          }
        }
      }
    } else if (
      isSME &&
      selectedTermContext?.text &&
      selectedTermContext.text.length > 0 &&
      selectedTermContext.start !== undefined &&
      selectedTermContext.end !== undefined
    ) {
        const plainText = container.innerText || "";
        const selectedTerm = selectedTermContext.text.toLowerCase();
        let match;
        const regex = new RegExp(`\\b${escapeRegExp(selectedTerm)}\\b`, "gi");
        
        // Build a list of all annotated spans to exclude
        const annotatedSpans = annotations
          .filter((a) => 
            typeof a.textContext.start === 'number' &&
            typeof a.textContext.end === 'number' &&
            a.textContext.start !== a.textContext.end
          )
          .map((a) => ({
            start: a.textContext.start!,
            end: a.textContext.end!,
        }));
        
        while ((match = regex.exec(plainText)) !== null) {
          const matchStart = match.index;
          const matchEnd = match.index + match[0].length;
        
          // Skip if match is already part of any annotated span
          const isOverlapping = annotatedSpans.some(
            (span) =>
              Math.max(span.start, matchStart) < Math.min(span.end, matchEnd)
          );
        
          if (isOverlapping) continue;
        
          const startInfo = getNodeAndOffsetForIndex(container, matchStart);
          const endInfo = getNodeAndOffsetForIndex(container, matchEnd);
        
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
                  label: "match",
                  color: "rgba(255,0,0,1)",
                  isRelation: false,
                  start: matchStart,
                  end: matchEnd,
                  text: match[0],
                  isMatchHighlight: true,
                });
              }
            } catch (e) {
              console.warn("Red match rendering failed", e);
            }
          }
        }
    }  
    
    setHighlightBoxes(boxes);
  }, [
    annotations,
    differences,
    optionColors,
    activeLabelFilters,
    disableFilter,
    selectedTermContext,
    userRole
  ]);

  useEffect(() => {
    computeHighlightBoxes();
  }, [computeHighlightBoxes]);

  useEffect(() => {
    const container = textRef.current;
    if (!container || !container.parentElement) return;
    const observer = new ResizeObserver(() => {
      computeHighlightBoxes();
    });
    observer.observe(container.parentElement);
    return () => observer.disconnect();
  }, [computeHighlightBoxes]);

  useEffect(() => {
    if (userRole === "Adjudicator") {
      const sme1Annotations = annotations.filter((a) => a.note.includes('SME1'));
      const sme2Annotations = annotations.filter((a) => a.note.includes('SME2'));
      const newDifferences = compareAnnotations(sme1Annotations, sme2Annotations);
      setDifferences(newDifferences);
    }
  }, [annotations, userRole, compareAnnotations]);

  return (
    <div className="page relative" style={{ margin: "10px auto" }} onMouseUp={handleTextSelection}>
      <pre
        ref={textRef}
        className="text-block whitespace-pre-wrap"
        style={{
          fontFamily: "'Calibri', 'Segoe UI', sans-serif",
          padding: "14px",
          whiteSpace: "pre-wrap",
          wordWrap: "break-word",
          position: "relative",
          lineHeight: "3.5",
          zIndex: 1,
        }}
      >
        {pageData}
      </pre>


      {highlightBoxes.map((box, i) => {
        const isSelected = selectedTermContext?.start === box.start && selectedTermContext?.end === box.end;
        const isSummarySelected = selectedTermContext?.start === box.start && selectedTermContext?.end === box.end && selectedTermContext?.text === box.text;
        const isMatchHighlight = box.isMatchHighlight;
        const isTextMatch = isSME && selectedTermContext?.text?.toLowerCase() === box.text?.toLowerCase();
        const hasLabel = box.label && box.label !== "match";
        
        return (
          <div
            key={i}
            onClick={(e) => {
              e.stopPropagation();
              if (userRole !== "Adjudicator"){ 
                if ((box.isMatchHighlight || box.note === 'Keyword')) {
                  if (onClickAnnotation) {
                    setSelectedTermContext({ text: box.text, start: box.start, end: box.end });
                    onClickAnnotation(box.text, box.start, box.end, e.pageX, e.pageY);
                    return;
                  }  
                }

                const isTermAlreadySelected = selectedTermContext?.start === box.start && selectedTermContext?.end === box.end && selectedTermContext?.text === box.text;
                if (isTermAlreadySelected) {
                  setSelectedTermContext(null);
                } else {
                  setSelectedTermContext({ text: box.text, start: box.start, end: box.end });
                  const canAnnotate = !hasLabel || annotationSet !== 'SME';
                  if (canAnnotate && onClickAnnotation) {
                    onClickAnnotation(box.text, box.start, box.end, e.pageX, e.pageY);
                  }
                }

              }else if (box.isDiscrepancy) {
                setDiscrepancyPopup({ box, x: e.pageX, y: e.pageY });
                return;
              }
            }}
            onMouseEnter={() => setHoveredBox({ start: box.start, end: box.end })}
            onMouseLeave={() => setHoveredBox(null)}
            style={{
              position: "absolute",
              top: (box.top ?? 0) + (box.stackOffset ?? 0) - 2,
              left: (box.left ?? 0) - 2,
              width: (box.width ?? 0) + 4,
              height: (box.height ?? 0) + 4,
              opacity: 1,
              backgroundColor: box.isRelation || box.isMatchHighlight
                ? 'transparent'
                : `${box.color.replace('hsl', 'hsla').replace(')', ', 0.2)')}`,
              zIndex: isSelected ? 10 : 2,
              pointerEvents: "auto",
              borderRadius: "6px",
              padding: "2px",
              border: box.isVerified 
                ? '2px solid green' 
                : box.isWarned 
                ? '2px solid red'
                : isSelected || isSummarySelected
                ? '2px solid #ff0000'
                : isMatchHighlight || isTextMatch
                ? '2px dashed #ff0000'
                : box.isRelation
                ? `2px solid ${darkenHSLColor(box.color)}`
                : 'none',
              boxShadow: box.isDiscrepancy ? '0 0 6px 3px rgba(255,0,0,0.4)' : "none",
              cursor: "pointer",
              transition: "all 0.2s ease-in-out",
            }}
          >
            {(userRole !== "Adjudicator" && (box.label || box.note)) && (
              <div
                style={{
                  position: "absolute",
                  top: "-2.2em",
                  left: 0,
                  display: "flex",
                  alignItems: "center",
                  flexWrap: "wrap",
                  backgroundColor: box.isWarned 
                  ? 'red'
                  : isMatchHighlight
                  ? "#ff0"
                  : "#ffffff",
                  color: box.isWarned 
                  ? '#fff'
                  : darkenHSLColor(box.color),
                  fontSize: isSummarySelected || isSelected ? "1.1em" : "0.6em",
                  fontWeight: 700,
                  padding: "4px 10px",
                  borderRadius: "10px",
                  whiteSpace: "nowrap",
                  border: box.isWarned 
                  ? 'transparent'
                  : `1px solid ${darkenHSLColor(box.color)}`,
                  boxShadow: "0 4px 8px rgba(0, 0, 0, 0.25)",
                  gap: "0.3em",
                  letterSpacing: "0.5px",
                  textTransform: "uppercase",
                  zIndex: 10,
                }}
              >
                <span>
                  {box.isVerified ? "[V] " : ""}
                  {box.isWarned ? "[R!] " : ""}
                  {box.label}
                </span>
              </div>
            )}
            {box.isDiscrepancy && userRole === "Adjudicator" && (
              <div style={{
                position: "absolute",
                top: "-2em",
                left: 0,
                fontSize: "0.7em",
                color: "#f00",
                background: "#fff",
                border: "1px solid #f00",
                padding: "2px 4px",
                borderRadius: "4px",
                fontWeight: 1000,
                zIndex: 11,
              }}>
                Attention!
              </div>
            )}
          </div>
        );
      })}
      
      {discrepancyPopup && (() => {
        
        const popupWidth = 400;
        const popupHeight = 300;
        const margin = 10;

        const x = Math.max(
          margin,
          Math.min(discrepancyPopup.x - 10, window.innerWidth - popupWidth - margin)
        );
        const y = Math.max(
          margin,
          Math.min(discrepancyPopup.y - 100, window.innerHeight - popupHeight - margin)
        );

        const difference = differences.find(d => 
          d.sme1Annotation && 
          d.sme1Annotation.textContext && 
          d.sme1Annotation.textContext.start === discrepancyPopup.box.start &&
          d.sme1Annotation.textContext.end === discrepancyPopup.box.end
        ) || null;

        const handleAccept = (acceptedAnnotation: Annotation, rejectedAnnotation?: Annotation) => {
          const warnNote = selectedReason ? `WARN: ${selectedReason}` : "WARN";

          updateAnnotationNote(
            acceptedAnnotation.textContext.start!,
            acceptedAnnotation.textContext.end!,
            acceptedAnnotation.textContext.text,
            acceptedAnnotation.label,
            "verified"
          );

          if (rejectedAnnotation) {
            updateAnnotationNote(
              rejectedAnnotation.textContext.start!,
              rejectedAnnotation.textContext.end!,
              rejectedAnnotation.textContext.text,
              rejectedAnnotation.label,
              warnNote
            );
          }
        
          setSelectedTermContext(null);
          setDiscrepancyPopup(null);
          setSelectedReason("");
        };
        

        return (
          <div
            className="fixed z-50 bg-white border border-gray-300 rounded-lg shadow-xl p-4 w-[400px]"
            style={{
              top: y,
              left: x,
              animation: 'fadeIn 0.2s ease-out',
            }}
          >
            <h3 className="text-sm font-bold text-red-700 mb-2 border-b pb-1">
              Resolve Discrepancy - {difference?.type
                ? difference.type.charAt(0).toUpperCase() + difference.type.slice(1)
                : 'Unknown'}
            </h3>

            {difference?.type !== 'missing' && (
              <div className="mb-3">
                <div className="mb-2">
                  <h4 className="text-xs font-semibold text-blue-600">SME1 Annotation:</h4>
                  <p className="text-xs text-gray-700">
                    <strong>Text:</strong> "{difference?.sme1Annotation?.textContext.text}"
                  </p>
                  <p className="text-xs text-gray-700">
                    <strong>Label:</strong> {difference?.sme1Annotation?.label}
                  </p>
                  <p className="text-xs text-gray-700">
                    <strong>Range:</strong> {difference?.sme1Annotation?.textContext.start} - {difference?.sme1Annotation?.textContext.end}
                  </p>
                </div>
                <div className="mb-2">
                  <h4 className="text-xs font-semibold text-green-600">SME2 Annotation:</h4>
                  <p className="text-xs text-gray-700">
                    <strong>Text:</strong> "{difference?.sme2Annotation?.textContext.text}"
                  </p>
                  <p className="text-xs text-gray-700">
                    <strong>Label:</strong> {difference?.sme2Annotation?.label}
                  </p>
                  <p className="text-xs text-gray-700">
                    <strong>Range:</strong> {difference?.sme2Annotation?.textContext.start} - {difference?.sme2Annotation?.textContext.end}
                  </p>
                </div>
                <div className="mb-2">
                  <label htmlFor="reason" className="block text-xs font-medium text-gray-700">
                    Reason for selection:
                  </label>
                  <select
                    id="reason"
                    value={selectedReason}
                    onChange={(e) => setSelectedReason(e.target.value)}
                    className="mt-1 block w-full py-2 px-3 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 text-xs"
                  >
                    <option value="">Select a reason</option>
                    {reasons.map((reason) => (
                      <option key={reason} value={reason}>{reason}</option>
                    ))}
                  </select>
                </div>
                <div className="flex justify-between mt-2">
                  {difference?.sme2Annotation && (
                    <div className="flex justify-between mt-2">
                      <button
                        className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-3 py-1 rounded"
                        onClick={() => handleAccept(difference?.sme1Annotation, difference?.sme2Annotation)}
                        disabled={!selectedReason}
                      >
                        Accept SME1
                      </button>
                      <button
                        className="bg-green-600 hover:bg-green-700 text-white text-xs font-semibold px-3 py-1 rounded"
                        onClick={() => handleAccept(difference?.sme2Annotation, difference?.sme1Annotation)}
                        disabled={!selectedReason}
                      >
                        Accept SME2
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {difference?.type === 'missing' && (
              <div className="mb-3">
                <h4 className="text-xs font-semibold text-purple-600">Missing Annotation:</h4>
                <p className="text-xs text-gray-700">
                  <strong>Text:</strong> "{difference?.sme1Annotation.textContext.text}"
                </p>
                <p className="text-xs text-gray-700">
                  <strong>Label:</strong> {difference?.sme1Annotation.label}
                </p>
                <p className="text-xs text-gray-700">
                  <strong>Range:</strong> {difference?.sme1Annotation.textContext.start} - {difference?.sme1Annotation.textContext.end}
                </p>
                <p className="text-xs text-gray-700">
                  <strong>Annotated by:</strong> {difference?.sme1Annotation.note.includes('SME1') ? 'SME1' : 'SME2'}
                </p>
                <button
                  className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold px-3 py-1 rounded w-full mt-2"
                  onClick={() => handleAccept(difference?.sme1Annotation)}
                >
                  Verify Missing Annotation
                </button>
              </div>
            )}

            <button
              className="bg-gray-300 hover:bg-gray-400 text-gray-800 text-xs font-semibold px-3 py-1 rounded w-full"
              onClick={() => setDiscrepancyPopup(null)}
            >
              ❌ Cancel
            </button>
          </div>
        );
      })()}

    </div>
  );
}

export default PageDisplay;
