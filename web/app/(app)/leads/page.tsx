'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { Lead } from '@/lib/types'
import { Plus, Search, ChevronRight, X, CheckCircle, Filter, Table, LayoutList } from 'lucide-react'

const STATUSES = ['New', 'Contacted', 'Interested', 'Proposal Sent', 'Won', 'Lost', 'On Hold']
const PRIORITIES = ['Low', 'Medium', 'High']

const STATUS_COLORS: Record<string, string> = {
  New: 'bg-gray-100 text-gray-700',
  Contacted: 'bg-blue-100 text-blue-700',
  Interested: 'bg-yellow-100 text-yellow-700',
  'Proposal Sent': 'bg-purple-100 text-purple-700',
  Won: 'bg-green-100 text-green-700',
  Lost: 'bg-red-100 text-red-700',
  'On Hold': 'bg-orange-100 text-orange-700',
}

const PRIORITY_COLORS: Record<string, string> = {
  High: 'bg-red-100 text-red-700',
  Medium: 'bg-yellow-100 text-yellow-700',
  Low: 'bg-gray-100 text-gray-600',
}

function blank(): Partial<Lead> {
  return {
    business_name: '', category: '', city: '', state: '',
    phone: '', email: '', website: '', owner_name: '',
    status: 'New', priority: 'Medium', next_follow_up_at: '', notes: '',
  }
}

function followUpStatus(date: string | null | undefined): 'overdue' | 'this-week' | 'future' | 'none' {
  if (!date) return 'none'
  const d = new Date(date)
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  const week = new Date(now)
  week.setDate(week.getDate() + 7)
  if (d < now) return 'overdue'
  if (d <= week) return 'this-week'
  return 'future'
}

export default function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [filter, setFilter] = useState('All')
  const [search, setSearch] = useState('')
  const [modal, setModal] = useState<Partial<Lead> | null>(null)
  const [saving, setSaving] = useState(false)
  const [converting, setConverting] = useState(false)

  // Extra filters
  const [filterPriority, setFilterPriority] = useState('All')
  const [filterState, setFilterState] = useState('All')
  const [filterCategory, setFilterCategory] = useState('All')
  const [filterFollowUp, setFilterFollowUp] = useState('All')

  // View mode
  const [viewMode, setViewMode] = useState<'card' | 'excel'>('card')

  const supabase = createClient()

  const load = useCallback(async () => {
    const { data } = await supabase.from('leads').select('*').order('created_at', { ascending: false })
    if (data) setLeads(data as Lead[])
  }, [supabase])

  useEffect(() => { load() }, [load])

  const uniqueStates = useMemo(() => {
    const s = Array.from(new Set(leads.map(l => l.state).filter(Boolean))).sort()
    return s
  }, [leads])

  const uniqueCategories = useMemo(() => {
    const c = Array.from(new Set(leads.map(l => l.category).filter(Boolean))).sort()
    return c
  }, [leads])

  const displayed = useMemo(() => leads.filter(l => {
    if (filter !== 'All' && l.status !== filter) return false
    if (filterPriority !== 'All' && l.priority !== filterPriority) return false
    if (filterState !== 'All' && l.state !== filterState) return false
    if (filterCategory !== 'All' && l.category !== filterCategory) return false
    if (filterFollowUp !== 'All') {
      const fs = followUpStatus(l.next_follow_up_at)
      if (filterFollowUp === 'Overdue' && fs !== 'overdue') return false
      if (filterFollowUp === 'This Week' && fs !== 'this-week') return false
      if (filterFollowUp === 'Not Set' && fs !== 'none') return false
    }
    if (!search) return true
    const t = search.toLowerCase()
    return l.business_name?.toLowerCase().includes(t) ||
      l.city?.toLowerCase().includes(t) ||
      l.category?.toLowerCase().includes(t) ||
      l.owner_name?.toLowerCase().includes(t)
  }), [leads, filter, filterPriority, filterState, filterCategory, filterFollowUp, search])

  function set(key: keyof Lead, val: string) {
    setModal(m => m ? { ...m, [key]: val } : m)
  }

  async function save() {
    if (!modal?.business_name) return
    setSaving(true)
    const now = new Date().toISOString()
    if (!modal.id) {
      await supabase.from('leads').insert([{
        ...modal,
        dedupe_key: crypto.randomUUID(),
        source: 'Manual',
        key_signals: '[]',
        personalized_openers: '[]',
        website_summary: '',
        raw_payload: '{}',
        last_seen_at: now,
        created_at: now,
        updated_at: now,
      }])
    } else {
      await supabase.from('leads').update({ ...modal, updated_at: now }).eq('id', modal.id)
    }
    setSaving(false)
    setModal(null)
    load()
  }

  async function convertToClient() {
    if (!modal?.id) return
    setConverting(true)
    const now = new Date().toISOString()
    const { data: client } = await supabase.from('clients').insert([{
      lead_id: modal.id,
      business_name: modal.business_name,
      website: modal.website || '',
      phone: modal.phone || '',
      email: modal.email || '',
      city: modal.city || '',
      state: modal.state || '',
      category: modal.category || '',
      status: 'Active',
      monthly_value: 0,
      total_value: 0,
      notes: modal.notes || '',
      created_at: now,
      updated_at: now,
    }]).select().single()

    if (client) {
      await supabase.from('leads').update({
        status: 'Won',
        converted_to_client_id: client.id,
        updated_at: now,
      }).eq('id', modal.id)
    }
    setConverting(false)
    setModal(null)
    load()
  }

  const hasActiveFilters = filterPriority !== 'All' || filterState !== 'All' || filterCategory !== 'All' || filterFollowUp !== 'All'

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Leads</h1>
          <p className="text-xs text-gray-400 mt-0.5">{leads.length} total · {displayed.length} shown</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode(v => v === 'card' ? 'excel' : 'card')}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
              viewMode === 'excel'
                ? 'bg-gray-900 text-white border-gray-900'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            }`}
            title="Toggle Excel view"
          >
            {viewMode === 'excel' ? <LayoutList size={14} /> : <Table size={14} />}
            {viewMode === 'excel' ? 'Card View' : 'Excel View'}
          </button>
          <button
            onClick={() => setModal(blank())}
            className="flex items-center gap-1.5 bg-blue-600 text-white px-3.5 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
          >
            <Plus size={15} /> Add Lead
          </button>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
        {['All', ...STATUSES].map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
              filter === s ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            {s}
            {s !== 'All' && (
              <span className="ml-1 text-xs opacity-50">{leads.filter(l => l.status === s).length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Search + extra filters */}
      <div className="flex flex-wrap gap-2 mb-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name, city, category..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>

        <select
          value={filterPriority}
          onChange={e => setFilterPriority(e.target.value)}
          className={`px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white ${filterPriority !== 'All' ? 'border-blue-400 text-blue-700' : 'border-gray-200 text-gray-600'}`}
        >
          <option value="All">All Priorities</option>
          {PRIORITIES.map(p => <option key={p}>{p}</option>)}
        </select>

        <select
          value={filterState}
          onChange={e => setFilterState(e.target.value)}
          className={`px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white ${filterState !== 'All' ? 'border-blue-400 text-blue-700' : 'border-gray-200 text-gray-600'}`}
        >
          <option value="All">All States</option>
          {uniqueStates.map(s => <option key={s}>{s}</option>)}
        </select>

        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className={`px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white ${filterCategory !== 'All' ? 'border-blue-400 text-blue-700' : 'border-gray-200 text-gray-600'}`}
        >
          <option value="All">All Categories</option>
          {uniqueCategories.map(c => <option key={c}>{c}</option>)}
        </select>

        <select
          value={filterFollowUp}
          onChange={e => setFilterFollowUp(e.target.value)}
          className={`px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white ${filterFollowUp !== 'All' ? 'border-blue-400 text-blue-700' : 'border-gray-200 text-gray-600'}`}
        >
          <option value="All">All Follow-ups</option>
          <option value="Overdue">Overdue</option>
          <option value="This Week">Due This Week</option>
          <option value="Not Set">Not Set</option>
        </select>

        {hasActiveFilters && (
          <button
            onClick={() => { setFilterPriority('All'); setFilterState('All'); setFilterCategory('All'); setFilterFollowUp('All') }}
            className="flex items-center gap-1 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg border border-red-200"
          >
            <X size={13} /> Clear
          </button>
        )}
      </div>

      {/* Card view */}
      {viewMode === 'card' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50/60">
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Business</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden md:table-cell">Category</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden lg:table-cell">Location</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden md:table-cell">Contact</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Status</th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden xl:table-cell">Follow-up</th>
                <th className="w-8 px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {displayed.map(lead => {
                const fs = followUpStatus(lead.next_follow_up_at)
                return (
                  <tr
                    key={lead.id}
                    onClick={() => setModal({ ...lead })}
                    className="border-b border-gray-50 hover:bg-gray-50/80 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{lead.business_name}</div>
                      {lead.owner_name && <div className="text-xs text-gray-400">{lead.owner_name}</div>}
                    </td>
                    <td className="px-4 py-3 text-gray-500 hidden md:table-cell">{lead.category || '—'}</td>
                    <td className="px-4 py-3 text-gray-500 hidden lg:table-cell">
                      {[lead.city, lead.state].filter(Boolean).join(', ') || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 hidden md:table-cell">{lead.phone || lead.email || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[lead.status] || 'bg-gray-100 text-gray-600'}`}>
                        {lead.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden xl:table-cell">
                      {lead.next_follow_up_at ? (
                        <span className={`text-xs ${fs === 'overdue' ? 'text-red-600 font-medium' : fs === 'this-week' ? 'text-yellow-600 font-medium' : 'text-gray-400'}`}>
                          {fs === 'overdue' ? '⚠ ' : ''}{new Date(lead.next_follow_up_at).toLocaleDateString()}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-300">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-300"><ChevronRight size={15} /></td>
                  </tr>
                )
              })}
              {displayed.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-14 text-center text-gray-400 text-sm">
                    {filter !== 'All' || hasActiveFilters ? 'No leads match the current filters.' : search ? 'No results' : 'No leads yet — add your first one!'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Excel view */}
      {viewMode === 'excel' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-x-auto">
          <table className="text-xs min-w-[1100px] w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-100 sticky top-0">
                {['Business Name', 'Category', 'City', 'State', 'Phone', 'Email', 'Website', 'Owner', 'Status', 'Priority', 'Follow-up', 'Notes', 'Created'].map(col => (
                  <th key={col} className="text-left px-3 py-2 font-semibold text-gray-600 whitespace-nowrap border-r border-gray-200 last:border-r-0">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayed.map((lead, i) => {
                const fs = followUpStatus(lead.next_follow_up_at)
                return (
                  <tr
                    key={lead.id}
                    onClick={() => setModal({ ...lead })}
                    className={`border-b border-gray-100 cursor-pointer hover:bg-blue-50/40 transition-colors ${i % 2 === 0 ? '' : 'bg-gray-50/40'}`}
                  >
                    <td className="px-3 py-1.5 font-medium text-gray-900 whitespace-nowrap border-r border-gray-100">{lead.business_name}</td>
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap border-r border-gray-100">{lead.category || '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap border-r border-gray-100">{lead.city || '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap border-r border-gray-100">{lead.state || '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap border-r border-gray-100">{lead.phone || '—'}</td>
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap border-r border-gray-100">{lead.email || '—'}</td>
                    <td className="px-3 py-1.5 border-r border-gray-100">
                      {lead.website
                        ? <a href={lead.website} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()} className="text-blue-500 hover:underline">{lead.website.replace(/^https?:\/\//, '').split('/')[0]}</a>
                        : <span className="text-gray-300">—</span>
                      }
                    </td>
                    <td className="px-3 py-1.5 text-gray-600 whitespace-nowrap border-r border-gray-100">{lead.owner_name || '—'}</td>
                    <td className="px-3 py-1.5 whitespace-nowrap border-r border-gray-100">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[lead.status] || 'bg-gray-100 text-gray-600'}`}>
                        {lead.status}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 whitespace-nowrap border-r border-gray-100">
                      {lead.priority ? (
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${PRIORITY_COLORS[lead.priority] || 'bg-gray-100 text-gray-600'}`}>
                          {lead.priority}
                        </span>
                      ) : '—'}
                    </td>
                    <td className={`px-3 py-1.5 whitespace-nowrap border-r border-gray-100 ${fs === 'overdue' ? 'text-red-600 font-medium' : fs === 'this-week' ? 'text-yellow-600 font-medium' : 'text-gray-400'}`}>
                      {lead.next_follow_up_at ? `${fs === 'overdue' ? '⚠ ' : ''}${new Date(lead.next_follow_up_at).toLocaleDateString()}` : '—'}
                    </td>
                    <td className="px-3 py-1.5 text-gray-500 max-w-[200px] truncate border-r border-gray-100">{lead.notes || '—'}</td>
                    <td className="px-3 py-1.5 text-gray-400 whitespace-nowrap">{lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                )
              })}
              {displayed.length === 0 && (
                <tr>
                  <td colSpan={13} className="px-4 py-14 text-center text-gray-400">
                    No leads match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={e => { if (e.target === e.currentTarget) setModal(null) }}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold text-gray-900">
                {modal.id ? modal.business_name : 'Add Lead'}
              </h2>
              <div className="flex items-center gap-2">
                {modal.id && !modal.converted_to_client_id && (
                  <button
                    onClick={convertToClient}
                    disabled={converting}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-green-50 text-green-700 hover:bg-green-100 rounded-lg font-medium border border-green-200 transition-colors"
                  >
                    <CheckCircle size={13} />
                    {converting ? 'Converting...' : 'Convert to Client'}
                  </button>
                )}
                {modal.converted_to_client_id && (
                  <span className="text-xs text-green-600 font-medium flex items-center gap-1">
                    <CheckCircle size={13} /> Converted to client
                  </span>
                )}
                <button onClick={() => setModal(null)} className="p1.5 hover:bg-gray-100 rounded-lg text-gray-400">
                  <X size={17} />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Field label="Business Name *">
                    <input value={modal.business_name || ''} onChange={e => set('business_name', e.target.value)} placeholder="Joe's Plumbing" className={INPUT} />
                  </Field>
                </div>
                <Field label="Category">
                  <input value={modal.category || ''} onChange={e => set('category', e.target.value)} placeholder="Plumber, Restaurant..." className={INPUT} />
                </Field>
                <Field label="Owner Name">
                  <input value={modal.owner_name || ''} onChange={e => set('owner_name', e.target.value)} placeholder="Joe Smith" className={INPUT} />
                </Field>
                <Field label="City">
                  <input value={modal.city || ''} onChange={e => set('city', e.target.value)} placeholder="Austin" className={INPUT} />
                </Field>
                <Field label="State">
                  <input value={modal.state || ''} onChange={e => set('state', e.target.value)} placeholder="TX" className={INPUT} />
                </Field>
                <Field label="Phone">
                  <input type="tel" value={modal.phone || ''} onChange={e => set('phone', e.target.value)} placeholder="(512) 555-0100" className={INPUT} />
                </Field>
                <Field label="Email">
                  <input type="email" value={modal.email || ''} onChange={e => set('email', e.target.value)} placeholder="joe@example.com" className={INPUT} />
                </Field>
                <div className="col-span-2">
                  <Field label="Website">
                    <input value={modal.website || ''} onChange={e => set('website', e.target.value)} placeholder="https://example.com" className={INPUT} />
                  </Field>
                </div>
                <Field label="Status">
                  <select value={modal.status || 'New'} onChange={e => set('status', e.target.value)} className={SELECT}>
                    {STATUSES.map(s => <option key={s}>{s}</option>)}
                  </select>
                </Field>
                <Field label="Priority">
                  <select value={modal.priority || 'Medium'} onChange={e => set('priority', e.target.value)} className={SELECT}>
                    {PRIORITIES.map(p => <option key={p}>{p}</option>)}
                  </select>
                </Field>
                <div className="col-span-2">
                  <Field label="Next Follow-up Date">
                    <input type="date" value={modal.next_follow_up_at?.split('T')[0] || ''} onChange={e => set('next_follow_up_at', e.target.value)} className={INPUT} />
                  </Field>
                </div>
                <div className="col-span-2">
                  <Field label="Notes">
                    <textarea
                      value={modal.notes || ''}
                      onChange={e => set('notes', e.target.value)}
                      rows={3}
                      placeholder="Any notes about this lead..."
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                    />
                  </Field>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
              <button
                onClick={save}
                disabled={saving || !modal.business_name}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
              >
                {saving ? 'Saving...' : modal.id ? 'Save Changes' : 'Add Lead'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const INPUT = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'
const SELECT = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
