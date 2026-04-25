import React from 'react';
import { ActionRecord } from '../lib/doc-reducer';

interface Props {
  history: ActionRecord[];
  onUndo: (actionId: string) => void;
  optionColors: { [key: string]: string };
}

const ActionHistoryPanel: React.FC<Props> = ({ history, onUndo, optionColors }) => {
  return (
    <div className="flex flex-col h-full bg-slate-50/50 overflow-hidden">
      <div className="flex-1 overflow-y-auto p-3">
        {(!history || history.length === 0) ? (
          <div className="text-center py-20">
            <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-6 h-6 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            </div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">No recent actions</p>
          </div>
        ) : (
          <div className="space-y-3">
            {history.map((record) => (
              <div 
                key={record.id}
                onClick={() => onUndo(record.id)}
                className="group relative bg-white p-3 rounded-xl border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md cursor-pointer transition-all animate-in fade-in slide-in-from-right-4 duration-200"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-[8px] font-black px-2 py-0.5 rounded-full uppercase tracking-tighter ${
                    record.type === 'add' ? 'bg-emerald-100 text-emerald-700' :
                    record.type === 'verify' ? 'bg-blue-100 text-blue-700' :
                    record.type === 'reject' ? 'bg-red-100 text-red-700' :
                    'bg-slate-100 text-slate-700'
                  }`}>
                    {record.type}
                  </span>
                  <span className="text-[8px] font-bold text-slate-400">
                    {new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
                
                <div className="text-[11px] font-bold text-slate-800 line-clamp-2 mb-2 leading-snug">
                  "{record.annotation.textContext.text}"
                </div>
                
                <div className="flex items-center gap-2">
                   <div 
                     className="w-1.5 h-1.5 rounded-full" 
                     style={{ backgroundColor: optionColors[record.annotation.label.toUpperCase()] || '#ccc' }}
                   />
                   <span className="text-[9px] font-black text-slate-500 uppercase tracking-tight">{record.annotation.label}</span>
                </div>

                {/* Undo Overlay */}
                <div className="absolute inset-0 bg-blue-600/95 rounded-xl flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-10">
                   <svg className="w-5 h-5 text-white mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"/></svg>
                   <span className="text-white text-[9px] font-black uppercase tracking-[0.2em]">Undo Action</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="p-3 bg-slate-100/80 border-t border-slate-200 text-[9px] font-bold text-slate-400 text-center uppercase tracking-widest">
        Click to restore
      </div>
    </div>
  );
};

export default ActionHistoryPanel;
