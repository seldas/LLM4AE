import React, { useEffect, useRef } from 'react';
import { AnnotationOptions } from '../../lib/interfaces';

interface Props {
  x: number;
  y: number;
  visible: boolean;
  text: string;
  annotationOptions: AnnotationOptions;
  type?: 'AI' | 'SME' | 'NEW';
  userRole?: string;
  selectedLabel: string;
  isVerified?: boolean;
  onAdd: (label?: string) => void;
  onUnverify?: () => void;
  onReject?: () => void;
  onRemove?: () => void;
  onClose: () => void;
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
  onClose
}) => {
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
                 backdrop-blur-sm ring-1 ring-black/5 transition-all animate-fadeIn w-[240px]"
      style={{ top: y, left: x }}
    >
      {/* Header with Close Button */}
      <div className="flex justify-between items-start mb-2">
        <div className="pr-4 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[9px] font-black text-gray-400 uppercase tracking-widest whitespace-nowrap">
              {type === 'AI' ? 'AI Suggestion' : type === 'SME' ? `Human Tag: ${userRole || ''}` : 'Quick Tag'}
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

      <div className="flex flex-col gap-2 mt-3 pt-3 border-t border-gray-100">
        {type === 'AI' && (
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
              Reject AI
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
          <button 
            onClick={() => onAdd(selectedLabel)} 
            className="w-full py-2 rounded-lg bg-blue-600 text-white font-bold text-xs hover:bg-blue-700 shadow-sm transition-all"
          >
            Tag as {selectedLabel || 'Annotation'}
          </button>
        )}
      </div>
    </div>
  );
};

export default LLMAnnotationPopup;
