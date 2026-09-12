// lib/projectUtils.ts
import * as XLSX from 'xlsx';

import type { ProjectEntry, MetaRecord, FileStats } from './interfaces';

export async function readMetaFile(projectName: string): Promise<ProjectEntry | null> {
  // We use history-files which now returns records directly from DB 
  // along with their counts and meta.
  const folderName = projectName;
  const statsRes = await fetch(`/api/history-files/${encodeURIComponent(folderName)}`);
  if (!statsRes.ok) return null;
  const statsData = await statsRes.json();
  
  // We need to fetch the 'meta' excel records if they exist for demographic info
  // though eventually we might want to fetch all columns from DB.
  const metaFile = `${projectName}_Meta.xlsx`;
  const metaRes = await fetch(`/api/meta?file=${encodeURIComponent(metaFile)}`);
  let metaRecords: any[] = [];
  if (metaRes.ok) {
    const metaJson = await metaRes.json();
    metaRecords = metaJson.records || [];
  }

  // Create a map of the meta records by Case-Version for easy lookup
  const metaMap = new Map<string, any>();
  metaRecords.forEach(r => {
    const c = r["Case Number"]?.toString().trim();
    const v = r["Version Number"]?.toString().trim();
    if (c && v) metaMap.set(`${c}-${v}`, r);
  });

  const records = statsData.files.map((f: any) => {
    const filename = f.filename; // e.g. "12345-1.json"
    const base = filename.replace(/\.json$/i, '');
    
    // Merge DB counts/meta with Excel demographic data
    const excelData = metaMap.get(base) || {};
    
    const meta = f.meta || {};
    let llmStatus = f.counts?.LLM ?? 0;
    if (!meta.llm_processed) {
      llmStatus = -2;
    } else if (meta.llm_processed === 'working') {
      llmStatus = -1;
    }

    return {
      ...excelData,
      annotate_filename: filename,
      folderName: folderName,
      meta: meta,
      counts: {
        ...f.counts,
        LLM: llmStatus,
        SME1: f.counts?.SME1 ?? 0,
        SME2: f.counts?.SME2 ?? 0,
        OTHER: f.counts?.Other ?? 0,
      }
    };
  });

  return { fileName: metaFile, folderName, records };
}

export async function readMetaFileExcel(projectName: string): Promise<ProjectEntry | null> {
  const file = `${projectName}_Meta.xlsx`;
  const res = await fetch(`/api/meta?file=${encodeURIComponent(file)}`);
  if (!res.ok) return null;

  const arrayBuffer = await res.arrayBuffer();
  const workbook = XLSX.read(arrayBuffer, { type: 'array' });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const records = XLSX.utils.sheet_to_json(worksheet);
  const folderName = projectName;

  // 🔁 Fetch file stats just for this project
  const statsRes = await fetch(`/api/history-files/${encodeURIComponent(folderName)}`);
  const statsData = await statsRes.json();
  const fileStatsMap = new Map<string, FileStats>(
    statsData.files.map((f: any) => [f.filename.replace(/\.json$/i, ''), f])
  );

  for (const record of records as MetaRecord[]) {
    const baseFilename = record.annotate_filename || record.case_id || 'unknown';
    if (baseFilename === 'unknown') continue;  
    record.annotate_filename = baseFilename + '.json';
      
    const stats: FileStats | undefined = fileStatsMap.get(baseFilename);
    
    record.folderName = folderName;
    record.meta = stats?.meta || {};
    const rawLLM = stats?.counts?.LLM ?? 0;
    let llmStatus = rawLLM;
    
    if (!record.meta.llm_processed) {
      llmStatus = -2; // never run
    } else if (record.meta.llm_processed === 'working') {
      llmStatus = -1;
    };
      
    record.counts = {
      LLM: llmStatus,
      SME1: stats?.counts?.SME1 ?? 0,
      SME2: stats?.counts?.SME2 ?? 0,
      OTHER: stats?.counts?.Other ?? 0,
    };
  }

  return { fileName: file, folderName, records };
}
