import React, { useEffect, useRef } from 'react';
import { AnnotationOptions } from '../../lib/interfaces';

interface Props {
  x: number;
  y: number;
  visible: boolean;
  text: string;
  annotationOptions: AnnotationOptions;
  selectedLabel: string;
  onChangeLabel: (label: string) => void;
  onAdd: () => void;
  onClose: () => void;
}

const LLMAnnotationPopup: React.FC<Props> = ({
  x,
  y,
  visible,
  text,
  annotationOptions,
  selectedLabel,
  onChangeLabel,
  onAdd,
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
  
  useEffect(() => {
    if (visible && !selectedLabel) {
      const defaultLabel = Object.keys(annotationOptions)[0] || '';
      onChangeLabel(defaultLabel); // set initial label if not set
    }
  }, [visible, annotationOptions, selectedLabel, onChangeLabel]);

  if (!visible) return null;

  return (
    <div
      ref={menuRef}
      className="absolute z-50 bg-white border border-gray-300 shadow-xl rounded-lg p-4 text-sm text-gray-800
                 backdrop-blur-sm ring-1 ring-black/5 transition-all animate-fadeIn"
      style={{ top: y, left: x, minWidth: '220px' }}
    >
      <div className="mb-1"><strong>{text}</strong></div>

      <label className="block mt-2 mb-1 text-xs text-gray-600">Annotation Label:</label>
      <select
        className="w-full border rounded px-2 py-1 text-sm"
        value={selectedLabel}
        onChange={(e) => onChangeLabel(e.target.value)}
      >
        {Object.keys(annotationOptions).map((label) => (
          <option key={label} value={label}>{label}</option>
        ))}
      </select>

      <div className="flex justify-end gap-2 mt-4">
        <button onClick={onClose} className="text-sm px-3 py-1 border rounded text-gray-700 hover:bg-gray-200">Cancel</button>
        <button onClick={onAdd} className="text-sm px-3 py-1 border rounded bg-blue-600 text-white hover:bg-blue-700">Add</button>
      </div>
    </div>
  );
};

export default LLMAnnotationPopup;
