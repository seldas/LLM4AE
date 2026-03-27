// assess_panel.tsx
'use client';

import React, { useMemo, useState, useRef, useCallback, useEffect } from 'react';
import type { Annotation } from '../lib/interfaces';

interface Props {
  pages: string[];
  meta?: any;
  annotations: Annotation[];
  folder: string;
  fileName: string;
  id?: string;
}

type DemographicEntry = {
  label: string;
  type: 'text' | 'list';
  value?: string;
  items?: string[];
};

type ProductField = {
  label: string;
  value: string;
};

type ProductItem = {
  display_name: string;
  fields: ProductField[];
};

type ProductGroup = {
  role: string;
  count: number;
  items: ProductItem[];
};

type ProductsMeta = {
  mode?: string;
  groups: ProductGroup[];
};

type OutcomeRow = {
  term_id?: number;
  soc?: string;
  hlgt?: string;
  hlt?: string;
  pt?: string;
  llt?: string;
  term_label?: string;
  term_event?: string;
  start_date?: string;
};

type OutcomesMeta = {
  mode?: string;
  rows: OutcomeRow[];
  categories?: Record<string, { rank?: number; text?: string }[]>;
};

type LlmHeaderObject = {
  suspected_drug?: string;
  primary_adverse_event?: string;
  judgment?: string;
};

type LlmReason = {
  id?: string;
  title?: string;
  finding?: string;
  evidence?: string;
};

interface LlmAssessResponse {
  header?: LlmHeaderObject | string;
  summary?: string;
  reasons?: LlmReason[];
  risk_warning?: string | null;
}

type StoredAssessment = {
  selected_judgment?: AssessmentOption | null;
  scores?: Partial<Record<AssessmentOption, number>>;
  llm_response?: LlmAssessResponse | null;
  reason_checks?: boolean[];
};

const ASSESSMENT_OPTIONS = [
  'Certain',
  'Probable',
  'Possible',
  'Unlikely',
  'Unassessable',
] as const;

type AssessmentOption = (typeof ASSESSMENT_OPTIONS)[number];

function AssessmentOutcomeControls({
  onSelect,
  loading,
  scores,
  selected,
}: {
  onSelect: (option: AssessmentOption) => void;
  loading: boolean;
  scores?: Partial<Record<AssessmentOption, number>>;
  selected: AssessmentOption | null;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm font-medium text-gray-700">Assessment outcome</label>
      <div className="flex flex-wrap gap-2">
        {ASSESSMENT_OPTIONS.map((option) => {
          const isActive = selected === option;
          return (
            <button
              key={option}
              type="button"
              onClick={() => {
                onSelect(option);
              }}
              disabled={loading}
              className={[
                'px-3 py-1.5 rounded-full text-xs font-semibold border transition',
                loading
                  ? 'bg-gray-200 text-gray-400 border-gray-300 cursor-not-allowed'
                  : isActive
                  ? 'bg-indigo-600 text-white border-indigo-700 shadow'
                  : 'bg-white text-gray-700 border-gray-300 hover:bg-indigo-50',
              ].join(' ')}
            >
              {option}
              {scores && typeof scores[option] === 'number'
                ? ` (${scores[option]}%)`
                : ''}
            </button>
          );
        })}
      </div>
      <p className="text-xs text-gray-500 mt-1">
        Only one outcome can be active at a time; clicking a different option will update the selection.
      </p>
    </div>
  );
}

export default function AssessPanel({ pages, meta, annotations, folder, fileName, id }: Props) {
  const firstPageText = pages?.[0] || '';
  const textRef = useRef<HTMLPreElement>(null);
  const [lineCount, setLineCount] = useState(0);

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
  const initialAssessment: StoredAssessment | undefined =
    (meta && (meta as any).assessment) || undefined;

  const demographicEntries = useMemo(() => {
    const raw = meta?.demographic;
    return Array.isArray(raw) ? (raw as DemographicEntry[]) : undefined;
  }, [meta]);

  const demographicHtml = useMemo(() => {
    if (demographicEntries) return '';
    const raw = meta?.demographic;
    return typeof raw === 'string' ? raw : '';
  }, [meta, demographicEntries]);

  const productsData = useMemo(() => {
    const raw = meta?.products;
    if (raw && typeof raw === 'object' && !Array.isArray(raw) && Array.isArray((raw as ProductsMeta).groups)) {
      return raw as ProductsMeta;
    }
    return undefined;
  }, [meta]);

  const productsHtml = useMemo(() => {
    if (productsData) return '';
    const raw = meta?.products;
    return typeof raw === 'string' ? raw : '';
  }, [meta, productsData]);

  const outcomesData = useMemo(() => {
    const raw = meta?.outcomes;
    if (raw && typeof raw === 'object' && !Array.isArray(raw) && (Array.isArray((raw as OutcomesMeta).rows) || raw.categories)) {
      return raw as OutcomesMeta;
    }
    return undefined;
  }, [meta]);

  const outcomesHtml = useMemo(() => {
    if (outcomesData) return '';
    const raw = meta?.outcomes;
    return typeof raw === 'string' ? raw : '';
  }, [meta, outcomesData]);

  const demographicPayload = demographicEntries
    ? formatDemographicText(demographicEntries)
    : stripHtmlTags(demographicHtml);
  const productsPayload = productsData
    ? formatProductsText(productsData)
    : stripHtmlTags(productsHtml);
  const outcomesPayload = outcomesData
    ? formatOutcomesText(outcomesData)
    : stripHtmlTags(outcomesHtml);

  const [selectedOutcome, setSelectedOutcome] = useState<AssessmentOption | null>(
    (initialAssessment?.selected_judgment as AssessmentOption) || null
  );

  const [llmData, setLlmData] = useState<LlmAssessResponse | null>(
    initialAssessment?.llm_response || null
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scoreMap, setScoreMap] = useState<Partial<Record<AssessmentOption, number>>>(
    initialAssessment?.scores || {}
  );

  const [reasonChecks, setReasonChecks] = useState<boolean[]>(
    initialAssessment?.reason_checks || []
  );
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const reasons: LlmReason[] = useMemo(
    () => (llmData?.reasons ? llmData.reasons : []),
    [llmData]
  );

  // Reset checklist when a new explanation/reasons arrive;
  // keep existing checks if lengths match (e.g., loaded from saved meta).
  React.useEffect(() => {
    setReasonChecks((prev) => {
      if (prev.length === reasons.length && prev.length > 0) {
        return prev;
      }
      return reasons.map(() => false);
    });
  }, [reasons]);

  const handleSelectOutcome = async (option: AssessmentOption) => {
    if (!firstPageText) return;
    setSelectedOutcome(option);
    setIsLoading(true);
    setError(null);
    setLlmData(null);
    setReasonChecks([]);

    try {
      const res = await fetch('/api/llm-assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          narrative: firstPageText,
          demographic_html: demographicPayload,
          products_html: productsPayload,
          outcomes_html: outcomesPayload,
          judgment: option,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error || 'Failed to generate explanation');
      }
      setLlmData(json as LlmAssessResponse);
    } catch (e: any) {
      setError(e.message || 'Unexpected error while generating explanation.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveAssessment = async () => {
    try {
      const payload: StoredAssessment = {
        selected_judgment: selectedOutcome,
        scores: Object.keys(scoreMap).length ? scoreMap : undefined,
        llm_response: llmData,
        reason_checks: reasonChecks.length ? reasonChecks : undefined,
      };

      const res = await fetch('/api/save-assessment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: id,
          file: fileName,
          folder,
          assessment: payload,
        }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.error || 'Failed to save assessment');
      }
      setSaveMessage('Assessment saved.');
      setTimeout(() => setSaveMessage(null), 3000);
    } catch (e: any) {
      setSaveMessage(`Save failed: ${e.message || 'Unexpected error'}`);
      setTimeout(() => setSaveMessage(null), 5000);
    }
  };

  // Fetch probabilistic scores once when narrative/meta are available,
  // unless scores already exist in meta.assessment.
  React.useEffect(() => {
    const loadScores = async () => {
      if (!firstPageText) return;
      if (Object.keys(scoreMap).length > 0) return;
      try {
        const res = await fetch('/api/llm-assess-scores', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            narrative: firstPageText,
            demographic_html: demographicPayload,
            products_html: productsPayload,
            outcomes_html: outcomesPayload,
          }),
        });
        const json = await res.json();
        if (!res.ok) {
          console.error('Failed to load assess scores:', json.error || res.statusText);
          return;
        }
        const scores = (json && json.scores) || {};
        const mapped: Partial<Record<AssessmentOption, number>> = {};
        (['Certain', 'Probable', 'Possible', 'Unlikely', 'Unassessable'] as AssessmentOption[]).forEach(
          (key) => {
            const rawVal = scores[key];
            if (typeof rawVal === 'number') {
              mapped[key] = Math.round(rawVal);
            }
          }
        );
        setScoreMap(mapped);
      } catch (e) {
        console.error('Unexpected error while loading assess scores:', e);
      }
    };
    loadScores();
  }, [firstPageText, demographicPayload, productsPayload, outcomesPayload, scoreMap]);

  React.useEffect(() => {
    updateLineCount();
  }, [updateLineCount, firstPageText]);

  React.useEffect(() => {
    const container = textRef.current;
    if (!container) return;
    const observer = new ResizeObserver(updateLineCount);
    observer.observe(container);
    return () => observer.disconnect();
  }, [updateLineCount]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-end sticky top-0 z-10 bg-white/80 backdrop-blur-sm pb-2">
        {saveMessage && (
          <span className="mr-3 text-xs text-gray-600">{saveMessage}</span>
        )}
        <button
          type="button"
          onClick={handleSaveAssessment}
          className="px-4 py-2 text-xs font-semibold rounded-md bg-emerald-600 hover:bg-emerald-700 text-white shadow"
        >
          Save Assessment
        </button>
      </div>
      {/* Annotated Narratives Display Section */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
        <h2 className="text-lg font-semibold mb-3 text-gray-800">Annotated Narratives</h2>
        {firstPageText ? (
          <div className="bg-gray-50 border border-gray-200 rounded-md text-sm leading-relaxed max-h-[400px] overflow-y-auto flex">
            {/* Visual Gutter */}
            <div 
              className="flex-shrink-0 text-right pr-4 text-gray-300 select-none font-mono text-xs border-r border-gray-200 bg-gray-100/50" 
              style={{ 
                width: '50px', 
                lineHeight: '3.5rem', 
                paddingTop: '14px'
              }}
            >
              {Array.from({ length: lineCount }).map((_, i) => (
                <div key={i}>{i + 1}</div>
              ))}
            </div>
            
            <div className="flex-1 min-w-0">
              <pre 
                ref={textRef}
                className="whitespace-pre-wrap text-gray-900 p-3.5" 
                style={{ fontFamily: "'Calibri', 'Segoe UI', sans-serif", lineHeight: '3.5rem', margin: 0 }}
              >
                {firstPageText}
              </pre>
            </div>
          </div>
        ) : (
          <div className="text-sm text-gray-500 italic">No narrative text available.</div>
        )}
      </div>

      {/* Demographic Information */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
        <h2 className="text-lg font-semibold mb-3 text-gray-800">Demographic Information</h2>
        {demographicEntries ? (
          renderDemographicEntries(demographicEntries)
        ) : demographicHtml ? (
          <div
            className="p-3 bg-gray-50 border border-gray-200 rounded-md text-sm leading-relaxed prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: demographicHtml }}
          />
        ) : (
          <div className="text-sm text-gray-500 italic">No demographic information available.</div>
        )}
      </div>

      {/* Product Information */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
        <h2 className="text-lg font-semibold mb-3 text-gray-800">Product Information</h2>
        {productsData ? (
          renderProductGroups(productsData)
        ) : productsHtml ? (
          <div
            className="p-3 bg-gray-50 border border-gray-200 rounded-md text-sm leading-relaxed prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: productsHtml }}
          />
        ) : (
          <div className="text-sm text-gray-500 italic">No product information available.</div>
        )}
      </div>

      {/* Outcomes Information */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
        <h2 className="text-lg font-semibold mb-3 text-gray-800">Outcomes</h2>
        {outcomesData ? (
          renderOutcomesEntries(outcomesData)
        ) : outcomesHtml ? (
          <div
            className="p-3 bg-gray-50 border border-gray-200 rounded-md text-sm leading-relaxed prose prose-sm max-w-none"
            dangerouslySetInnerHTML={{ __html: outcomesHtml }}
          />
        ) : (
          <div className="text-sm text-gray-500 italic">No outcomes information available.</div>
        )}
      </div>

      {/* Assessment Section */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
        <h2 className="text-lg font-semibold mb-3 text-gray-800">Assessment</h2>
        <div className="flex flex-col md:flex-row gap-4 items-start">
          <AssessmentOutcomeControls
            onSelect={handleSelectOutcome}
            loading={isLoading}
            scores={scoreMap}
            selected={selectedOutcome}
          />

          <div className="flex-1">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">Explanation</h3>
            {error && (
              <div className="p-3 mb-2 bg-red-50 border border-red-200 rounded-md text-sm text-red-700">
                {error}
              </div>
            )}
            <div className="p-3 bg-gray-50 border border-gray-200 rounded-md text-sm text-gray-700">
              {isLoading && 'Generating explanation from LLM...'}
              {!isLoading && !llmData && !error && (
                <span className="text-gray-500">
                  Select an assessment outcome to generate an explanation based on the narrative and meta information.
                </span>
              )}
              {!isLoading && llmData && (
                <>
                  {/* Meta-info / Header */}
                  {llmData.header && (
                    <div className="mb-3 p-2 bg-white border border-gray-200 rounded-md text-xs text-gray-800">
                      <div className="font-semibold text-gray-700 mb-1">
                        Case Meta Information
                      </div>
                      {typeof llmData.header === 'string' ? (
                        <p className="whitespace-pre-wrap">{llmData.header}</p>
                      ) : (
                        <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
                          {llmData.header.suspected_drug && (
                            <>
                              <dt className="font-medium text-gray-600">Suspected Drug</dt>
                              <dd className="text-gray-800">
                                {llmData.header.suspected_drug}
                              </dd>
                            </>
                          )}
                          {llmData.header.primary_adverse_event && (
                            <>
                              <dt className="font-medium text-gray-600">
                                Primary Adverse Event
                              </dt>
                              <dd className="text-gray-800">
                                {llmData.header.primary_adverse_event}
                              </dd>
                            </>
                          )}
                          {llmData.header.judgment && (
                            <>
                              <dt className="font-medium text-gray-600">
                                Reviewer&apos;s Judgment
                              </dt>
                              <dd className="text-gray-800">
                                {llmData.header.judgment}
                              </dd>
                            </>
                          )}
                        </dl>
                      )}
                    </div>
                  )}

                  {/* Summary */}
                  {llmData.summary && (
                    <div className="mb-3 p-2 bg-indigo-50 border border-indigo-100 rounded-md text-xs text-gray-800">
                      <div className="font-semibold text-gray-700 mb-1">
                        Explanation Summary
                      </div>
                      <p className="whitespace-pre-wrap">{llmData.summary}</p>
                    </div>
                  )}

                  {/* Checkable list of reasons */}
                  {reasons.length > 0 && (
                    <div className="mb-3 p-2 bg-white border border-indigo-100 rounded-md text-xs text-gray-800">
                      <div className="font-semibold text-gray-700 mb-1">
                        Checklist of Reasons
                      </div>
                      <ul className="space-y-1">
                        {reasons.map((reason, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <input
                              type="checkbox"
                              className="mt-0.5 h-3 w-3 accent-indigo-600"
                              checked={reasonChecks[idx] || false}
                              onChange={() =>
                                setReasonChecks((prev) => {
                                  const next = [...prev];
                                  next[idx] = !next[idx];
                                  return next;
                                })
                              }
                            />
                            <div className="flex-1">
                              <div className="font-semibold text-gray-800">
                                {reason.title || reason.id || `Reason ${idx + 1}`}
                              </div>
                              {reason.finding && (
                                <div className="text-gray-700">
                                  {reason.finding}
                                </div>
                              )}
                              {reason.evidence && (
                                <div className="text-gray-500">
                                  <span className="font-medium">Evidence: </span>
                                  {reason.evidence}
                                </div>
                              )}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Risk warning, only when present */}
                  {llmData.risk_warning && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-300 rounded-md text-xs text-red-800">
                      {llmData.risk_warning}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const stripHtmlTags = (value?: string): string =>
  value ? value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() : '';

const formatDemographicText = (entries: DemographicEntry[]): string =>
  entries
    .map(entry => {
      if (entry.type === 'list') {
        return `${entry.label}: ${(entry.items || []).join('; ')}`;
      }
      return `${entry.label}: ${entry.value || ''}`;
    })
    .filter(Boolean)
    .join('\n');

const formatProductsText = (data?: ProductsMeta): string => {
  if (!data || !Array.isArray(data.groups)) return '';
  const pieces: string[] = [];
  data.groups.forEach(group => {
    (group.items || []).forEach(item => {
      const detail = item.fields.map(field => `${field.label}: ${field.value}`).join(' | ');
      pieces.push(`Role: ${group.role} - ${item.display_name}${detail ? ` | ${detail}` : ''}`);
    });
  });
  return pieces.join('\n');
};

const formatOutcomesText = (data?: OutcomesMeta): string => {
  if (!data) return '';
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const rowPieces = rows.map(row => {
    const columns = [
      `SOC: ${row.soc || '—'}`,
      `HLGT: ${row.hlgt || '—'}`,
      `HLT: ${row.hlt || '—'}`,
      `PT: ${row.pt || '—'}`,
      `LLT: ${row.llt || '—'}`
    ].join(', ');
    const header = row.term_label || row.term_event || `Term ${row.term_id || '—'}`;
    return `${header}${row.start_date ? ` | Start: ${row.start_date}` : ''} | ${columns}`;
  });
  const categoryPieces = data.categories
    ? Object.entries(data.categories)
        .map(([category, items]) => {
          const textList = (Array.isArray(items) ? items.map(item => item?.text || '').filter(Boolean) : []).join(', ');
          return `${category}: ${textList || 'Not provided'}`;
        })
        .filter(Boolean)
    : [];
  return [...rowPieces, ...categoryPieces].filter(Boolean).join('\n');
};

const renderDemographicEntries = (entries: DemographicEntry[]): React.ReactNode => (
  <div className="space-y-3">
    {entries.map((entry, idx) => (
      <div key={`${entry.label}-${idx}`} className="bg-gray-50 border border-gray-200 rounded-2xl p-4">
        <p className="text-[9px] uppercase tracking-[0.3em] text-gray-500 mb-2">{entry.label}</p>
        {entry.type === 'list' ? (
          <ul className="list-disc list-inside text-sm text-gray-700 space-y-1">
            {(entry.items || []).map((item, itemIdx) => (
              <li key={itemIdx}>{item}</li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-700">{entry.value || '—'}</p>
        )}
      </div>
    ))}
  </div>
);

const renderProductGroups = (data: ProductsMeta): React.ReactNode => {
  if (!Array.isArray(data.groups) || !data.groups.length) {
    return <p className="text-sm text-gray-500 italic">No product information available.</p>;
  }
  return (
    <div className="space-y-4">
      {data.groups.map(group => (
        <div key={group.role} className="space-y-3">
            <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-gray-500">
              <span>{group.role}</span>
              <span>{group.count ?? (group.items?.length ?? 0)} products</span>
            </div>
          <div className="space-y-3">
            {(group.items || []).map((item, idx) => (
              <div key={`${group.role}-${idx}`} className="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm">
                <div className="text-sm font-semibold text-gray-900 mb-2">{item.display_name}</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[12px] text-gray-700">
                  {item.fields.map(field => (
                    <div key={`${field.label}-${field.value}`} className="space-y-1">
                      <p className="text-[10px] uppercase tracking-[0.3em] text-gray-400">{field.label}</p>
                      <p className="font-semibold text-gray-800">{field.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

const renderOutcomesEntries = (data: OutcomesMeta): React.ReactNode => {
  const rows = Array.isArray(data.rows) ? data.rows : [];
  const categories = data.categories || {};
  if (!rows.length && !Object.keys(categories).length) {
    return <p className="text-sm text-gray-500 italic">No outcomes listed.</p>;
  }
  return (
    <div className="space-y-4">
      {Object.entries(categories).length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.entries(categories).map(([category, items]) => (
            <div key={category} className="bg-white border border-gray-200 rounded-2xl p-3 text-[10px] uppercase tracking-[0.3em] text-gray-500">
              <div className="font-semibold text-gray-800 mb-1">{category}</div>
              <p className="text-[12px] text-gray-600">
                {(Array.isArray(items) ? items.map(item => item?.text || '').filter(Boolean) : []).join(', ') ||
                  'Not provided'}
              </p>
            </div>
          ))}
        </div>
      )}
      {rows.map((row, idx) => (
        <div key={`outcome-row-${idx}`} className="bg-gray-50 border border-gray-200 rounded-2xl p-4">
          <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-gray-400 mb-2">
            <span>Term {row.term_id || idx + 1}</span>
            <span>{row.start_date ? `Start: ${row.start_date}` : 'Start date unknown'}</span>
          </div>
          <div className="text-sm font-semibold text-gray-900 mb-1">{row.term_label || row.term_event || '—'}</div>
          <div className="grid grid-cols-2 gap-3 text-[12px] text-gray-600">
            <div>SOC: {row.soc || '—'}</div>
            <div>HLGT: {row.hlgt || '—'}</div>
            <div>HLT: {row.hlt || '—'}</div>
            <div>PT: {row.pt || '—'}</div>
            <div>LLT: {row.llt || '—'}</div>
          </div>
        </div>
      ))}
    </div>
  );
};
