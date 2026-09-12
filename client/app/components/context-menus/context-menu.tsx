import { AnnotationOptions, ContextMenu } from "../../lib/interfaces";
import React, { useEffect, useRef } from 'react';

interface Props {
  contextMenu: ContextMenu;
  annotationOptions: AnnotationOptions;
  optionColors: { [key: string]: string };
  addAnnotation: (label: string) => void;
  closeContextMenu: () => void;  
}

const ContextMenuDisplay = (props: Props) => {
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
      const handleClickOutsideOrEscape = (event: MouseEvent | KeyboardEvent) => {
        // Close on outside click
        if (event instanceof MouseEvent) {
          if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
            props.closeContextMenu();
          }
        }
    
        // Close on Escape key
        if (event instanceof KeyboardEvent && event.key === 'Escape') {
          props.closeContextMenu();
        }
      };
    
      document.addEventListener('mousedown', handleClickOutsideOrEscape);
      document.addEventListener('keydown', handleClickOutsideOrEscape);
    
      return () => {
        document.removeEventListener('mousedown', handleClickOutsideOrEscape);
        document.removeEventListener('keydown', handleClickOutsideOrEscape);
      };
  }, [props]);
    
  return (
    <div
      ref={menuRef}  
      style={{
        position: 'absolute',
        top: `${props.contextMenu.y}px`,
        left: `${props.contextMenu.x}px`,
        backgroundColor: '#fff',
        border: '1px solid #ccc',
        borderRadius: '8px',
        padding: '8px',
        zIndex: 1000,
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        minWidth: '300px',
        maxWidth: '500px',
        display: 'flex',
        flexWrap: 'wrap',
        gap: '6px',
        animation: 'fadeIn 0.2s ease-in-out'
      }}
    >
      {Object.keys(props.annotationOptions).map((option) => (
        <div
          key={option}
          onClick={() => props.addAnnotation(option)}
          style={{
            cursor: 'pointer',
            padding: '6px 10px',
            borderRadius: '6px',
            backgroundColor: props.optionColors[option] || '#f2f2f2',
            color: '#333',
            fontSize: '13px',
            fontWeight: 500,
            transition: 'background-color 0.2s ease',
            textAlign: 'center',
            whiteSpace: 'nowrap'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#e0e0e0';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = props.optionColors[option] || '#f2f2f2';
          }}
        >
          {option}
        </div>
      ))}
    </div>
  );
};

export default ContextMenuDisplay;
