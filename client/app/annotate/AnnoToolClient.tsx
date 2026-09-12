'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Annotate_Panel from '../components/annotate_panel';

export default function AnnoToolClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const project = searchParams.get('project');
  const id = searchParams.get('id');

  const [ready, setReady] = useState(false);
  const [currProject, setCurrProject] = useState('');
  const [currId, setCurrId] = useState('');

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
    
    if (!id) return;
    setCurrProject(project || 'askMyFAERS');
    setCurrId(id);
    setReady(true);
  }, [project, id, router]);

  if (!ready) return <div className="p-6">Loading annotation tool...</div>;

  return (
    <Annotate_Panel
      overrideProject={currProject}
      overrideId={currId}
    />
  );
}
