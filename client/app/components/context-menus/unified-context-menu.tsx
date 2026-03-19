import React, { useEffect, useRef } from 'react';
import { AnnotationOptions, ContextMenu } from "../../lib/interfaces";

interface Props {
  contextMenu: ContextMenu & { type: 'annotation' | 'relationship' | 'verification'; options?: string[] };
  annotationOptions: AnnotationOptions;
  optionColors: { [key: string]: string };
  addAnnotation: (label: string) => void;
  handleAddRelationship: (label: string) => void;
  closeContextMenu: () => void;
}

const UnifiedContextMenuDisplay = ({
  contextMenu,
  annotationOptions,
  optionColors,
  addAnnotation,
  handleAddRelationship,
  closeContextMenu,
}: Props) => {
  const menuRef = useRef<HTMLDivElement>(null);

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
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '6px',
            padding: '4px',
            maxWidth: '240px', // adjust based on your layout
          }}
        >
          {Object.keys(annotationOptions).map((option) => (
            <div
              key={option}
              onClick={() => {
                addAnnotation(option);
                closeContextMenu();
              }}
              style={{
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: '4px',
                backgroundColor: optionColors[option] || '#f2f2f2',
                color: '#333',
                fontSize: '11px',
                fontWeight: 500,
                transition: 'background-color 0.2s ease',
                whiteSpace: 'nowrap',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#e0e0e0';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = optionColors[option] || '#f2f2f2';
              }}
            >
              {option}
            </div>
          ))}
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