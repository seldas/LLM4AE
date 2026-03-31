'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  getPaginationRowModel,
  flexRender,
  SortingState,   
  CellContext,  
} from '@tanstack/react-table';
import type { ProjectEntry, MetaRecord } from './lib/interfaces';

// --- Icons (Inline SVGs for professional look) ---
const IconPlus = () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"/></svg>;
const IconRefresh = () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>;
const IconSearch = () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>;
const IconFolder = () => <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>;
const IconTrash = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 7l1-2h10l1 2m-10 0v10m4-10v10m-7-6h14m-4-4V4H9v3"/>
  </svg>
);

const NewProjectUploader = ({
  fetchProjectList,
  onClose
}: {
  fetchProjectList: () => Promise<void>;
  onClose: () => void;
}) => {
  const [newProjectName, setNewProjectName] = useState('');
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);

  const handleUploadProject = async () => {
    if (!newProjectName.trim() || !excelFile) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("file", excelFile);
    formData.append("projectName", newProjectName.trim());

    try {
      const res = await fetch("/annotator_api/api/create-project-from-excel", { method: "POST", body: formData });
      if (res.ok) {
        await fetchProjectList();
        onClose();
      } else {
        alert("System error: Unable to create project.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-8 border border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900 mb-6 border-b border-slate-100 pb-4">Initialize Dataset</h2>
        <div className="space-y-5">
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Project Identifier</label>
            <input
              type="text"
              placeholder="Internal ID (e.g. PH-2026-03)"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded text-sm focus:border-blue-500 outline-none transition-colors placeholder:text-slate-300"
            />
          </div>
          <div>
            <label className="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Source File (.xlsx)</label>
            <input
              type="file"
              accept=".xlsx"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  const file = e.target.files[0];
                  setExcelFile(file);
                  if (!newProjectName) setNewProjectName(file.name.replace(/\.xlsx$/i, ''));
                }
              }}
              className="hidden"
              id="fileInput"
            />
            <label
              htmlFor="fileInput"
              className="flex items-center justify-center gap-2 w-full px-4 py-4 bg-slate-50 border border-dashed border-slate-300 rounded text-slate-600 text-sm font-medium cursor-pointer hover:bg-slate-100 transition-colors"
            >
              {excelFile ? excelFile.name : 'Select structured data source'}
            </label>
          </div>
          <div className="flex gap-3 pt-4">
            <button onClick={onClose} className="flex-1 px-4 py-2 text-slate-600 text-sm font-semibold hover:text-slate-900 transition-colors">Cancel</button>
            <button
              disabled={loading || !excelFile}
              onClick={handleUploadProject}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded text-sm font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Initializing...' : 'Confirm'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default function HomePage() {
  const [user, setUser] = useState<any>(null);
  const router = useRouter();
  const [projectList, setProjectList] = useState<string[]>([]);
  const [selectedProjectName, setSelectedProjectName] = useState<string | null>(null);
  const [loadedProject, setLoadedProject] = useState<ProjectEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [showUploader, setShowUploader] = useState(false);
  const [deletingProject, setDeletingProject] = useState<string | null>(null);
  
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 15 });
  const [globalFilter, setGlobalFilter] = useState('');
  const [projectSearch, setProjectSearch] = useState('');
  const [playgroundText, setPlaygroundText] = useState('');

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
    } else {
      const u = JSON.parse(storedUser);
      setUser(u);
      fetchProjectList().then(list => {
        if (list.length > 0) handleProjectClick(list[0]);
      });
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('user');
    router.push('/login');
  };

  const fetchProjectList = async () => {
    const res = await fetch('/annotator_api/api/projects');
    const projects = await res.json();
    const sorted = projects.sort((a: string, b: string) => {
      if (a.toLowerCase() === 'playground') return -1;
      return a.localeCompare(b);
    });
    setProjectList(sorted);
    return sorted;
  };

  const handleProjectClick = async (projectName: string, limit = 15, offset = 0) => {
    setSelectedProjectName(projectName);
    setLoading(true);
    try {
      const res = await fetch(`/annotator_api/api/show_project/${encodeURIComponent(projectName)}?limit=${limit}&offset=${offset}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error);
      const records = data.records.map((r: any) => {
        const llmCount = r.counts?.LLM ?? 0;
        let llmStatus = 0;
        return { ...r, folderName: projectName, counts: { ...r.counts, LLM: llmStatus } };
      });
      setLoadedProject({ 
        folderName: projectName, 
        fileName: '', 
        records,
        totalCount: data.totalCount,
        limit: data.limit,
        offset: data.offset
      });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteProject = async (projectName: string) => {
    if (!window.confirm(`Delete project "${projectName}"? This keeps the underlying cases.`)) return;
    setDeletingProject(projectName);
    try {
      const res = await fetch('/annotator_api/api/delete-project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ projectName })
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.error || 'Failed to delete');
      }
      const updatedList = await fetchProjectList();
      if (selectedProjectName === projectName) {
        setLoadedProject(null);
        if (updatedList.length > 0) {
          handleProjectClick(updatedList[0]);
        } else {
          setSelectedProjectName(null);
        }
      }
    } catch (err: any) {
      console.error(err);
      alert(`Unable to remove project: ${err?.message || err}`);
    } finally {
      setDeletingProject(null);
    }
  };

  const handlePageChange = async (pageIndex: number) => {
    if (!selectedProjectName) return;
    const limit = pagination.pageSize;
    const offset = pageIndex * limit;
    await handleProjectClick(selectedProjectName, limit, offset);
    setPagination({ ...pagination, pageIndex });
  };

  const handlePageSizeChange = async (pageSize: number) => {
    if (!selectedProjectName) return;
    const offset = 0;
    await handleProjectClick(selectedProjectName, pageSize, offset);
    setPagination({ pageIndex: 0, pageSize });
  };

  const demographicFields = ["Case Number", "Version Number", "All Suspect Products", "MCN or CTU", "Latest FDA Received Date", "Country Derived", "Patient ID", "Age in Years", "Sex"];

  const columns = useMemo(() => [
    {
      id: 'actions',
      header: 'Workflow',
      cell: ({ row }: CellContext<MetaRecord, unknown>) => {
        const id = row.original.id;
        const folderName = row.original.folderName || selectedProjectName || 'Playground';

        const isAdj = user?.username === 'admin' || user?.role_name === 'Adjudicator';

        return (
          <div className="flex gap-3">
            {isAdj && (
              <button
                onClick={() => window.open(`/annotator/adjudicate?project=${encodeURIComponent(folderName)}&id=${encodeURIComponent(id)}`, '_blank')}
                className="text-emerald-600 hover:text-emerald-800 text-[11px] font-bold uppercase tracking-wider"
              >
                Adjudicate
              </button>
            )}
            <button
              onClick={() => window.open(`/annotator/annotate?project=${encodeURIComponent(folderName)}&id=${encodeURIComponent(id)}`, '_blank')}
              className="text-blue-600 hover:text-blue-800 text-[11px] font-bold uppercase tracking-wider"
            >
              Review
            </button>
          </div>
        );
      },
    },
    ...demographicFields.map(label => ({
      id: label.toLowerCase().replace(/\s+/g, '_'),
      header: label,
      accessorFn: (row: any) => row[label] ?? '',
      cell: ({ getValue }: any) => <span className="truncate max-w-[140px] block text-slate-500">{String(getValue() || '')}</span>,
    }))
  ], [selectedProjectName]);

  const table = useReactTable({
    data: loadedProject?.records ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: { sorting, pagination, globalFilter },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    onGlobalFilterChange: setGlobalFilter,
  });

  if (!user) return null;
  const isAdminUser = user.username === 'admin';

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden text-slate-900 antialiased">
      
      {/* --- Sidebar Navigation --- */}
      <aside className="w-64 bg-slate-900 flex flex-col z-20">
        <div className="p-6 border-b border-slate-800">
          <div className="flex items-center gap-2.5 mb-6">
            <div className="w-2 h-2 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
            <h1 className="text-sm font-bold text-white tracking-widest uppercase">LLM4AE</h1>
            <span className="text-[9px] font-black bg-blue-500/20 text-blue-400 px-1.5 py-0.5 rounded border border-blue-500/30 tracking-tighter">BETA</span>
          </div>
          <button 
            onClick={() => setShowUploader(true)}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-bold uppercase tracking-widest rounded transition-colors shadow-sm"
          >
            <IconPlus /> Import Dataset
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-4">
          <div className="px-6 mb-3 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">Available Repositories</div>
          <nav className="px-3 space-y-0.5">
            {projectList.filter(p => p.toLowerCase().includes(projectSearch.toLowerCase())).map(name => {
              const isActive = selectedProjectName === name;
              const isPlayground = name.toLowerCase() === 'playground';
              return (
                <div key={name} className="w-full flex items-center gap-2">
                  <button
                    onClick={() => handleProjectClick(name)}
                    className={`flex-1 flex items-center gap-3 px-4 py-2.5 rounded text-[12px] font-medium transition-all ${
                      isActive ? 'bg-slate-800 text-white' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                    }`}
                  >
                    <span className={isActive ? 'text-blue-400' : 'text-slate-600'}><IconFolder /></span>
                    <span className="truncate uppercase tracking-tight">{isPlayground ? 'Ad-hoc Review' : name}</span>
                  </button>
                  {isAdminUser && !isPlayground && (
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        handleDeleteProject(name);
                      }}
                      disabled={deletingProject === name}
                      className="flex-shrink-0 h-8 w-8 flex items-center justify-center text-red-500 border border-red-500/60 rounded bg-white hover:bg-red-500 hover:text-white transition-colors disabled:opacity-40 disabled:hover:bg-white"
                      title="Remove project"
                    >
                      {deletingProject === name ? (
                        <span className="w-3 h-3 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></span>
                      ) : (
                        <IconTrash />
                      )}
                      <span className="sr-only">Remove project</span>
                    </button>
                  )}
                </div>
              );
            })}
          </nav>
        </div>

        <div className="p-4 bg-slate-950 border-t border-slate-800">
          <div className="flex items-center gap-3 mb-4 px-2">
            <div className="w-7 h-7 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
              {user.username.charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-bold text-slate-200 truncate uppercase">{user.full_name || user.username}</p>
              <p className="text-[9px] text-slate-500 font-medium">System Operator</p>
            </div>
          </div>
          <div className="flex gap-2">
            {user.username === 'admin' && (
              <button onClick={() => router.push('/admin/users')} className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-400 text-[10px] font-bold uppercase rounded border border-slate-700">Manage</button>
            )}
            <button onClick={handleLogout} className="flex-1 py-1.5 bg-slate-800 hover:bg-red-900/30 hover:text-red-400 text-slate-400 text-[10px] font-bold uppercase rounded border border-slate-700 transition-colors">Exit</button>
          </div>
        </div>
      </aside>

      {/* --- Main Workspace --- */}
      <main className="flex-1 flex flex-col overflow-hidden">
        
        <header className="bg-white border-b border-slate-200 h-16 flex items-center justify-between px-8 shrink-0">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-widest flex items-center gap-3">
              {selectedProjectName ? selectedProjectName : 'Repository Overview'}
              {selectedProjectName?.toLowerCase() === 'playground' && <span className="text-[9px] font-bold text-blue-500 border border-blue-500/30 px-1.5 py-0.5 rounded leading-none">Sandbox</span>}
            </h2>
          </div>

          <div className="flex items-center gap-6">
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"><IconSearch /></span>
              <input
                type="text"
                placeholder="Search Inventory..."
                value={globalFilter ?? ''}
                onChange={(e) => setGlobalFilter(e.target.value)}
                className="pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-[12px] focus:bg-white focus:ring-1 focus:ring-blue-500 outline-none w-64 transition-all"
              />
            </div>
            <button onClick={() => handleProjectClick(selectedProjectName || '')} className="text-slate-400 hover:text-slate-600 transition-colors" title="Sync Database"><IconRefresh /></button>
          </div>
        </header>

        <div className="flex-1 flex flex-col min-h-0 p-8">
          {selectedProjectName?.toLowerCase() === 'playground' && (
            <div className="bg-white border border-slate-200 rounded shadow-sm mb-8 p-6">
              <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-[0.2em] mb-4">Ad-hoc Evidence Intake</h3>
              <textarea
                rows={3}
                placeholder="Paste unstructured clinical narrative for immediate review..."
                value={playgroundText}
                onChange={(e) => setPlaygroundText(e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded text-sm focus:bg-white focus:border-blue-500 outline-none transition-all font-mono leading-relaxed mb-4"
              />
              <button 
                onClick={async () => {
                  const finalBaseName = `manual_${Date.now()}`;
                  await fetch('/annotator_api/api/save', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fileName: finalBaseName, curr_folder: 'Playground', pages: [playgroundText.trim()], annotations: [], meta: {} }) });
                  setPlaygroundText('');
                  handleProjectClick('Playground');
                  window.open(`/annotate?project=Playground&file=${encodeURIComponent(finalBaseName + '.json')}`, '_blank');
                }}
                className="px-6 py-2 bg-slate-900 text-white text-[11px] font-bold uppercase tracking-widest rounded hover:bg-slate-800 transition-colors shadow-sm"
              >
                Launch Workflow
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-300">
              <div className="w-5 h-5 border-2 border-slate-200 border-t-blue-500 rounded-full animate-spin mb-3"></div>
              <p className="text-[10px] font-bold uppercase tracking-widest">Establishing Database Connection...</p>
            </div>
          ) : loadedProject ? (
            <div className="bg-white border border-slate-200 rounded shadow-sm overflow-hidden flex flex-col flex-1 min-h-0">
              
              <div className="px-6 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/50 shrink-0">
                <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Inventory Management</div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-slate-400 font-bold uppercase">Display:</span>
                    <select
                      value={pagination.pageSize}
                      onChange={e => handlePageSizeChange(Number(e.target.value))}
                      className="text-[10px] font-bold text-blue-600 bg-transparent outline-none cursor-pointer"
                    >
                      {[15, 30, 50, 100].map(s => <option key={s} value={s}>{s} rows</option>)}
                    </select>
                  </div>
                  <div className="flex items-center gap-1">
                    <button 
                      onClick={() => handlePageChange(pagination.pageIndex - 1)} 
                      disabled={pagination.pageIndex === 0} 
                      className="p-1 hover:text-blue-600 disabled:opacity-20 transition-colors"
                    >
                      ◀
                    </button>
                    <span className="text-[10px] font-bold text-slate-600 mx-1 uppercase tracking-tighter">
                      Page {pagination.pageIndex + 1} / {loadedProject?.totalCount ? Math.ceil(loadedProject.totalCount / pagination.pageSize) : 1}
                    </span>
                    <button 
                      onClick={() => handlePageChange(pagination.pageIndex + 1)} 
                      disabled={(pagination.pageIndex + 1) * pagination.pageSize >= (loadedProject?.totalCount || 0)} 
                      className="p-1 hover:text-blue-600 disabled:opacity-20 transition-colors"
                    >
                      ▶
                    </button>
                  </div>
                </div>
              </div>

              <div className="overflow-auto flex-1">
                <table className="w-full border-collapse">
                  <thead className="bg-white sticky top-0 z-10 shadow-[0_1px_0_rgba(0,0,0,0.05)]">
                    {table.getHeaderGroups().map(headerGroup => (
                      <tr key={headerGroup.id}>
                        {headerGroup.headers.map(header => (
                          <th 
                            key={header.id} 
                            onClick={header.column.getToggleSortingHandler()}
                            className="px-6 py-4 text-left text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100 cursor-pointer hover:text-slate-900 transition-colors"
                          >
                            <div className="flex items-center gap-1.5">
                              {flexRender(header.column.columnDef.header, header.getContext())}
                              <span className="text-blue-500 opacity-0 group-hover:opacity-100">
                                {{ asc: '↑', desc: '↓' }[header.column.getIsSorted() as string] ?? ''}
                              </span>
                            </div>
                          </th>
                        ))}
                      </tr>
                    ))}
                  </thead>
                  <tbody className="divide-y divide-slate-50">
                    {table.getRowModel().rows.map(row => (
                      <tr key={row.id} className="hover:bg-slate-50/80 transition-colors">
                        {row.getVisibleCells().map(cell => (
                          <td key={cell.id} className="px-6 py-3 text-[12px] font-medium text-slate-600 whitespace-nowrap">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center py-32">
              <div className="w-12 h-12 border border-slate-200 rounded flex items-center justify-center text-slate-300 mb-6"><IconFolder /></div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-widest mb-2">Selection Required</h2>
              <p className="text-[12px] text-slate-400 max-w-xs mx-auto">Please select a repository from the left panel to begin your evidence review workflow.</p>
            </div>
          )}
        </div>
      </main>

      {showUploader && (
        <NewProjectUploader 
          fetchProjectList={fetchProjectList}
          onClose={() => setShowUploader(false)}
        />
      )}
    </div>
  );
}
