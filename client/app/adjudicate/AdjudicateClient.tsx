'use client';

import { useEffect, useState, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { getHistoryFile, getCaseById } from '../lib/api';
import type { FileData, Annotation } from '../lib/interfaces';
import PageDisplay from '../components/page-display-brat';
import { generateOptionColors } from '../lib/util';

export default function AdjudicateClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const folderParam = searchParams.get('project');
  const folder = folderParam || 'askMyFAERS';
  const file = searchParams.get('file');
  const id = searchParams.get('id');

  const [loading, setLoading] = useState(true);
  const [fileData, setFileData] = useState<FileData | null>(null);
  const [user, setUser] = useState<any>(null);
  const [adjudications, setAdjudications] = useState<Record<number, { status: string; reason: string }>>({});
  const [selectedAnn, setSelectedAnn] = useState<any>(null);
  
  // Popup for reasons
  const [reasonPopup, setReasonPopup] = useState<{ id: number; status: string; text: string } | null>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
    setUser(JSON.parse(storedUser));

    const load = async () => {
      if (!file && !id) return;
      setLoading(true);
      
      const data = id 
        ? await getCaseById(id, folder)
        : await getHistoryFile(file!, folder);

      if (data) {
        setFileData(data);
        const initialAdj: Record<number, any> = {};
        data.annotations.forEach((ann: any) => {
          if (ann.adjudication) {
            try {
              initialAdj[ann.id] = JSON.parse(ann.adjudication);
            } catch(e) {
              initialAdj[ann.id] = { status: 'not-assessed', reason: '' };
            }
          } else {
            initialAdj[ann.id] = { status: 'not-assessed', reason: '' };
          }
        });
        setAdjudications(initialAdj);
      }
      setLoading(false);
    };
    load();
  }, [folder, file, id, router]);

  const humanAnnotations = useMemo<Annotation[]>(() => {
    if (!fileData) return [];
    return fileData.annotations.filter((a: Annotation) => {
      const note = a.note.toUpperCase();
      const isAI = note.includes('AI') || note.includes('LLM') || note.includes('LLAMA') || note.includes('BERT');
      return !isAI || note.includes('VERIFIED');
    });
  }, [fileData]);

  const optionColors = useMemo(() => {
    const labels = Array.from(new Set(humanAnnotations.map((a: Annotation) => a.label.toUpperCase())));
    return generateOptionColors(labels as string[]);
  }, [humanAnnotations]);

  const handleStatusChange = (annId: number, status: string) => {
    if (status === 'denied' || status === 'modified') {
      setReasonPopup({ id: annId, status, text: adjudications[annId]?.reason || '' });
    } else {
      saveAdjudication(annId, status, '');
    }
  };

  const saveAdjudication = async (annId: number, status: string, reason: string) => {
    try {
      const res = await fetch('/api/adjudicate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          annotation_id: annId,
          status,
          reason,
          user_id: user?.id
        })
      });
      if (res.ok) {
        setAdjudications(prev => ({ ...prev, [annId]: { status, reason } }));
        setReasonPopup(null);
      }
    } catch (e) {
      alert('Failed to save adjudication');
    }
  };

  const getAnnotatorDisplay = (note: string) => {
    const upperNote = note.toUpperCase();
    if (['SME1', 'SME2', 'ADJUDICATOR'].includes(upperNote)) return 'DevUser';
    return note;
  };

  if (loading || !fileData) return <div className="p-8">Loading for adjudication...</div>;

  return (
    <div className="flex flex-col h-screen bg-slate-50 overflow-hidden">
      {/* Header */}
      <header className="h-14 bg-white border-b border-slate-200 flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-sm font-bold text-slate-900 uppercase tracking-widest">Quality Adjudication</h1>
          <span className="text-[11px] text-slate-400 font-medium">{folder} / {file}</span>
        </div>
        <button onClick={() => window.close()} className="text-xs font-bold text-slate-500 hover:text-slate-900">Close Window</button>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Checklist */}
        <aside className="w-1/2 border-r border-slate-200 bg-white flex flex-col overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
            <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Annotation Checklist ({humanAnnotations.length})</h2>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {humanAnnotations.map((ann: any, idx: number) => {
              const keyId = ann.id || `idx-${idx}`;
              const adj = adjudications[ann.id] || { status: 'not-assessed', reason: '' };
              const isSelected = selectedAnn?.id === ann.id;

              return (
                <div 
                  key={keyId} 
                  onClick={() => setSelectedAnn(ann)}
                  className={`p-4 border rounded-lg transition-all cursor-pointer ${
                    isSelected ? 'ring-2 ring-blue-500 shadow-md' : ''
                  } ${
                    adj.status === 'approved' ? 'border-emerald-200 bg-emerald-50/30' :
                    adj.status === 'denied' ? 'border-red-200 bg-red-50/30' :
                    adj.status === 'modified' ? 'border-amber-200 bg-amber-50/30' : 'border-slate-200 bg-white'
                  }`}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="min-w-0">
                      <span className="inline-block px-2 py-0.5 rounded text-[9px] font-black text-white uppercase mb-1" style={{ backgroundColor: optionColors[ann.label.toUpperCase()] }}>
                        {ann.label}
                      </span>
                      <p className="text-sm font-bold text-slate-800 break-words">"{ann.textContext.text}"</p>
                      <p className="text-[10px] text-slate-400 mt-1 font-medium italic">By {getAnnotatorDisplay(ann.note)}</p>
                    </div>
                    <div className="flex gap-1" onClick={e => e.stopPropagation()}>
                      {['approved', 'denied', 'modified'].map(s => {
                        const isActive = adj.status === s;
                        return (
                          <button
                            key={s}
                            onClick={() => handleStatusChange(ann.id, s)}
                            className={`px-2 py-1 rounded text-[10px] font-bold uppercase transition-all shadow-sm ${
                              isActive 
                              ? (s === 'approved' ? 'bg-emerald-600 text-white' : s === 'denied' ? 'bg-red-600 text-white' : 'bg-amber-500 text-white')
                              : 'bg-white text-slate-400 border border-slate-200 hover:bg-slate-50'
                            }`}
                          >
                            {s === 'approved' ? '✓' : s === 'denied' ? '✗' : '±'} {s}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  {adj.reason && (
                    <div className="mt-2 p-2 bg-white/50 border border-slate-100 rounded text-[11px] text-slate-600 leading-relaxed">
                      <span className="font-bold uppercase text-[9px] block mb-0.5">Note:</span>
                      {adj.reason}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </aside>

        {/* Right: Narrative */}
        <main className="w-1/2 flex flex-col bg-white overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center gap-2">
            <h2 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Reference Narrative</h2>
            <span className="text-[9px] bg-slate-200 text-slate-500 px-1.5 py-0.5 rounded font-black uppercase">Read Only</span>
          </div>
          <div className="flex-1 overflow-y-auto p-8 bg-slate-50/20">
            <div className="max-w-3xl mx-auto">
              <PageDisplay
                annotations={humanAnnotations}
                updateAnnotationNote={() => {}} // Read only
                userRole="Adjudicator"
                currentPage={0}
                pageData={fileData.pages[0] || ''}
                optionColors={optionColors}
                handleTextSelection={() => {}}
                activeLabelFilters={Array.from(new Set(humanAnnotations.map(a => a.label.toUpperCase())))}
                disableFilter={true}
                annotationSet="SME"
                selectedTermContext={selectedAnn ? { text: selectedAnn.textContext.text, start: selectedAnn.textContext.start, end: selectedAnn.textContext.end } : null}
                setSelectedTermContext={(ctx) => {
                  if (ctx) {
                    const found = humanAnnotations.find(a => a.textContext.start === ctx.start);
                    if (found) setSelectedAnn(found);
                  }
                }}
                isReadOnly={true}
              />
            </div>
          </div>
        </main>
      </div>

      {/* Reason Modal */}
      {reasonPopup && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[200] flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6 animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-bold text-slate-900 mb-2 uppercase tracking-tight">
              {reasonPopup.status === 'denied' ? 'Denial Reason' : 'Modification Notes'}
            </h3>
            <p className="text-sm text-slate-500 mb-4 font-medium leading-relaxed">
              Please provide a brief explanation for this decision. This feedback will be recorded.
            </p>
            <textarea
              autoFocus
              value={reasonPopup.text}
              onChange={e => setReasonPopup({ ...reasonPopup, text: e.target.value })}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:border-blue-500 outline-none transition-all font-sans leading-relaxed mb-4 min-h-[120px]"
              placeholder="Enter text..."
            />
            <div className="flex gap-3">
              <button
                onClick={() => setReasonPopup(null)}
                className="flex-1 px-4 py-2 text-slate-600 text-sm font-bold hover:text-slate-900 transition-colors"
              >
                CANCEL
              </button>
              <button
                onClick={() => saveAdjudication(reasonPopup.id, reasonPopup.status, reasonPopup.text)}
                className={`flex-1 px-4 py-2 text-white rounded-lg text-sm font-bold transition-all ${
                  reasonPopup.status === 'denied' ? 'bg-red-600 hover:bg-red-700' : 'bg-amber-500 hover:bg-amber-600'
                }`}
              >
                SUBMIT DECISION
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
