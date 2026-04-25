import React, { useEffect, useRef, useState } from 'react';
import { AnnotationGuideline, AnnotationOptions, ContextMenu } from "../../lib/interfaces";

interface Props {
  contextMenu: ContextMenu & { type: 'annotation' | 'relationship' | 'verification'; options?: string[] };
  annotationOptions: AnnotationOptions[];
  optionColors: { [key: string]: string };
  annotationGuidelines: AnnotationGuideline[];
  addAnnotation: (label: string) => void;
  handleAddRelationship: (label: string) => void;
  closeContextMenu: () => void;
  isReadOnly?: boolean;
}

const UnifiedContextMenuDisplay = ({
  contextMenu,
  annotationOptions,
  optionColors,
  annotationGuidelines,
  addAnnotation,
  handleAddRelationship,
  closeContextMenu,
  isReadOnly
}: Props) => {
  const menuRef = useRef<HTMLDivElement>(null);
  const [selectedGuideline, setSelectedGuideline] = useState<AnnotationGuideline | null>(null);

  useEffect(() => {
    const handleClickOutsideOrEscape = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof MouseEvent) {
        if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
          closeContextMenu();
        }
      }
      if (event instanceof KeyboardEvent && event.key === 'Escape') {
        closeContextMenu();
      }
    };

    document.addEventListener('mousedown', handleClickOutsideOrEscape);
    document.addEventListener('keydown', handleClickOutsideOrEscape);
    return () => {
      document.removeEventListener('mousedown', handleClickOutsideOrEscape);
      document.removeEventListener('keydown', handleClickOutsideOrEscape);
    };
  }, [closeContextMenu]);

  if (isReadOnly) return null;

  return (
    <div
      ref={menuRef}
      style={{
        position: 'absolute',
        top: `${contextMenu.y}px`,
        left: `${contextMenu.x}px`,
        backgroundColor: '#fff',
        border: '1px solid #ccc',
        borderRadius: '8px',
        padding: '8px',
        zIndex: 1000,
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        minWidth: '180px',
        maxWidth: '360px',
        animation: 'fadeIn 0.2s ease-in-out',
      }}
    >
      {contextMenu.type === 'annotation' && (
        <div className="space-y-3">
          <label className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500">Annotation Category</label>
            <select
              value={selectedGuideline?.label || ''}
              onChange={(e) => {
                const matched = annotationGuidelines.find(item => item.label === e.target.value);
                setSelectedGuideline(matched || null);
              }}
              className="w-full rounded border border-slate-200 px-3 py-2 text-[11px] font-semibold text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all"
            >
              <option value="" disabled>Select category</option>
              {annotationGuidelines.map((item) => (
                <option key={item.label} value={item.label}>{item.label}</option>
              ))}
            </select>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-[10px] text-slate-600 min-h-[64px]">
            {selectedGuideline ? (
              <>
                <p className="font-semibold text-slate-900 mb-1">{selectedGuideline.description}</p>
                <p className="text-[9px] text-slate-500 italic">{selectedGuideline.rule}</p>
              </>
            ) : (
              <p className="text-[9px] text-slate-500 italic">Choose a category to see its definition.</p>
            )}
          </div>
          <button
            onClick={() => selectedGuideline && addAnnotation(selectedGuideline.label)}
            disabled={!selectedGuideline}
            className="w-full py-2 rounded-lg bg-blue-600 text-white text-xs font-bold uppercase tracking-[0.3em] transition-all hover:bg-blue-700 disabled:bg-slate-300"
          >
            OK
          </button>
        </div>
      )}

      {contextMenu.type === 'relationship' &&
        (contextMenu.options || []).map((option) => (
          <div
            key={option}
            onClick={() => {
              handleAddRelationship(option);
              closeContextMenu();
            }}
            style={{
              cursor: 'pointer',
              padding: '6px 10px',
              marginBottom: '4px',
              borderRadius: '6px',
              backgroundColor: '#fdf2e9',
              color: '#6e2c00',
              fontSize: '13px',
              fontWeight: 500,
              textAlign: 'center',
              transition: 'background-color 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = '#f8c471';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = '#fdf2e9';
            }}
          >
            {option}
          </div>
        ))}
    </div>
  );
};

export default UnifiedContextMenuDisplay;
