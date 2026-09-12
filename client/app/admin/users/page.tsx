'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';

interface User {
  id: number;
  username: string;
  full_name: string;
  role_id: number;
  role_name: string;
  migration_key: string | null;
  annotation_count?: number;
}

interface Role {
  id: number;
  name: string;
}

interface Stats {
  project_count: number;
  case_count: number;
  bert_processed_count: number;
  llm_processed_count?: number;
  user_count: number;
  label_distribution: Record<string, { Human: number; LLM: number; BERT: number; Total: number; }>;
  user_distribution: Record<string, number>;
}

type SortKey = 'username' | 'role_name' | 'annotation_count';
type SortOrder = 'asc' | 'desc';

type LabelCounts = Stats['label_distribution'][string];

const LABEL_CANONICAL_OVERRIDES: Record<string, string> = {
  'CAUSE OF DEATH': 'Cause of Death',
  'CAUSE_OF_DEATH': 'Cause of Death',
  'COD': 'Cause of Death',
  'RULE OUT': 'Rule Out',
  'RULE_OUT': 'Rule Out',
  'R/O': 'Rule Out',
  'RO': 'Rule Out',
  'MEDICAL HISTORY': 'Medical History',
  'MEDICAL_HISTORY': 'Medical History',
  'HISTORY': 'Medical History',
  'FAMILY HISTORY': 'Family History',
  'FAMILY_HISTORY': 'Family History',
  'FHX': 'Family History'
};

const normalizeLabelName = (label: string | undefined): string => {
  if (!label) return 'Unknown';
  const trimmed = label.trim();
  const upper = trimmed.toUpperCase();
  return LABEL_CANONICAL_OVERRIDES[upper] ?? trimmed;
};

const LABEL_CATEGORY_ORDER = [
  'Drug & Therapy',
  'Medical Events',
  'Temporal',
  'Demographic',
  'History & Context',
  'Other'
];

const LABEL_CATEGORY_DEFINITIONS: { name: string; matcher: RegExp }[] = [
  { name: 'History & Context', matcher: /(MEDICAL HISTORY|FAMILY HISTORY|HISTORY)/ },
  { name: 'Demographic', matcher: /(AGE|SEX)/ },
  { name: 'Drug & Therapy', matcher: /(DRUG|DOSE|VACCINE)/ },
  { name: 'Medical Events', matcher: /(AE|MAE|SYMPTOM|TREATMENT|DIAGNOSTIC|STATUS|DISPOSITION|RULE OUT|RULE_OUT|R\/O|RO|COD|CAUSE OF DEATH|CAUSE|IND|OUTCOME)/ },
  { name: 'Temporal', matcher: /(TEMPORAL|DATE|TIME|LATENCY|DURATION|RELATIVE)/ }
];

const categorizeLabel = (label: string): string => {
  const upper = label.toUpperCase();
  for (const def of LABEL_CATEGORY_DEFINITIONS) {
    if (def.matcher.test(upper)) {
      return def.name;
    }
  }
  return 'Other';
};

interface AggregatedLabel {
  label: string;
  counts: LabelCounts;
  category: string;
}

const aggregateLabelDistribution = (distribution: Stats['label_distribution']): AggregatedLabel[] => {
  const map: Record<string, AggregatedLabel> = {};
  Object.entries(distribution).forEach(([label, counts]) => {
    const canonical = normalizeLabelName(label);
    const category = categorizeLabel(canonical);
    if (!map[canonical]) {
      map[canonical] = {
        label: canonical,
        counts: { Human: 0, LLM: 0, BERT: 0, Total: 0 },
        category
      };
    }
    map[canonical].counts.Human += counts?.Human ?? 0;
    map[canonical].counts.LLM += counts?.LLM ?? 0;
    map[canonical].counts.BERT += counts?.BERT ?? 0;
    map[canonical].counts.Total += counts?.Total ?? 0;
  });
  return Object.values(map).sort((a, b) => {
    const idxA = LABEL_CATEGORY_ORDER.indexOf(a.category);
    const idxB = LABEL_CATEGORY_ORDER.indexOf(b.category);
    if (idxA !== idxB) return idxA - idxB;
    return (b.counts.Total ?? 0) - (a.counts.Total ?? 0);
  });
};

export default function AdminDashboardPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [adminUser, setAdminUser] = useState<any>(null);
  const [isProcessingBert, setIsProcessingBert] = useState(false);
  const [isProcessingLlm, setIsProcessingLlm] = useState(false);
  const [categoryExpanded, setCategoryExpanded] = useState<Record<string, boolean>>(() =>
    LABEL_CATEGORY_ORDER.reduce((acc, name) => ({ ...acc, [name]: false }), {})
  );
  const router = useRouter();

  // Table State
  const [sortConfig, setSortConfig] = useState<{ key: SortKey; order: SortOrder }>({ key: 'annotation_count', order: 'desc' });
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    full_name: '',
    role_id: 2, 
    migration_key: ''
  });

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (!storedUser) {
      router.push('/login');
      return;
    }
    const user = JSON.parse(storedUser);
    if (user.username !== 'admin') {
      router.push('/');
      return;
    }
    setAdminUser(user);
    const init = async () => {
        await Promise.all([fetchData(), fetchStats()]);
        setLoading(false);
    }
    init();
  }, [router]);

  const fetchData = async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([
        fetch('/api/users'),
        fetch('/api/roles')
      ]);
      const usersData = await usersRes.json();
      const rolesData = await rolesRes.json();
      setUsers(usersData);
      setRoles(rolesData);
    } catch (err) {
      setError('Failed to fetch user data');
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/admin/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to fetch stats', err);
    }
  };

  const handleTriggerBert = async () => {
    if (!confirm('Trigger background BERT annotation?')) return;
    setIsProcessingBert(true);
    try {
      const res = await fetch('/api/admin/bert-annotate', { method: 'POST' });
      if (res.ok) alert('BERT annotation started in background.');
      else alert('Failed to start BERT annotation.');
    } catch (err) {
      alert('Error triggering BERT annotation.');
    } finally {
      setIsProcessingBert(false);
    }
  };

  const handleTriggerLlm = async () => {
    if (!confirm('Trigger background LLM annotation (P2_TAG mode) for unannotated cases?')) return;
    setIsProcessingLlm(true);
    try {
      const res = await fetch('/api/admin/llm-annotate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: 'tag', schema: 'faers', note: 'Llama4' })
      });
      if (res.ok) alert('LLM annotation started in background.');
      else alert('Failed to start LLM annotation.');
    } catch (err) {
      alert('Error triggering LLM annotation.');
    } finally {
      setIsProcessingLlm(false);
    }
  };

  const handleSubmitUser = async (e: React.FormEvent) => {
    e.preventDefault();
    const url = editingUser ? `/api/users/${editingUser.id}` : '/api/users';
    const method = editingUser ? 'PUT' : 'POST';
    
    try {
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        setShowModal(false);
        setEditingUser(null);
        setFormData({ username: '', password: '', full_name: '', role_id: 2, migration_key: '' });
        fetchData();
        fetchStats();
      } else {
        const d = await res.json();
        alert(d.error || 'Operation failed');
      }
    } catch (err) {
      alert('Network error');
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Delete this user?')) return;
    try {
      const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchData();
        fetchStats();
      }
    } catch (err) {
      alert('Error');
    }
  };

  const openAddModal = () => {
    setEditingUser(null);
    setFormData({ username: '', password: '', full_name: '', role_id: 2, migration_key: '' });
    setShowModal(true);
  };

  const openEditModal = (user: User) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      password: '',
      full_name: user.full_name || '',
      role_id: user.role_id,
      migration_key: user.migration_key || ''
    });
    setShowModal(true);
  };

  const handleSort = (key: SortKey) => {
    setSortConfig(prev => ({
      key,
      order: prev.key === key && prev.order === 'desc' ? 'asc' : 'desc'
    }));
  };

  const toggleCategory = (name: string) => {
    setCategoryExpanded(prev => ({ ...prev, [name]: !prev[name] }));
  };

  // Processed Users List
  const processedUsers = useMemo(() => {
    const enriched = users.map(u => ({
      ...u,
      annotation_count: stats?.user_distribution[u.username] || 0
    }));

    return enriched.sort((a, b) => {
      const aVal = a[sortConfig.key] ?? 0;
      const bVal = b[sortConfig.key] ?? 0;
      if (aVal < bVal) return sortConfig.order === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.order === 'asc' ? 1 : -1;
      return 0;
    });
  }, [users, stats, sortConfig]);

  // Pagination
  const totalPages = Math.ceil(processedUsers.length / itemsPerPage);
  const paginatedUsers = processedUsers.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const maxUserAnnotations = Math.max(...processedUsers.map(u => u.annotation_count || 0), 1);
  const sortedLabels = stats ? aggregateLabelDistribution(stats.label_distribution) : [];
  const maxLabelCount = sortedLabels.reduce((prev, curr) => Math.max(prev, curr.counts.Total ?? 0), 1);
  const groupedLabelSections = LABEL_CATEGORY_ORDER.map(name => {
    const items = sortedLabels.filter(entry => entry.category === name);
    const total = items.reduce((sum, entry) => sum + (entry.counts.Total ?? 0), 0);
    return { name, items, total };
  }).filter(section => section.items.length > 0);

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-slate-50">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900"></div>
    </div>
  );

  return (
    <div className="p-8 max-w-[1600px] mx-auto bg-slate-50 min-h-screen font-sans selection:bg-blue-100">
      
      {/* Header & Quick Actions */}
      <div className="flex justify-between items-start mb-8">
        <div>
          <h1 className="text-3xl font-black text-slate-900 tracking-tight uppercase">Admin Dashboard</h1>
          <p className="text-slate-500 font-bold text-[10px] uppercase tracking-widest mt-1">System Monitoring & Database Control</p>
        </div>
        
        <div className="flex gap-2 items-center">
          <button 
            onClick={handleTriggerLlm}
            disabled={isProcessingLlm}
            className="px-3 py-1.5 bg-purple-600 text-white rounded-lg font-black text-[8px] uppercase tracking-widest hover:bg-purple-700 disabled:bg-purple-300 transition-all shadow-sm flex items-center gap-1.5"
          >
            <svg className={`w-2.5 h-2.5 ${isProcessingLlm ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            {isProcessingLlm ? 'Running...' : 'LLM Annotate'}
          </button>
          <button 
            onClick={handleTriggerBert}
            disabled={isProcessingBert}
            className="px-3 py-1.5 bg-slate-900 text-white rounded-lg font-black text-[8px] uppercase tracking-widest hover:bg-slate-800 disabled:bg-slate-300 transition-all shadow-sm"
          >
            {isProcessingBert ? 'Running...' : 'BERT Annotate'}
          </button>
          <div className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500 text-white rounded-lg text-[8px] font-black uppercase tracking-widest">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M5 12l5 5L20 7" />
            </svg>
            DB Ready
          </div>
          <button 
            onClick={() => { fetchStats(); fetchData(); }}
            className="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 rounded-lg font-black text-[8px] uppercase tracking-widest hover:bg-slate-50 transition-all shadow-sm"
          >
            Refresh
          </button>
          <div className="w-px h-6 bg-slate-200 mx-1"></div>
          <button 
            onClick={() => router.push('/')}
            className="px-3 py-1.5 bg-white border border-slate-200 text-slate-600 rounded-lg font-black text-[8px] uppercase tracking-widest hover:text-blue-600 transition-all shadow-sm"
          >
            Exit
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-6">
        
        {/* Main Section */}
        <div className="col-span-12 lg:col-span-9 space-y-6">
          
          {/* Top Row Cards */}
          <div className="grid grid-cols-5 gap-4">
            {[
              { label: 'Projects', val: stats?.project_count, color: 'text-slate-900' },
              { label: 'Total Cases', val: stats?.case_count, color: 'text-slate-900' },
              { label: 'LLM Processed', val: stats?.llm_processed_count, color: 'text-purple-600' },
              { label: 'BERT Processed', val: stats?.bert_processed_count, color: 'text-emerald-600' },
              { label: 'System Users', val: stats?.user_count, color: 'text-blue-600' }
            ].map(card => (
              <div key={card.label} className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200/60">
                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-1 truncate">{card.label}</p>
                <p className={`text-xl font-black ${card.color}`}>{card.val || 0}</p>
              </div>
            ))}
          </div>

          {/* Combined Personnel List & Contribution */}
          <div className="bg-white rounded-[2rem] shadow-sm border border-slate-200/60 overflow-hidden">
            <div className="px-8 py-5 border-b border-slate-50 flex justify-between items-center">
              <h3 className="text-xs font-black text-slate-900 uppercase tracking-widest">Personnel Registry</h3>
              <button 
                onClick={openAddModal}
                className="text-[9px] font-black text-blue-600 uppercase tracking-widest hover:text-blue-700 transition-colors"
              >
                + New Profile
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-slate-50/30">
                    <th onClick={() => handleSort('username')} className="px-8 py-3 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:text-slate-600 transition-colors">
                      Username {sortConfig.key === 'username' && (sortConfig.order === 'asc' ? '↑' : '↓')}
                    </th>
                    <th onClick={() => handleSort('role_name')} className="px-8 py-3 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:text-slate-600 transition-colors">
                      Role {sortConfig.key === 'role_name' && (sortConfig.order === 'asc' ? '↑' : '↓')}
                    </th>
                    <th onClick={() => handleSort('annotation_count')} className="px-8 py-3 text-left text-[9px] font-black text-slate-400 uppercase tracking-widest cursor-pointer hover:text-slate-600 transition-colors">
                      Contributions {sortConfig.key === 'annotation_count' && (sortConfig.order === 'asc' ? '↑' : '↓')}
                    </th>
                    <th className="px-8 py-3 text-right text-[9px] font-black text-slate-400 uppercase tracking-widest">Command</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {paginatedUsers.map((u) => (
                    <tr key={u.id} className="hover:bg-slate-50/50 transition-colors group">
                      <td className="px-8 py-4">
                        <span className="text-xs font-bold text-slate-900">{u.username}</span>
                        <p className="text-[9px] text-slate-400 font-medium">{u.full_name}</p>
                      </td>
                      <td className="px-8 py-4">
                        <span className={`px-2 py-0.5 text-[8px] font-black uppercase rounded-full border
                          ${u.role_name === 'Admin' ? 'bg-purple-50 text-purple-600 border-purple-100' : 
                            u.role_name === 'AI' ? 'bg-orange-50 text-orange-600 border-orange-100' : 
                            'bg-blue-50 text-blue-600 border-blue-100'}`}>
                          {u.role_name}
                        </span>
                      </td>
                      <td className="px-8 py-4 min-w-[200px]">
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden border border-slate-200/50">
                            <div 
                              className="h-full bg-slate-900 rounded-full transition-all duration-1000 ease-out group-hover:bg-blue-600" 
                              style={{ width: `${((u.annotation_count || 0) / maxUserAnnotations) * 100}%` }}
                            />
                          </div>
                          <span className="text-[10px] font-black text-slate-900 w-10">{(u.annotation_count || 0).toLocaleString()}</span>
                        </div>
                      </td>
                      <td className="px-8 py-4 text-right">
                        <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button onClick={() => openEditModal(u)} className="p-1.5 text-slate-400 hover:text-slate-900"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg></button>
                          {u.username !== 'admin' && (
                            <button onClick={() => handleDelete(u.id)} className="p-1.5 text-slate-400 hover:text-red-600"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Pagination Controls */}
            <div className="px-8 py-4 bg-slate-50/30 border-t border-slate-50 flex items-center justify-between">
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Showing {(currentPage-1)*itemsPerPage + 1} - {Math.min(currentPage*itemsPerPage, processedUsers.length)} of {processedUsers.length} Users
              </p>
              <div className="flex gap-1">
                <button 
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(p => p - 1)}
                  className="px-3 py-1 bg-white border border-slate-200 rounded text-[9px] font-black uppercase hover:bg-slate-50 disabled:opacity-50 transition-all"
                >
                  Prev
                </button>
                {Array.from({ length: totalPages }).map((_, i) => (
                  <button 
                    key={i}
                    onClick={() => setCurrentPage(i + 1)}
                    className={`px-3 py-1 rounded text-[9px] font-black transition-all ${currentPage === i + 1 ? 'bg-slate-900 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'}`}
                  >
                    {i + 1}
                  </button>
                ))}
                <button 
                  disabled={currentPage === totalPages}
                  onClick={() => setCurrentPage(p => p + 1)}
                  className="px-3 py-1 bg-white border border-slate-200 rounded text-[9px] font-black uppercase hover:bg-slate-50 disabled:opacity-50 transition-all"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Column */}
        <div className="col-span-12 lg:col-span-3 space-y-6 flex flex-col justify-start h-full">
          
          {/* Annotation Inventory - Sorted Bar Chart */}
          <div className="w-full max-w-[360px] h-full bg-white rounded-[2rem] shadow-sm border border-slate-200/60 overflow-hidden flex flex-col">
            <div className="px-8 py-5 border-b border-slate-50 flex items-center justify-center">
              <h3 className="text-xs font-black text-slate-900 uppercase tracking-widest">Inventory</h3>
            </div>
            <div className="p-6 space-y-6 flex-1 overflow-y-auto pr-2 sm:pr-0">
              {groupedLabelSections.length > 0 ? (
                groupedLabelSections.map(section => {
                  const isExpanded = categoryExpanded[section.name] ?? true;
                  return (
                    <div key={section.name} className="space-y-3">
                      <div className="flex flex-col gap-1 text-[10px] font-black uppercase tracking-[0.3em] text-slate-500 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex flex-col gap-1 leading-tight">
                          <span>{section.name}</span>
                          <span className="text-[9px] font-bold text-slate-400">{section.items.length} sub-categories</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-slate-700">{section.total.toLocaleString()} total</span>
                          <button
                            onClick={() => toggleCategory(section.name)}
                            className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-400 hover:text-slate-900 transition-colors"
                            aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${section.name}`}
                          >
                            {isExpanded ? (
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 12 12">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2 6h8" />
                              </svg>
                            ) : (
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 12 12">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 2v8m4-4H2" />
                              </svg>
                            )}
                          </button>
                        </div>
                      </div>
                      {isExpanded ? (
                        <div className="space-y-3">
                          {section.items.map(({ label, counts }) => {
                            const total = counts?.Total ?? 0;
                            const humanCount = counts?.Human ?? 0;
                            const llmCount = counts?.LLM ?? 0;
                            const bertCount = counts?.BERT ?? 0;
                            const barWidthPercent = (total / maxLabelCount) * 100;
                            const humanPct = total ? (humanCount / total) * 100 : 0;
                            const llmPct = total ? (llmCount / total) * 100 : 0;
                            const bertPct = total ? (bertCount / total) * 100 : 0;
                            return (
                              <div key={label} className="bg-slate-50/80 rounded-2xl p-4 border border-slate-100 shadow-[0_12px_24px_-14px_rgba(15,23,42,0.8)]">
                                <div className="flex flex-col gap-3">
                                  <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                                    <span className="text-[11px] font-semibold text-slate-900 uppercase tracking-[0.25em]">{label}</span>
                                    <span className="text-[11px] font-black text-slate-700">{total.toLocaleString()}</span>
                                  </div>
                                  <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                                    <div
                                      className="h-full flex rounded-full transition-all duration-700 ease-out"
                                      style={{ width: `${barWidthPercent}%` }}
                                    >
                                      {humanCount > 0 && (
                                        <div
                                          className="h-full bg-slate-700"
                                          style={{ width: `${humanPct}%` }}
                                        />
                                      )}
                                      {llmCount > 0 && (
                                        <div
                                          className="h-full bg-blue-500"
                                          style={{ width: `${llmPct}%` }}
                                        />
                                      )}
                                      {bertCount > 0 && (
                                        <div
                                          className="h-full bg-amber-400"
                                          style={{ width: `${bertPct}%` }}
                                        />
                                      )}
                                    </div>
                                  </div>
                                  <div className="flex flex-col gap-1 text-[9px] font-black uppercase tracking-[0.3em] text-slate-500 sm:flex-row sm:items-center sm:justify-between">
                                    <span className="text-slate-900">{humanCount.toLocaleString()} Human</span>
                                    <span className="text-blue-500">{llmCount.toLocaleString()} LLM</span>
                                    <span className="text-amber-500">{bertCount.toLocaleString()} BERT</span>
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="text-[9px] uppercase tracking-[0.3em] text-slate-400">
                          {section.items.length} sub-categories hidden • click the icon to expand
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-slate-600 text-xs font-bold uppercase italic">No data</div>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* User Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-[2.5rem] shadow-2xl max-w-lg w-full p-10 border border-slate-200">
            <div className="flex justify-between items-center mb-10">
              <h2 className="text-xl font-black uppercase tracking-wider text-slate-900">
                {editingUser ? `Adjust Profile: ${editingUser.username}` : 'New Access Profile'}
              </h2>
              <button onClick={() => setShowModal(false)} className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-slate-100 text-slate-400 transition-colors">✕</button>
            </div>
            
            <form onSubmit={handleSubmitUser} className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-1">Username</label>
                  <input required type="text" value={formData.username} onChange={e => setFormData({...formData, username: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all" />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-1">Password {editingUser && '(opt)'}</label>
                  <input required={!editingUser} type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all" />
                </div>
              </div>
              
              <div className="space-y-1.5">
                <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
                <input type="text" value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all" />
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-1.5">
                  <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-1">Role Designation</label>
                  <select value={formData.role_id} onChange={e => setFormData({...formData, role_id: parseInt(e.target.value)})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all appearance-none">
                    {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-1">Mapping Key</label>
                  <input type="text" value={formData.migration_key} onChange={e => setFormData({...formData, migration_key: e.target.value})} className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all" placeholder="e.g. BERT, SME1" />
                </div>
              </div>

              <div className="pt-6">
                <button type="submit" className="w-full py-4 bg-slate-900 text-white rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] hover:bg-slate-800 transition-all shadow-xl shadow-slate-200">
                  {editingUser ? 'Update Profile' : 'Confirm Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
