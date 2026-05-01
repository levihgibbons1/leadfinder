'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { Project, Client } from '@/lib/types'
import { Plus, X, ChevronRight } from 'lucide-react'

const PROJECT_TYPES = ['Build', 'Optimize', 'Fix', 'Manage', 'Redesign', 'Other']
const PROJECT_STATUSES = ['Planning', 'In Progress', 'Review', 'Done', 'Cancelled']
const PRIORITIES = ['Low', 'Medium', 'High']

const STATUS_COLORS: Record<string, string> = {
  Planning: 'bg-gray-100 text-gray-600',
  'In Progress': 'bg-blue-100 text-blue-700',
  Review: 'bg-yellow-100 text-yellow-700',
  Done: 'bg-green-100 text-green-700',
  Cancelled: 'bg-red-100 text-red-600',
}

const PRIORITY_COLORS: Record<string, string> = {
  Low: 'text-gray-400',
  Medium: 'text-yellow-500',
  High: 'text-red-500',
}

function blank(): Partial<Project> {
  return {
    project_name: '', client_name: '', project_type: 'Build',
    status: 'Planning', priority: 'Medium',
    start_date: '', due_date: '', value: 0, notes: '',
  }
}

const STATUS_ORDER = ['Planning', 'In Progress', 'Review', 'Done', 'Cancelled']

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [filter, setFilter] = useState('Active')
  const [modal, setModal] = useState<Partial<Project> | null>(null)
  const [saving, setSaving] = useState(false)
  const supabase = createClient()

  const load = useCallback(async () => {
    const [pr, cl] = await Promise.all([
      supabase.from('projects').select('*').order('created_at', { ascending: false }),
      supabase.from('clients').select('id, business_name').order('business_name'),
    ])
    if (pr.data) setProjects(pr.data as Project[])
    if (cl.data) setClients(cl.data as Client[])
  }, [supabase])

  useEffect(() => { load() }, [load])

  function set(key: keyof Project, val: string | number) {
    setModal(m => m ? { ...m, [key]: val } : m)
  }

  async function save() {
    if (!modal?.project_name) return
    setSaving(true)
    const now = new Date().toISOString()
    if (!modal.id) {
      await supabase.from('projects').insert([{ ...modal, created_at: now, updated_at: now }])
    } else {
      await supabase.from('projects').update({ ...modal, updated_at: now }).eq('id', modal.id)
    }
    setSaving(false)
    setModal(null)
    load()
  }

  const displayed = filter === 'All'
    ? projects
    : filter === 'Active'
      ? projects.filter(p => !['Done', 'Cancelled'].includes(p.status))
      : projects.filter(p => p.status === filter)

  const grouped = STATUS_ORDER.map(status => ({
    status,
    items: displayed.filter(p => p.status === status),
  })).filter(g => g.items.length > 0)

  const p = modal

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Projects</h1>
          <p className="text-xs text-gray-400 mt-0.5">{projects.length} total</p>
        </div>
        <button
          onClick={() => setModal(blank())}
          className="flex items-center gap-1.5 bg-blue-600 text-white px-3.5 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          <Plus size={15} /> Add Project
        </button>
      </div>

      {/* Filter */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
        {['Active', 'All', ...PROJECT_STATUSES].map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium whitespace-nowrap transition-colors ${
              filter === s ? 'bg-blue-100 text-blue-700' : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            {s}
            {s !== 'Active' && s !== 'All' && (
              <span className="ml-1 text-xs opacity-50">{projects.filter(p => p.status === s).length}</span>
            )}
          </button>
        ))}
      </div>

      {grouped.length === 0 && (
        <div className="text-center py-20 text-gray-400 text-sm">
          No projects {filter !== 'All' ? `with status "${filter}"` : 'yet'}
        </div>
      )}

      <div className="space-y-6">
        {grouped.map(({ status, items }) => (
          <div key={status}>
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[status]}`}>{status}</span>
              <span className="text-xs text-gray-400">{items.length}</span>
            </div>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50/50">
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Project</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden md:table-cell">Client</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden sm:table-cell">Type</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden lg:table-cell">Due Date</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden lg:table-cell">Value</th>
                    <th className="w-8 px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map(project => (
                    <tr
                      key={project.id}
                      onClick={() => setModal({ ...project })}
                      className="border-b border-gray-50 last:border-0 hover:bg-gray-50/80 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">{project.project_name}</div>
                        <div className={`text-xs mt-0.5 font-medium ${PRIORITY_COLORS[project.priority] || 'text-gray-400'}`}>
                          {project.priority} priority
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-500 hidden md:table-cell">{project.client_name || '—'}</td>
                      <td className="px-4 py-3 text-gray-500 hidden sm:table-cell">{project.project_type}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs hidden lg:table-cell">
                        {project.due_date ? new Date(project.due_date).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-500 text-xs hidden lg:table-cell">
                        {project.value > 0 ? `$${project.value.toLocaleString()}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-300"><ChevronRight size={15} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      {/* Modal */}
      {p && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={e => { if (e.target === e.currentTarget) setModal(null) }}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold">{p.id ? 'Edit Project' : 'Add Project'}</h2>
              <button onClick={() => setModal(null)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400"><X size={17} /></button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Field label="Project Name *">
                    <input value={p.project_name || ''} onChange={e => set('project_name', e.target.value)} placeholder="Website Redesign" className={INPUT} />
                  </Field>
                </div>
                <div className="col-span-2">
                  <Field label="Client">
                    {clients.length > 0 ? (
                      <select
                        value={p.client_id || ''}
                        onChange={e => {
                          const client = clients.find(c => c.id === Number(e.target.value))
                          setModal(m => m ? { ...m, client_id: Number(e.target.value) || undefined, client_name: client?.business_name || '' } : m)
                        }}
                        className={INPUT}
                      >
                        <option value="">— Select client —</option>
                        {clients.map(c => <option key={c.id} value={c.id}>{c.business_name}</option>)}
                      </select>
                    ) : (
                      <input value={p.client_name || ''} onChange={e => set('client_name', e.target.value)} placeholder="Client name" className={INPUT} />
                    )}
                  </Field>
                </div>
                <Field label="Type">
                  <select value={p.project_type || 'Build'} onChange={e => set('project_type', e.target.value)} className={INPUT}>
                    {PROJECT_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                </Field>
                <Field label="Status">
                  <select value={p.status || 'Planning'} onChange={e => set('status', e.target.value)} className={INPUT}>
                    {PROJECT_STATUSES.map(s => <option key={s}>{s}</option>)}
                  </select>
                </Field>
                <Field label="Priority">
                  <select value={p.priority || 'Medium'} onChange={e => set('priority', e.target.value)} className={INPUT}>
                    {PRIORITIES.map(pr => <option key={pr}>{pr}</option>)}
                  </select>
                </Field>
                <Field label="Value ($)">
                  <input type="number" min="0" value={p.value || ''} onChange={e => set('value', parseFloat(e.target.value) || 0)} placeholder="0" className={INPUT} />
                </Field>
                <Field label="Start Date">
                  <input type="date" value={p.start_date?.split('T')[0] || ''} onChange={e => set('start_date', e.target.value)} className={INPUT} />
                </Field>
                <Field label="Due Date">
                  <input type="date" value={p.due_date?.split('T')[0] || ''} onChange={e => set('due_date', e.target.value)} className={INPUT} />
                </Field>
                <div className="col-span-2">
                  <Field label="Notes">
                    <textarea value={p.notes || ''} onChange={e => set('notes', e.target.value)} rows={3} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
                  </Field>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-500">Cancel</button>
              <button onClick={save} disabled={saving || !p.project_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
                {saving ? 'Saving...' : p.id ? 'Save Changes' : 'Add Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const INPUT = 'w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white'

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      {children}
    </div>
  )
}
