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
    if (!storedUser) {
        // If not logged in, we could redirect to login with a return URL,
        // but let's just check if we have a user.
        // router.push('/login');
        // return;
    }
    
    if (!id) return;
    setCurrId(id);
    setReady(true);
  }, [id, router]);

  if (!ready) return <div className="p-6">Loading ICSR annotation tool...</div>;

  return (
    <AnnotateIcsrPanel
      overrideProject="AskMyFAERS_Integration"
      overrideId={currId}
    />
  );
}
