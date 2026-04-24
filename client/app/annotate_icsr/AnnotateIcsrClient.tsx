'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import AnnotateIcsrPanel from '../components/annotate_icsr_panel';

export default function AnnotateIcsrClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const id = searchParams.get('id');

  const [ready, setReady] = useState(false);
  const [currId, setCurrId] = useState('');

  useEffect(() => {
    // For ICSR integration, we might not strictly require login if it's an embedded view,
    // but for now let's keep it consistent with the main app.
    const storedUser = localStorage.getItem('user');
    
    if (!id) {
        setReady(true); // Set ready but we'll show an error if id is missing
        return;
    }
    setCurrId(id);
    setReady(true);
  }, [id, router]);

  if (!ready) return <div className="p-6">Loading ICSR annotation tool...</div>;

  if (!currId) {
    return (
      <div className="p-12 text-center bg-slate-50 min-h-screen">
        <h1 className="text-xl font-bold text-red-600 mb-4 uppercase tracking-tight">Integration Error</h1>
        <p className="text-slate-600 mb-6 max-w-md mx-auto">
          No ICSR Case ID was provided. Please ensure you are accessing this tool via the correct intake workflow.
        </p>
        <button 
          onClick={() => router.push('/')}
          className="px-6 py-2 bg-slate-900 text-white rounded font-bold text-xs uppercase tracking-widest"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  return (
    <AnnotateIcsrPanel
      overrideProject="AskMyFAERS_Integration"
      overrideId={currId}
    />
  );
}
