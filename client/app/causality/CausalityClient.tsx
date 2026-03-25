'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import AssessPanel from '../components/assess_panel';
import { getHistoryFile, getCaseById } from '../lib/api';
import type { FileData } from '../lib/interfaces';

export default function CausalityClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const folder = searchParams.get('project');
  const file = searchParams.get('file');
  const id = searchParams.get('id');

  const [loading, setLoading] = useState(true);
  const [fileData, setFileData] = useState<FileData | null>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }

    const load = async () => {
      if (!folder || (!file && !id)) return;
      setLoading(true);
      const data = id 
        ? await getCaseById(id, folder)
        : await getHistoryFile(file!, folder);
      if (data) setFileData(data);
      setLoading(false);
    };
    load();
  }, [folder, file, id, router]);

  if (!folder || (!file && !id)) {
    return <div className="p-6 text-sm text-red-700">Missing project or identifier parameters.</div>;
  }

  if (loading || !fileData) {
    return <div className="p-6">Loading causality metrics...</div>;
  }

  const rawMeta: any = fileData.meta || {};
  const caseNumber =
    (rawMeta['Case Number'] ?? rawMeta.case_number ?? rawMeta.caseNo ?? '')
      ?.toString()
      .trim() || '';
  const versionNumber =
    (rawMeta['Version Number'] ?? rawMeta.version_number ?? rawMeta.versionNo ?? '')
      ?.toString()
      .trim() || '';

  const caseLabel =
    caseNumber && versionNumber
      ? `${caseNumber}.${versionNumber}`
      : caseNumber || '';

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">🔍 Causality Analysis: {caseLabel}</h1>
      </div>
      <AssessPanel
        pages={fileData.pages}
        meta={fileData.meta}
        annotations={fileData.annotations}
        folder={folder}
        fileName={file || ''}
        id={id || undefined}
      />
    </div>
  );
}
