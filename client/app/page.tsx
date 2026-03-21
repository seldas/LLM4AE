'use client';

import React, { useEffect, useState, useMemo, useRef, } from 'react';
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

const NewProjectUploader = ({
  newProjectName,
  setNewProjectName,
  excelFile,
  setExcelFile,
  fileInputRef,
  refreshHistoryFiles,
  fetchProjectList  
}: {
  newProjectName: string;
  setNewProjectName: (name: string) => void;
  excelFile: File | null;
  setExcelFile: (file: File | null) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  refreshHistoryFiles: () => Promise<any[]>;
  fetchProjectList: () => Promise<void>;  
}) => {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setExcelFile(e.target.files[0]);
    }
  };

  const handleUploadProject = async () => {
    if (!newProjectName.trim() || !excelFile) {
      alert("Please enter a project name and select an Excel file.");
      return;
    }

    const formData = new FormData();
    formData.append("file", excelFile);
    formData.append("projectName", newProjectName.trim());

    const res = await fetch("/api/create-project-from-excel", {
      method: "POST",
      body: formData,
    });
    
    if (res.ok) {
      alert("Project created successfully!");
      setNewProjectName('');
      setExcelFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      await refreshHistoryFiles();
      await fetchProjectList();  
    } else {
      alert("Failed to create project.");
    }
  };

  return (
    <div className="flex pl-4 items-center gap-1 bg-gray-100 hover:bg-gray-200 border-gray-900">
      <input
        type="text"
        placeholder="Project name"
        value={newProjectName}
        onChange={(e) => setNewProjectName(e.target.value)}
        className="px-2 py-0.5 border border-gray-300 rounded text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-[120px]"
      />
    
      <input
        type="file"
        accept=".xlsx"
        ref={fileInputRef}
        onChange={(e) => {
          if (e.target.files?.[0]) {
            const file = e.target.files[0];
            setExcelFile(file);
            const nameWithoutExtension = file.name.replace(/\.xlsx$/i, '');
            setNewProjectName(nameWithoutExtension);
          }
        }}
        className="hidden"
        id="newProjectExcel"
      />
    
      <label
        htmlFor="newProjectExcel"
        className="bg-blue-500 hover:bg-blue-600 text-white px-2 py-0.5 text-xs rounded cursor-pointer whitespace-nowrap"
      >
        Choose
      </label>
    
      <button
        onClick={handleUploadProject}
        className="bg-green-600 hover:bg-green-700 text-white px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap"
      >
        Create
      </button>
    </div>
  );
};

export default function HomePage() {
  const [user, setUser] = useState<any>(null);
  const router = useRouter();

  const [projectFiles, setProjectFiles] = useState<string[]>([]);
  const [loadedProject, setLoadedProject] = useState<ProjectEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [showUserInput, setShowUserInput] = useState(false);
  const [customFilename, setCustomFilename] = useState('');
  const [sorting, setSorting] = useState<SortingState>([])
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 });
  const [globalFilter, setGlobalFilter] = useState('');
  const [playgroundText, setPlaygroundText] = useState('');
  const [displayRows, setDisplayRows] = useState<any[]>([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);  
  const [deletionEnabled, setDeletionEnabled] = useState(false);
  
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
    } else {
      setUser(JSON.parse(storedUser));
      fetchProjectList();
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('user');
    router.push('/login');
  };

  const handleProjectClick = async (projectName: string) => {
      setLoading(true);
      try {
        const res = await fetch(`/api/show_project/${encodeURIComponent(projectName)}`);
        const data = await res.json();
        
        if (!res.ok) throw new Error(data.error || 'Failed to load project');

        const records = data.records.map((r: any) => {
          const llmCount = r.counts?.LLM ?? 0;
          const meta = r.meta || {};
          let llmStatus = llmCount;
          
          // Only use status codes if there are NO annotations
          if (llmCount === 0) {
            if (!meta.llm_processed) {
              llmStatus = -2; 
            } else if (meta.llm_processed === 'working') {
              llmStatus = -1;
            };
          }
          
          return {
            ...r,
            folderName: projectName,
            counts: { ...r.counts, LLM: llmStatus }
          };
        });

        setLoadedProject({
          folderName: projectName,
          fileName: '',
          records: records,
        });
        setDisplayRows(records);
        setShowUserInput(projectName === 'Playground');
      } catch (err: any) {
        alert(`❌ Error: ${err.message}`);
      } finally {
        setLoading(false);
      }
  };
    
  const handleDeleteProject = async (projectName: string) => {
      const confirmed = window.confirm(`Are you sure you want to delete project "${projectName}"? This action cannot be undone.`);
      if (!confirmed) return;
    
      try {
        const res = await fetch('/api/delete-project', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ projectName }),
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.error || 'Unknown error');
        await fetchProjectList();  
      } catch (err: any) {
        alert(`❌ Failed to delete project: ${err.message}`);
      }
  };

  const openAssessPopup = (folder: string, file: string) => {
      const url = `/assess?project=${encodeURIComponent(folder)}&file=${encodeURIComponent(file)}`;
      window.open(url, '_blank');
  };

  const openAnnotationPopup = (folder: string, file: string) => {
      const url = `/annotate?project=${encodeURIComponent(folder)}&file=${encodeURIComponent(file)}`;
      window.open(url, '_blank');
  };

  const handlePlaygroundSubmit = async (defaultFilename: string) => {
    if (!playgroundText.trim()) return;

    const text = playgroundText.trim();
    const finalBaseName = (customFilename.trim() || defaultFilename).replace(/\.json$/i, '');

    try {
      const response = await fetch('/api/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fileName: finalBaseName,
          curr_folder: 'Playground',
          pages: [text],
          annotations: [],
          meta: {},
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save playground entry');
      }

      const filename = `${finalBaseName}.json`;
      const url = `/annotate?project=Playground&file=${encodeURIComponent(filename)}`;
      window.open(url, '_blank', 'width=1280,height=800');
      setPlaygroundText('');
      setCustomFilename('');
      await refreshHistoryFiles();
    } catch (err: any) {
      alert(`❌ Failed to create playground file: ${err.message}`);
    }
  };
  
  const handleGenerateLLMAnnotation = async (row: any, table: any) => {
    row.counts.LLM = -1; // mark as "processing"
    setDisplayRows([...displayRows]); // trigger re-render
  
    const file = row.annotate_filename;
    const folder = loadedProject?.folderName;
    if (!file || !folder) return;
  
    try {
      // Start the LLM annotation process
      const response = await fetch('/api/llm-annotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file, folder }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Unknown error');
  
    } catch (err: any) {
      alert(`❌ Failed: ${err.message}`);
      throw err;
    }
  };
  

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        setExcelFile(e.target.files[0]);
      }
  };
    
  const handleDeletePlaygroundFile = async (filename: string) => {
      const confirmed = window.confirm(`Are you sure you want to delete ${filename}?`);
      if (!confirmed) return;
    
      try {
        const path = `Playground___${filename}`;
        const response = await fetch(`/api/history/${path}`, {
          method: 'DELETE',
        });
    
        const result = await response.json();
    
        if (!response.ok) {
          throw new Error(result.error || 'Unknown error');
        }
    
        await refreshHistoryFiles();
      } catch (err: any) {
        console.error("Delete failed:", err);
        alert(`❌ Failed to delete file: ${err.message}`);
      }
  };
    
  const refreshHistoryFiles = async (): Promise<any[]> => {
      if (!loadedProject?.folderName) return [];
      
      setLoading(true);
      try {
        const res = await fetch(`/api/show_project/${encodeURIComponent(loadedProject.folderName)}`);
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to refresh');

        const records = data.records.map((r: any) => {
          const llmCount = r.counts?.LLM ?? 0;
          const meta = r.meta || {};
          let llmStatus = llmCount;
          
          if (llmCount === 0) {
            if (!meta.llm_processed) {
              llmStatus = -2; 
            } else if (meta.llm_processed === 'working') {
              llmStatus = -1;
            };
          }
          
          return {
            ...r,
            folderName: loadedProject.folderName,
            counts: { ...r.counts, LLM: llmStatus }
          };
        });

        setLoadedProject({
          folderName: loadedProject.folderName,
          fileName: '',
          records: records,
        });
        setDisplayRows(records);
        return records;
      } catch (err: any) {
        console.error("Refresh failed:", err);
        return [];
      } finally {
        setLoading(false);
      }
  };

  const fetchProjectList = async () => {
      const res = await fetch('/api/projects');
      const projects = await res.json();
      const otherProjects = projects.filter((p: string) => p.toLowerCase() !== 'playground');
      setProjectFiles(['Playground', ...otherProjects]);
  };
    
  // Demographic fields to show in the table
  const demographicFields = [
    "Case Number", "Version Number", "All Suspect Products", "MCN or CTU", "Latest FDA Received Date",
    "Country Derived", "Patient ID", "Age in Years", "DOB", "Sex",
    "Weight In kg", "Health Professional",
  ];

  const demographicColumns = demographicFields.map((label) => {
    const id = label.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
  
    return {
      id,
      header: label,
      accessorFn: (row: any) => row[label] ?? '',
      cell: ({ getValue }: any) => (
        <span className="truncate max-w-[200px] block">{String(getValue() || '')}</span>
      ),
    };
  });
  
  const columns = useMemo(() => [
    {
      id: 'actions',
      header: 'Action',
      cell: ({ row }: CellContext<MetaRecord, unknown>) => {
        const fileName = row.original.annotate_filename || '';
        const folderName = row.original.folderName || loadedProject?.folderName || 'Playground'; // fallback
    
        return (
          <button
            onClick={() =>
              openAnnotationPopup(folderName, fileName)
            }
            className="bg-sky-600 hover:bg-sky-700 text-white text-xs font-medium px-4 py-1.5 rounded-full shadow-sm transition-all duration-200"
          >
            ✏️Annotate
          </button>
        );
      },
    },
    {
      id: 'human_count',
      header: '👤 Human',
      accessorFn: (row: any) => (row.counts?.SME1 || 0) + (row.counts?.SME2 || 0) + (row.counts?.Other || 0),
      cell: ({ getValue }: any) => (
        <span className="font-bold text-indigo-600 px-2">{getValue()}</span>
      ),
    },
    {
      id: 'ai_count',
      header: '🤖 AI',
      accessorFn: (row: any) => {
        const count = row.counts?.LLM || 0;
        return count < 0 ? 0 : count; // handle status codes
      },
      cell: ({ getValue }: any) => (
        <span className="font-bold text-orange-600 px-2">{getValue()}</span>
      ),
    },
    ...(loadedProject?.folderName === 'Playground' ? [  
      { accessorKey: 'annotate_filename', header: 'File' },
      {
      id: 'actions-playground',
      header: '🗑️ Delete',
      cell: ({ row }: CellContext<MetaRecord, unknown>) => {
        const file = row.original.annotate_filename || '';
        if (loadedProject?.folderName !== 'Playground') return null;
        return (
          <button
            onClick={() => handleDeletePlaygroundFile(file)}
            className="bg-red-100 hover:bg-red-200 text-red-800 font-semibold text-xs px-2 py-1 rounded shadow"
          >
            🗑️
          </button>
        );
      }
    }] : demographicColumns),
    //
  ], [loadedProject]);

  const table = useReactTable({
    data: loadedProject?.folderName === 'Playground' ? displayRows : loadedProject?.records ?? [],
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    state: {
      sorting,
      pagination,
      globalFilter,
    },
    onSortingChange: setSorting,
    onPaginationChange: setPagination,
    onGlobalFilterChange: setGlobalFilter,
  });
    
  if (!user) return null;

  const randomString = Math.random().toString(36).substring(2, 8); // generates 6-char string
  const defaultFilename = `playground_${randomString}`;
  
  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">📁 <a href="">Annotation Projects</a></h1>
        <div className="flex items-center gap-4">
          {user.username === 'admin' && (
            <button 
              onClick={() => router.push('/admin/users')}
              className="text-xs font-bold text-blue-600 hover:text-blue-800 border border-blue-200 px-3 py-1 rounded-full bg-blue-50 transition-all"
            >
              ⚙️ User Management
            </button>
          )}
          <span className="text-sm font-medium text-gray-700">👤 {user.full_name || user.username}</span>
          <button 
            onClick={handleLogout}
            className="text-xs font-semibold text-red-600 hover:text-red-800 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>
      
      <button
          disabled
          onClick={() => setDeletionEnabled(!deletionEnabled)}
          // hidden // very dangerous to show, only for dev user.
          className="mb-4 px-3 py-1 text-sm rounded border border-gray-400 bg-white hover:bg-gray-100"
      >
          {deletionEnabled ? '🛑 Deletion Enabled' : '🔒 Enable Delete Mode'}
      </button>  
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
          {projectFiles.map((fileName) => (
              <div
                key={fileName}
                onClick={() => handleProjectClick(fileName)} // ✅ Clickable wrapper
                className={`relative p-4 border rounded-lg shadow-sm transition-all cursor-pointer ${
                  fileName === 'Playground'
                    ? 'bg-amber-100 hover:bg-amber-200 border-amber-300 text-amber-900'
                    : 'bg-sky-100 hover:bg-sky-200 border-sky-300 text-sky-900'
                }`}
              >
                <h3 className="text-lg font-semibold">{fileName}</h3>
            
                {fileName !== 'Playground' && (
                  <button
                      onClick={(e) => {
                        e.stopPropagation(); // 🛑 Prevents card click from triggering
                        handleDeleteProject(fileName);
                      }}
                      disabled={!deletionEnabled}
                      className={`mt-2 text-xs px-3 py-1 rounded ${
                        deletionEnabled
                          ? 'bg-red-600 text-white hover:bg-red-700'
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                  >
                      {deletionEnabled ? 'Delete' : 'Delete Disabled'}
                  </button>

                )}
              </div>
          ))}


          <NewProjectUploader
            newProjectName={newProjectName}
            setNewProjectName={setNewProjectName}
            excelFile={excelFile}
            setExcelFile={setExcelFile}
            fileInputRef={fileInputRef}
            refreshHistoryFiles={refreshHistoryFiles}
            fetchProjectList={fetchProjectList}
          />
      </div>

      {showUserInput && (
        <div className="p-6 bg-white border border-gray-200 rounded-lg shadow-sm mb-8 space-y-4">
          <h2 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
            🧪 Playground Input
          </h2>

          {/* Filename Input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Filename <span className="text-gray-400 italic">(optional)</span>
            </label>
            <input
              type="text"
              placeholder={`[by default] ${defaultFilename}`}
              value={customFilename}
              onChange={(e) => setCustomFilename(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md text-sm font-mono shadow-sm focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            />
          </div>

          {/* Textarea */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Text to Annotate
            </label>
            <textarea
              value={playgroundText}
              onChange={(e) => setPlaygroundText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handlePlaygroundSubmit(defaultFilename);
                }
              }}
              rows={6}
              placeholder="Paste or type any text here to begin annotation..."
              className="w-full p-3 border border-gray-300 rounded-md text-sm font-mono shadow-sm focus:ring-2 focus:ring-indigo-400 focus:outline-none"
            />
          </div>

          {/* Button */}
          <div>
            <button
              onClick={() => handlePlaygroundSubmit(defaultFilename)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-md shadow"
            >
              Annotate
            </button>
          </div>
        </div>
      )}



      {loading && <p className="text-gray-600 italic">Loading project...</p>}

      {loadedProject && (
        <div className="overflow-x-auto border rounded-lg shadow bg-white">
          <div className="p-4 border-b flex justify-between items-center">
            <h1 className="text-2xl font-semibold text-gray-800">
              {loadedProject.folderName}
            </h1>
            <button 
              onClick={async () => {
                const updatedRecords = await refreshHistoryFiles();
                setDisplayRows(updatedRecords);
              }}
              className="text-gray-600 hover:text-gray-900 transition-colors duration-200"
              title="Reload project"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
          <div className="flex justify-between items-center p-2 flex-wrap gap-3">            
            <label className="text-sm font-medium">Rows per page:
              <select
                className="ml-2 px-2 py-1 border rounded"
                value={pagination.pageSize}
                onChange={(e) => setPagination({ ...pagination, pageSize: Number(e.target.value) })}
              >
                {[10, 25, 50].map(size => (
                  <option key={size} value={size}>{size}</option>
                ))}
              </select>
            </label>

            <input
              type="text"
              placeholder="Search..."
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="border px-3 py-1 rounded text-sm w-[200px]"
            />

            <div className="flex items-center gap-2">
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              >
                Prev
              </button>

              <span className="text-sm">
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
              </span>

              <input
                type="number"
                min={1}
                max={table.getPageCount()}
                placeholder="To ..."
                className="w-[80px] text-sm px-2 py-1 border rounded"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const input = parseInt((e.target as HTMLInputElement).value);
                    if (!isNaN(input) && input >= 1 && input <= table.getPageCount()) {
                      table.setPageIndex(input - 1);
                    }
                  }
                }}
              />

              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>

          <table className="min-w-full table-auto text-sm">
            <thead className="bg-gray-100">
              {table.getHeaderGroups().map(headerGroup => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map(header => (
                    <th key={header.id} className="px-3 py-2 text-left font-semibold whitespace-nowrap cursor-pointer hover:bg-gray-200" onClick={header.column.getToggleSortingHandler()}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{ asc: ' 🔼', desc: ' 🔽' }[header.column.getIsSorted() as string] ?? ''}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="hover:bg-blue-50">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="px-3 py-1 max-w-[160px] truncate whitespace-nowrap overflow-hidden text-ellipsis border-t">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
