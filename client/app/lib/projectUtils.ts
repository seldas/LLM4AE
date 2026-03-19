// lib/projectUtils.ts
import * as XLSX from 'xlsx';

import type { ProjectEntry, MetaRecord, FileStats } from './interfaces';

export async function readMetaFile(projectName: string): Promise<ProjectEntry | null> {
  const file = `${projectName}_Meta.xlsx`;
  const res = await fetch(`/api/meta?file=${encodeURIComponent(file)}`);
  if (!res.ok) return null;

  // ✅ Expecting structured JSON { records: [...] }
  const json = await res.json();
  const records = json.records || [];
  const folderName = projectName;

  // 🔁 Fetch LLM/SME/ETHER file stats
  const statsRes = await fetch(`/api/history-files/${encodeURIComponent(folderName)}`);
  const statsData = await statsRes.json();
  const fileStatsMap = new Map<string, FileStats>(
    statsData.files.map((f: any) => [f.filename.replace(/\.json$/i, ''), f])
  );

  for (const record of records as MetaRecord[]) {
    // Handle annotate_filename fallback from Case Number + Version Number
    const caseNumber = record["Case Number"]?.toString().trim() || "";
    const versionNumber = record["Version Number"]?.toString().trim() || "";
    let baseFilename = record.annotate_filename?.replace(/\.json$/i, "") || "";

    if (!baseFilename && caseNumber && versionNumber) {
      baseFilename = `${caseNumber}-${versionNumber}`;
    }

    if (!baseFilename) continue;

    record.annotate_filename = `${baseFilename}.json`;
    record.folderName = folderName;

    const stats = fileStatsMap.get(baseFilename);
    record.meta = stats?.meta || {};

    const rawLLM = stats?.counts?.LLM ?? 0;
    let llmStatus = rawLLM;

    if (!record.meta.llm_processed) {
      llmStatus = -2; // never run
    } else if (record.meta.llm_processed === 'working') {
      llmStatus = -1;
    }

    record.counts = {
      LLM: llmStatus,
      SME1: stats?.counts?.SME1 ?? 0,
      SME2: stats?.counts?.SME2 ?? 0,
      OTHER: stats?.counts?.Other ?? 0,
    };
  }

  return { fileName: file, folderName, records };
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
