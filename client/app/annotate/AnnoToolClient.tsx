'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Annotate_Panel from '../components/annotate_panel';

export default function AnnoToolClient() {
  const searchParams = useSearchParams();
  const folder = searchParams.get('project');
  const file = searchParams.get('file');

  const [ready, setReady] = useState(false);
  const [overrideFile, setOverrideFile] = useState('');
  const [currFolder, setCurrFolder] = useState('');

  useEffect(() => {
    if (!folder || !file) return;
    setOverrideFile(file);
    setCurrFolder(folder);
    setReady(true);
  }, [folder, file]);

  if (!ready) return <div className="p-6">Loading annotation tool...</div>;

  return (
    <Annotate_Panel
      overrideFileName={overrideFile}
      overrideFolder={currFolder}
    />
  );
}
