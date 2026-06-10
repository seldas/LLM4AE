'use client';

import { forwardRef } from 'react';

interface Props {
  file: File | null;
  handleFileChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handleUpload: () => void;
  handleTextPaste: (e: React.FocusEvent<HTMLTextAreaElement>) => void;
  saveFileName: string;
  handleSaveFileName: (fileName: string) => void;
  handleSave: () => void;
  handleClear: () => void;  
}

const UserInput = forwardRef<HTMLInputElement, Props>(function UserInput(props, ref) {
  return (
    <div className="w-full max-w-3xl mx-auto bg-white p-6 rounded-lg shadow-md mb-8 border border-gray-200">
      
    
      <div className="flex flex-wrap items-center gap-3 mb-4">
          <h1 className="text-xl font-semibold text-gray-800 whitespace-nowrap">
            Upload PDF or DOCX
          </h1>
          <label htmlFor="customFileInput" className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md cursor-pointer shadow-sm">
            Upload File...
          </label>
          <input id="customFileInput" type="file" onChange={props.handleFileChange} ref={ref} accept=".pdf, .docx" className="hidden" />
          <button disabled={!props.file} onClick={props.handleUpload} className="px-4 py-2 text-sm bg-green-600 text-white rounded-md disabled:bg-gray-300">
            Upload
          </button>
          {props.file && (
            <span className="text-sm text-gray-600 italic max-w-xs truncate">
              {props.file.name}
            </span>
          )}
      </div>

      <h3 className="text-lg font-semibold mb-2 text-gray-700">✏️ Or paste input text below</h3>
    
      {/* Textarea Input */}
      <textarea
        placeholder="Paste text here for annotation..."
        className="w-full min-h-[50px] border border-gray-300 rounded-md p-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-6"
        onBlur={props.handleTextPaste}
      />
    </div>

  );
});

export default UserInput;
