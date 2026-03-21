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
  setSelectedTermContext,
  isReadOnly
}: Props) {
  const textRef = useRef<HTMLPreElement>(null);
  const [highlightBoxes, setHighlightBoxes] = useState<any[]>([]);
  const [hoveredBox, setHoveredBox] = useState<null | { start: number; end: number }>(null);
  const [lineCount, setLineCount] = useState(0);
  const isSME = ["SME1", "SME2", "MJ.L"].includes(userRole);
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

    const smeAnnotations = annotations.filter(a => {
      const note = a.note.toUpperCase();
      const isAI = note.includes('LLM') || note.includes('AI') || a.note.toLowerCase().includes('llama') || a.note.toLowerCase().includes('bert');
      return !isAI && !note.includes('REJECTED');
    });

    annotations.forEach((annotation) => {
      const { start, end, text } = annotation.textContext;
      if (start === undefined || end === undefined) return;

      const note = annotation.note.toUpperCase();
      const isRejected = note.includes('REJECTED');

      // Skip AI annotations if there is an exact SME match (start/end)
      const isAIAnnotation = note.includes('LLM') || 
                            note.includes('AI') || 
                            annotation.note.toLowerCase().includes('llama') || 
                            annotation.note.toLowerCase().includes('bert');
      
      if (isAIAnnotation && !isRejected) {
        const hasSmeMatch = smeAnnotations.some(sme => 
          sme.textContext.start === start && sme.textContext.end === end
        );
        if (hasSmeMatch) return;
      }

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
      const plainText = (container.innerText || "").replace(/\u00A0/g, ' ');
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
        const plainText = (container.innerText || "").replace(/\u00A0/g, ' ');
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

  useEffect(() => {
    if (userRole === "Adjudicator") {
      const sme1Annotations = annotations.filter((a) => a.note.includes('SME1'));
      const sme2Annotations = annotations.filter((a) => a.note.includes('SME2'));
      const newDifferences = compareAnnotations(sme1Annotations, sme2Annotations);
      setDifferences(newDifferences);
    }
  }, [annotations, userRole, compareAnnotations]);

  return (
    <div className="page flex" style={{ margin: "10px auto" }} onMouseUp={() => !isReadOnly && handleTextSelection()}>
      {/* Visual Gutter */}
      <div 
        className="flex-shrink-0 text-right pr-4 text-gray-300 select-none font-mono text-xs border-r border-gray-100" 
        style={{ 
          width: '50px', 
          lineHeight: '3.5rem', 
          paddingTop: '14px',
          marginTop: '0px'
        }}
      >
        {Array.from({ length: lineCount }).map((_, i) => (
          <div key={i}>{i + 1}</div>
        ))}
      </div>

      <div className="relative flex-1 min-w-0">
        <pre
          ref={textRef}
          className="text-block whitespace-pre-wrap"
          style={{
            fontFamily: "'Calibri', 'Segoe UI', sans-serif",
            padding: "14px",
            whiteSpace: "pre-wrap",
            wordWrap: "break-word",
            position: "relative",
            lineHeight: "3.5rem",
            zIndex: 1,
            margin: 0
          }}
        >
          {processedPageData}
        </pre>


      {highlightBoxes.map((box, i) => {
        const isSelected = selectedTermContext?.start === box.start && selectedTermContext?.end === box.end;
        const isSummarySelected = selectedTermContext?.start === box.start && selectedTermContext?.end === box.end && selectedTermContext?.text === box.text;
        const isMatchHighlight = box.isMatchHighlight;
        const isTextMatch = isSME && selectedTermContext?.text?.toLowerCase() === box.text?.toLowerCase();
        
        // Focus Mode: Dim anything that isn't the selected term or a match
        const isDimmed = selectedTermContext && !isSelected && !isSummarySelected && !isMatchHighlight;

        const hasLabel = box.label && box.label !== "match";
        
        const noteUpper = box.note?.toUpperCase() || "";
        const isAI = noteUpper.includes('LLM') || noteUpper.includes('AI') || noteUpper.includes('LLAMA') || noteUpper.includes('BERT');
        const isHuman = noteUpper.includes('SME') || noteUpper.includes('MJ.L') || noteUpper.includes('K.L') || noteUpper.includes('ADJUDICATOR');
        const isRejected = noteUpper.includes('REJECTED');
        const isVerified = box.isVerified || (isHuman && !isAI && !isRejected); // Human-made or explicit verified
        
        return (
          <div
            key={i}
            onClick={(e) => {
              e.stopPropagation();
              if (userRole !== "Adjudicator"){ 
                if ((box.isMatchHighlight || box.note === 'Keyword')) {
                  if (onClickAnnotation) {
                    setSelectedTermContext({ text: box.text, start: box.start, end: box.end });
                    onClickAnnotation(box.text, box.start, box.end, e.pageX, e.pageY, box.note, box.label);
                    return;
                  }  
                }

                const isTermAlreadySelected = selectedTermContext?.start === box.start && selectedTermContext?.end === box.end && selectedTermContext?.text === box.text;
                if (isTermAlreadySelected) {
                  setSelectedTermContext(null);
                } else {
                  setSelectedTermContext({ text: box.text, start: box.start, end: box.end });
                  if (onClickAnnotation) {
                    onClickAnnotation(box.text, box.start, box.end, e.pageX, e.pageY, box.note, box.label);
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
              opacity: isDimmed ? 0.1 : (isRejected ? 0.4 : 1),
              backgroundColor: isDimmed 
                ? 'transparent'
                : isMatchHighlight
                  ? 'transparent'
                  : isRejected
                    ? 'rgba(156, 163, 175, 0.1)'
                    : isVerified 
                      ? `${box.color.replace('hsl', 'hsla').replace(')', ', 0.15)')}`
                      : 'transparent',
              zIndex: isSelected ? 10 : 2,
              pointerEvents: isDimmed ? "none" : "auto",
              borderRadius: "4px",
              borderBottom: isDimmed
                ? 'none'
                : isSelected || isSummarySelected
                  ? '3px solid #ff0000'
                  : isMatchHighlight 
                    ? '2px dashed #ff0000'
                    : isRejected
                      ? '2px dotted #9ca3af'
                      : isAI && !isVerified
                        ? `2px dashed ${darkenHSLColor(box.color)}`
                        : `2px solid ${darkenHSLColor(box.color)}`,
              boxShadow: box.isDiscrepancy ? '0 0 6px 3px rgba(255,0,0,0.4)' : "none",
              cursor: isDimmed ? "default" : "pointer",
              transition: "all 0.1s ease-in-out",
            }}
          >
            {(userRole !== "Adjudicator" && (box.label || box.note) && !isDimmed) && (
              <div
                style={{
                  position: "absolute",
                  top: isAI && !isHuman ? "-1.8em" : "-2.2em",
                  left: 0,
                  display: "flex",
                  alignItems: "center",
                  backgroundColor: isRejected 
                    ? "#9ca3af" 
                    : isAI && !isVerified 
                      ? "white" 
                      : darkenHSLColor(box.color),
                  color: isRejected
                    ? "white"
                    : isAI && !isVerified 
                      ? darkenHSLColor(box.color) 
                      : "white",
                  fontSize: "9px",
                  fontWeight: 800,
                  padding: "2px 6px",
                  borderRadius: "4px",
                  whiteSpace: "nowrap",
                  border: isRejected
                    ? "1px solid #9ca3af"
                    : `1px solid ${darkenHSLColor(box.color)}`,
                  boxShadow: "0 2px 4px rgba(0, 0, 0, 0.1)",
                  gap: "4px",
                  zIndex: 10,
                  textDecoration: isRejected ? 'line-through' : 'none'
                }}
              >
                <span>
                  {isRejected ? '🚫' : isAI && !isVerified ? (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg>
                  ) : (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  )}
                </span>
                <span>{box.label}</span>
                {isVerified && <span style={{ marginLeft: '2px' }}>✓</span>}
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
    </div>
  );
}

export default PageDisplay;
