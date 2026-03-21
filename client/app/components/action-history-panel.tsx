import React from 'react';
import { ActionRecord } from '../lib/doc-reducer';

interface Props {
  history: ActionRecord[];
  onUndo: (actionId: string) => void;
  optionColors: { [key: string]: string };
}

const ActionHistoryPanel: React.FC<Props> = ({ history, onUndo, optionColors }) => {
  return (
    <div className="flex flex-col h-full bg-gray-50 border-l border-gray-200 w-[300px]">
      <div className="p-4 border-b border-gray-200 bg-white">
        <h2 className="text-xs font-black text-gray-800 uppercase tracking-widest">Recent Actions</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2">
        {(!history || history.length === 0) ? (
          <div className="text-center py-10 text-gray-400 text-xs font-bold italic">
            No recent actions
          </div>
        ) : (
          <div className="space-y-2">
            {history.map((record) => (
              <div 
                key={record.id}
                onClick={() => onUndo(record.id)}
                className="group relative bg-white p-3 rounded-lg border border-gray-200 shadow-sm hover:border-blue-400 hover:shadow-md cursor-pointer transition-all animate-in fade-in slide-in-from-right-4 duration-200"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase ${
                    record.type === 'add' ? 'bg-emerald-100 text-emerald-700' :
                    record.type === 'verify' ? 'bg-blue-100 text-blue-700' :
                    record.type === 'reject' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {record.type}
                  </span>
                  <span className="text-[8px] font-bold text-gray-400">
                    {new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                  </span>
                </div>
                
                <div className="text-xs font-bold text-gray-800 line-clamp-2 mb-1">
                  "{record.annotation.textContext.text}"
                </div>
                
                <div className="flex items-center gap-2">
                   <div 
                     className="w-2 h-2 rounded-full" 
                     style={{ backgroundColor: optionColors[record.annotation.label] || '#ccc' }}
                   />
                   <span className="text-[9px] font-black text-gray-500 uppercase">{record.annotation.label}</span>
                </div>

                {/* Undo Overlay */}
                <div className="absolute inset-0 bg-blue-600/90 rounded-lg flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                   <span className="text-white text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
                     <span>↺</span> Undo Action
                   </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="p-3 bg-gray-100 border-t border-gray-200 text-[8px] font-bold text-gray-400 text-center uppercase tracking-tighter">
        Click an item to restore state
      </div>
    </div>
  );
};

export default ActionHistoryPanel;
