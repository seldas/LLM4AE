import React, { useEffect, useRef, useMemo, useState } from 'react';
import { AnnotationOptions } from '../../lib/interfaces';

interface Props {
  x: number;
  y: number;
  visible: boolean;
  text: string;
  annotationOptions: AnnotationOptions[];
  type?: 'LLM' | 'BERT' | 'SME' | 'NEW';
  userRole?: string;
  selectedLabel: string;
  isVerified?: boolean;
  onAdd: (label?: string) => void;
  onUnverify?: () => void;
  onReject?: () => void;
  onRemove?: () => void;
  onClose: () => void;
  isReadOnly?: boolean;
}

const LLMAnnotationPopup: React.FC<Props> = ({
  x,
  y,
  visible,
  text,
  type = 'NEW',
  userRole,
  selectedLabel,
  isVerified = false,
  onAdd,
  onUnverify,
  onReject,
  onRemove,
  onClose,
  isReadOnly
}) => {
  type CategoryGuideline = {
    label: string;
    description: string;
    rule: string;
    color: string;
  };

  const CATEGORY_GUIDELINES: CategoryGuideline[] = useMemo(() => [
    {
      label: 'SDrug',
      description: 'A drug or biological product believed to have caused, contributed to, or been associated with the adverse event.',
      rule: 'Use causal language or temporal link and note clinical actions taken on the drug.',
      color: '#d92626'
    },
    {
      label: 'CDrug',
      description: 'Drugs administered concurrently as part of the patient’s regular regimen.',
      rule: 'Annotate when drugs are listed without causal links, often described as background or chronic therapy.',
      color: '#5b2ef1'
    },
    {
      label: 'ODrug',
      description: 'Drugs that are mentioned without a clear connection to the current adverse event.',
      rule: 'Use for general drug references, disposition history, illicit substances, or when context is not tied to a symptom.',
      color: '#d99c00'
    },
    {
      label: 'Dose',
      description: 'Explicit dosage information, frequency, or dose adjustments.',
      rule: 'Capture dosing details such as mg, frequency, and upward/downward adjustments.',
      color: '#4426d9'
    },
    {
      label: 'Treatment',
      description: 'Drugs described as treatment interventions addressing disease, adverse events, or symptoms.',
      rule: 'Annotate when medications are explicitly called treatments or therapy.',
      color: '#25a3ff'
    },
    {
      label: 'AE',
      description: 'Any negative health outcome, condition, or symptom that occurs during or immediately after the adverse event.',
      rule: 'Annotate conditions or symptoms described with causal or temporal language linking them to AE.',
      color: '#d92626'
    },
    {
      label: 'mAE',
      description: 'Manifestations and sequelae that appear immediately during or after the adverse event.',
      rule: 'Capture signs, symptoms, or complications described in relation to the adverse event.',
      color: '#ff69b4'
    },
    {
      label: 'bSYM',
      description: 'Pre-existing symptoms or findings unrelated to the adverse event.',
      rule: 'Annotate chronic findings or conditions described prior to AE onset.',
      color: '#7fbf00'
    },
    {
      label: 'RO',
      description: 'Conditions that were considered but ruled out as causes of the symptoms.',
      rule: 'Tag when the narrative specifies a diagnosis was excluded or lacked evidence.',
      color: '#ed8f0d'
    },
    {
      label: 'Dx',
      description: 'Diagnostic procedures performed to evaluate or confirm a condition.',
      rule: 'Include names of imaging, biopsies, or other diagnostic tests.',
      color: '#d92626'
    },
    {
      label: 'CoD',
      description: 'Specific cause or reason for death potentially related to the drug.',
      rule: 'Annotate when death is attributed to a condition connected to the medication.',
      color: '#ffb703'
    },
    {
      label: 'Lab',
      description: 'Laboratory results and measurements indicating biochemical markers.',
      rule: 'Capture test names plus results such as elevated or normal values.',
      color: '#bf2ae7'
    },
    {
      label: 'FHx',
      description: 'Family medical history often tied to genetic predispositions.',
      rule: 'Annotate references to conditions described in relatives or inherited context.',
      color: '#16a34a'
    },
    {
      label: 'MHx',
      description: 'Medical conditions or findings that pre-existed before the adverse event.',
      rule: 'Use for past medical history language like prior diagnosis or baseline conditions.',
      color: '#e7f11a'
    },
    {
      label: 'IND',
      description: 'Intended medical purpose or reason for a drug/procedure.',
      rule: 'Select when the narrative states why a drug was prescribed or used.',
      color: '#34d399'
    },
    {
      label: 'Status',
      description: 'Statements about clinical progression, recovery, stability, or outcome.',
      rule: 'Annotate mentions of resolution, deterioration, stability, or complications.',
      color: '#5b9cdd'
    },
    {
      label: 'Age',
      description: 'Age of the patient during the described event.',
      rule: 'Include any stated ages or age descriptors.',
      color: '#1e88e5'
    },
    {
      label: 'Sex',
      description: 'Biological sex of the patient mentioned in the narrative.',
      rule: 'Annotate when sex is explicitly stated.',
      color: '#1e88e5'
    },
    {
      label: 'Date',
      description: 'Exact or partial dates mentioned.',
      rule: 'Use when the text specifies a calendar date.',
      color: '#1e88e5'
    },
    {
      label: 'Time',
      description: 'Specific times of day mentioned.',
      rule: 'Annotate clock times or general times like AM, PM.',
      color: '#1e88e5'
    },
    {
      label: 'Duration',
      description: 'Length of time over which an event occurs or persists.',
      rule: 'Capture spans described as hours, days, weeks, etc.',
      color: '#2193b5'
    },
    {
      label: 'Relative',
      description: 'Time expressions expressed relative to other events.',
      rule: 'Tag before/after language that places events relative to one another.',
      color: '#2193b5'
    },
    {
      label: 'Latency',
      description: 'Time interval between an initial event and a subsequent adverse event.',
      rule: 'Include statements describing how long after an intervention the AE occurred.',
      color: '#27ae60'
    },
    {
      label: 'Temporal',
      description: 'Explicit temporal markers showing timing of adverse events.',
      rule: 'Capture phrases like “hours later,” “days before,” or “next morning.”',
      color: '#31a3d2'
    }
  ], []);
  const [selectedGuideline, setSelectedGuideline] = useState<CategoryGuideline | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutsideOrEscape = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof MouseEvent) {
        if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
          onClose();
        }
      }
      if (event instanceof KeyboardEvent && event.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutsideOrEscape);
    document.addEventListener('keydown', handleClickOutsideOrEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutsideOrEscape);
      document.removeEventListener('keydown', handleClickOutsideOrEscape);
    };
  }, [onClose]);

  if (!visible) return null;

  return (
      <div
        ref={menuRef}
        className="absolute z-50 bg-white border border-gray-300 shadow-2xl rounded-xl p-4 text-sm text-gray-800
                 backdrop-blur-sm ring-1 ring-black/5 transition-all animate-fadeIn w-[260px]"
        style={{ top: y, left: x }}
      >
      {/* Header with Close Button */}
      <div className="flex justify-between items-start mb-2">
        <div className="pr-4 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest whitespace-nowrap">
              {type === 'LLM' ? 'LLM Suggestion' : type === 'BERT' ? 'BERT Suggestion' : type === 'SME' ? `Human Tag: ${userRole || ''}` : 'Quick Tag'}
            </span>
            {selectedLabel && (
               <span className="bg-blue-50 text-blue-700 text-[9px] font-black px-1.5 py-0.5 rounded border border-blue-100 uppercase truncate">
                {selectedLabel}
              </span>
            )}
          </div>
          <strong className="text-gray-900 leading-tight block truncate">"{text}"</strong>
        </div>
        <button 
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 p-1 -mr-2 -mt-1 transition-colors flex-shrink-0"
        >
          ✕
        </button>
      </div>

      {!isReadOnly && (
        <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-gray-100">
          {(type === 'LLM' || type === 'BERT') && (
            <>
              <button 
                onClick={() => isVerified ? onUnverify?.() : onAdd(selectedLabel)} 
                className={`w-full py-2 rounded-lg font-bold text-xs shadow-sm transition-all flex items-center justify-center gap-2 ${
                  isVerified 
                  ? "bg-amber-500 hover:bg-amber-600 text-white" 
                  : "bg-emerald-600 hover:bg-emerald-700 text-white"
                }`}
              >
                <span>{isVerified ? '↺' : '✓'}</span> {isVerified ? 'Unverify' : 'Verify'}
              </button>
              <button 
                onClick={onReject} 
                className="w-full py-2 rounded-lg border border-red-200 text-red-600 font-bold text-xs hover:bg-red-50 transition-all"
              >
                Reject {type}
              </button>
            </>
          )}

          {type === 'SME' && (
            <button 
              onClick={onRemove} 
              className="w-full py-2 rounded-lg bg-red-50 text-red-600 font-bold text-xs hover:bg-red-100 transition-all"
            >
              Remove
            </button>
          )}

          {type === 'NEW' && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {CATEGORY_GUIDELINES.map(item => (
                  <button
                    key={item.label}
                    onClick={() => setSelectedGuideline(item)}
                    className={`px-3 py-1 rounded-md text-[11px] font-bold transition-all border ${selectedGuideline?.label === item.label ? 'border-slate-400 shadow-sm' : 'border-transparent'} whitespace-nowrap`}
                    style={{ backgroundColor: item.color, color: '#1d1d1f' }}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-[10px] text-slate-600 min-h-[56px]">
                {selectedGuideline ? (
                  <>
                    <p className="font-semibold text-slate-900 mb-1">{selectedGuideline.description}</p>
                    <p className="text-[9px] text-slate-500 italic">{selectedGuideline.rule}</p>
                  </>
                ) : (
                  <p className="text-[9px] text-slate-500">Choose a guideline to see its definition.</p>
                )}
              </div>
              <button
                onClick={() => selectedGuideline && onAdd(selectedGuideline.label)}
                className="w-full py-2 rounded-lg bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 shadow-sm transition-all"
                disabled={!selectedGuideline}
              >
                OK
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LLMAnnotationPopup;
