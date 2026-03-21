'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Annotate_Panel from '../components/annotate_panel';

export default function AnnoToolClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const folder = searchParams.get('project');
  const file = searchParams.get('file');

  const [ready, setReady] = useState(false);
  const [overrideFile, setOverrideFile] = useState('');
  const [currFolder, setCurrFolder] = useState('');

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
    
    if (!folder || !file) return;
    setOverrideFile(file);
    setCurrFolder(folder);
    setReady(true);
  }, [folder, file, router]);

  if (!ready) return <div className="p-6">Loading annotation tool...</div>;

  return (
    <Annotate_Panel
      overrideFileName={overrideFile}
      overrideFolder={currFolder}
    />
  );
}
