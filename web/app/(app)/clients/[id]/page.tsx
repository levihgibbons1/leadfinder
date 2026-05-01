'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { Client, Contact, Project } from '@/lib/types'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Phone, Globe, Mail, MapPin, Plus, X, Pencil, Trash2 } from 'lucide-react'
import Link from 'next/link'

const PROJECT_TYPES = ['Build', 'Optimize', 'Fix', 'Manage', 'Redesign', 'Other']
const PROJECT_STATUSES = ['Planning', 'In Progress', 'Review', 'Done', 'Cancelled']
const PRIORITIES = ['Low', 'Medium', 'High']

const PROJECT_STATUS_COLORS: Record<string, string> = {
  Planning: 'bg-gray-100 text-gray-600',
  'In Progress': 'bg-blue-100 text-blue-700',
  Review: 'bg-yellow-100 text-yellow-700',
  Done: 'bg-green-100 text-green-700',
  Cancelled: 'bg-red-100 text-red-600',
}

type Tab = 'contacts' | 'projects' | 'notes'

export default function ClientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const supabase = createClient()

  const [client, setClient] = useState<Client | null>(null)
  const [contacts, setContacts] = useState<Contact[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [tab, setTab] = useState<Tab>('contacts')
  const [editingClient, setEditingClient] = useState(false)
  const [clientDraft, setClientDraft] = useState<Partial<Client>>({})
  const [contactModal, setContactModal] = useState<Partial<Contact> | null>(null)
  const [projectModal, setProjectModal] = useState<Partial<Project> | null>(null)
  const [saving, setSaving] = useState(false)
  const [notes, setNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)

  const load = useCallback(async () => {
    const [cl, co, pr] = await Promise.all([
      supabase.from('clients').select('*').eq('id', id).single(),
      supabase.from('contacts').select('*').eq('client_id', id).order('created_at'),
      supabase.from('projects').select('*').eq('client_id', id).order('created_at', { ascending: false }),
    ])
    if (cl.data) { setClient(cl.data as Client); setNotes(cl.data.notes || '') }
    if (co.data) setContacts(co.data as Contact[])
    if (pr.data) setProjects(pr.data as Project[])
  }, [id, supabase])

  useEffect(() => { load() }, [load])

  async function saveClient() {
    if (!client) return
    setSaving(true)
    await supabase.from('clients').update({ ...clientDraft, updated_at: new Date().toISOString() }).eq('id', client.id)
    setSaving(false)
    setEditingClient(false)
    load()
  }

  async function saveNotes() {
    if (!client) return
    setSavingNotes(true)
    await supabase.from('clients').update({ notes, updated_at: new Date().toISOString() }).eq('id', client.id)
    setSavingNotes(false)
  }

  async function saveContact() {
    if (!contactModal?.first_name && !contactModal?.last_name) return
    setSaving(true)
    const now = new Date().toISOString()
    if (!contactModal.id) {
      await supabase.from('contacts').insert([{ ...contactModal, client_id: Number(id), created_at: now }])
    } else {
      await supabase.from('contacts').update({ ...contactModal }).eq('id', contactModal.id)
    }
    setSaving(false)
    setContactModal(null)
    load()
  }

  async function deleteContact(contactId: number) {
    await supabase.from('contacts').delete().eq('id', contactId)
    load()
  }

  async function saveProject() {
    if (!projectModal?.project_name) return
    setSaving(true)
    const now = new Date().toISOString()
    if (!projectModal.id) {
      await supabase.from('projects').insert([{
        ...projectModal,
        client_id: Number(id),
        client_name: client?.business_name || '',
        created_at: now,
        updated_at: now,
      }])
    } else {
      await supabase.from('projects').update({ ...projectModal, updated_at: now }).eq('id', projectModal.id)
    }
    setSaving(false)
    setProjectModal(null)
    load()
  }

  async function deleteProject(projectId: number) {
    await supabase.from('projects').delete().eq('id', projectId)
    load()
  }

  if (!client) {
    return <div className="p-6 text-gray-400 text-sm">Loading...</div>
  }

  const co = contactModal
  const pr = projectModal

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Back */}
      <Link href="/clients" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-5">
        <ArrowLeft size={15} /> Clients
      </Link>

      {/* Client Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        {editingClient ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 flex items-center justify-between mb-2">
              <h2 className="font-semibold text-gray-700 text-sm">Edit Client</h2>
              <div className="flex gap-2">
                <button onClick={() => setEditingClient(false)} className="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
                <button onClick={saveClient} disabled={saving} className="text-sm bg-blue-600 text-white px-3 py-1 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
            {[
              ['business_name', 'Business Name'], ['category', 'Category'],
              ['phone', 'Phone'], ['email', 'Email'],
              ['website', 'Website'], ['city', 'City'],
              ['state', 'State'], ['status', 'Status'],
              ['monthly_value', 'Monthly Value ($)'], ['total_value', 'Total Value ($)'],
            ].map(([key, label]) => (
              <div key={key} className={key === 'business_name' || key === 'website' ? 'col-span-2' : ''}>
                <label className="block text-xs font-medium text-gray-500 mb-1">{label}</label>
                {key === 'status' ? (
                  <select
                    value={(clientDraft[key as keyof Client] as string) ?? client[key as keyof Client] ?? ''}
                    onChange={e => setClientDraft(d => ({ ...d, [key]: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                  >
                    <option>Active</option><option>Inactive</option><option>Churned</option>
                  </select>
                ) : (
                  <input
                    type={key.includes('value') ? 'number' : 'text'}
                    value={(clientDraft[key as keyof Client] as string | number) ?? client[key as keyof Client] ?? ''}
                    onChange={e => setClientDraft(d => ({ ...d, [key]: key.includes('value') ? parseFloat(e.target.value) || 0 : e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                )}
              </div>
            ))}
          </div>
        ) : (
          <div>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h1 className="text-xl font-semibold text-gray-900">{client.business_name}</h1>
                {client.category && <p className="text-sm text-gray-400 mt-0.5">{client.category}</p>}
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                  client.status === 'Active' ? 'bg-green-100 text-green-700' :
                  client.status === 'Churned' ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-600'
                }`}>{client.status}</span>
                <button
                  onClick={() => { setClientDraft({ ...client }); setEditingClient(true) }}
                  className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400"
                >
                  <Pencil size={15} />
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              {(client.city || client.state) && (
                <span className="flex items-center gap-1.5"><MapPin size={13} className="text-gray-300" />{[client.city, client.state].filter(Boolean).join(', ')}</span>
              )}
              {client.phone && (
                <a href={`tel:${client.phone}`} className="flex items-center gap-1.5 hover:text-gray-700"><Phone size={13} className="text-gray-300" />{client.phone}</a>
              )}
              {client.email && (
                <a href={`mailto:${client.email}`} className="flex items-center gap-1.5 hover:text-gray-700"><Mail size={13} className="text-gray-300" />{client.email}</a>
              )}
              {client.website && (
                <a href={client.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 hover:text-gray-700">
                  <Globe size={13} className="text-gray-300" />{client.website.replace(/^https?:\/\//, '')}
                </a>
              )}
            </div>

            {(client.monthly_value > 0 || client.total_value > 0) && (
              <div className="flex gap-6 mt-4 pt-4 border-t border-gray-50">
                {client.monthly_value > 0 && (
                  <div>
                    <p className="text-xs text-gray-400">Monthly</p>
                    <p className="text-base font-semibold text-gray-900">${client.monthly_value.toLocaleString()}</p>
                  </div>
                )}
                {client.total_value > 0 && (
                  <div>
                    <p className="text-xs text-gray-400">Total Value</p>
                    <p className="text-base font-semibold text-gray-900">${client.total_value.toLocaleString()}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5">
        {(['contacts', 'projects', 'notes'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
              tab === t ? 'bg-white border border-gray-200 text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t}
            {t === 'contacts' && contacts.length > 0 && <span className="ml-1.5 text-xs text-gray-400">{contacts.length}</span>}
            {t === 'projects' && projects.length > 0 && <span className="ml-1.5 text-xs text-gray-400">{projects.length}</span>}
          </button>
        ))}
      </div>

      {/* Contacts tab */}
      {tab === 'contacts' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">Contacts</h2>
            <button onClick={() => setContactModal({ first_name: '', last_name: '', role: '', email: '', phone: '', notes: '' })} className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium">
              <Plus size={14} /> Add Contact
            </button>
          </div>

          {contacts.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">No contacts yet</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {contacts.map(contact => (
                <div key={contact.id} className="flex items-start justify-between px-5 py-4">
                  <div>
                    <p className="font-medium text-gray-900">{[contact.first_name, contact.last_name].filter(Boolean).join(' ')}</p>
                    {contact.role && <p className="text-xs text-gray-400 mt-0.5">{contact.role}</p>}
                    <div className="flex gap-3 mt-1.5">
                      {contact.email && <a href={`mailto:${contact.email}`} className="text-xs text-blue-600 hover:underline">{contact.email}</a>}
                      {contact.phone && <a href={`tel:${contact.phone}`} className="text-xs text-gray-500">{contact.phone}</a>}
                    </div>
                    {contact.notes && <p className="text-xs text-gray-400 mt-1">{contact.notes}</p>}
                  </div>
                  <div className="flex gap-1 ml-3">
                    <button onClick={() => setContactModal({ ...contact })} className="p-1.5 hover:bg-gray-100 rounded text-gray-400"><Pencil size={13} /></button>
                    <button onClick={() => deleteContact(contact.id)} className="p-1.5 hover:bg-red-50 rounded text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Projects tab */}
      {tab === 'projects' && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
            <h2 className="font-medium text-gray-900">Projects</h2>
            <button
              onClick={() => setProjectModal({ project_name: '', project_type: 'Build', status: 'Planning', priority: 'Medium', start_date: '', due_date: '', value: 0, notes: '' })}
              className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              <Plus size={14} /> Add Project
            </button>
          </div>

          {projects.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">No projects yet</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {projects.map(project => (
                <div key={project.id} className="flex items-start justify-between px-5 py-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium text-gray-900">{project.project_name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${PROJECT_STATUS_COLORS[project.status] || 'bg-gray-100 text-gray-600'}`}>
                        {project.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">{project.project_type}{project.due_date ? ` · Due ${new Date(project.due_date).toLocaleDateString()}` : ''}</p>
                    {project.value > 0 && <p className="text-xs text-gray-500 mt-0.5">${project.value.toLocaleString()}</p>}
                    {project.notes && <p className="text-xs text-gray-400 mt-1 truncate max-w-sm">{project.notes}</p>}
                  </div>
                  <div className="flex gap-1 ml-3 flex-shrink-0">
                    <button onClick={() => setProjectModal({ ...project })} className="p-1.5 hover:bg-gray-100 rounded text-gray-400"><Pencil size={13} /></button>
                    <button onClick={() => deleteProject(project.id)} className="p-1.5 hover:bg-red-50 rounded text-gray-400 hover:text-red-500"><Trash2 size={13} /></button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Notes tab */}
      {tab === 'notes' && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-medium text-gray-900 mb-3">Notes</h2>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={10}
            placeholder="Add notes about this client..."
            className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
          <div className="flex justify-end mt-3">
            <button
              onClick={saveNotes}
              disabled={savingNotes}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {savingNotes ? 'Saving...' : 'Save Notes'}
            </button>
          </div>
        </div>
      )}

      {/* Contact Modal */}
      {co && (
        <Modal title={co.id ? 'Edit Contact' : 'Add Contact'} onClose={() => setContactModal(null)}>
          <div className="grid grid-cols-2 gap-4">
            <Field label="First Name">
              <input value={co.first_name || ''} onChange={e => setContactModal(m => m ? { ...m, first_name: e.target.value } : m)} className={INPUT} placeholder="Jane" />
            </Field>
            <Field label="Last Name">
              <input value={co.last_name || ''} onChange={e => setContactModal(m => m ? { ...m, last_name: e.target.value } : m)} className={INPUT} placeholder="Smith" />
            </Field>
            <div className="col-span-2">
              <Field label="Role / Title">
                <input value={co.role || ''} onChange={e => setContactModal(m => m ? { ...m, role: e.target.value } : m)} className={INPUT} placeholder="Owner, Manager..." />
              </Field>
            </div>
            <Field label="Email">
              <input type="email" value={co.email || ''} onChange={e => setContactModal(m => m ? { ...m, email: e.target.value } : m)} className={INPUT} placeholder="jane@example.com" />
            </Field>
            <Field label="Phone">
              <input type="tel" value={co.phone || ''} onChange={e => setContactModal(m => m ? { ...m, phone: e.target.value } : m)} className={INPUT} placeholder="(512) 555-0100" />
            </Field>
            <div className="col-span-2">
              <Field label="Notes">
                <textarea value={co.notes || ''} onChange={e => setContactModal(m => m ? { ...m, notes: e.target.value } : m)} rows={2} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
              </Field>
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-5">
            <button onClick={() => setContactModal(null)} className="px-4 py-2 text-sm text-gray-500">Cancel</button>
            <button onClick={saveContact} disabled={saving} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
              {saving ? 'Saving...' : co.id ? 'Save' : 'Add Contact'}
            </button>
          </div>
        </Modal>
      )}

      {/* Project Modal */}
      {pr && (
        <Modal title={pr.id ? 'Edit Project' : 'Add Project'} onClose={() => setProjectModal(null)}>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <Field label="Project Name *">
                <input value={pr.project_name || ''} onChange={e => setProjectModal(m => m ? { ...m, project_name: e.target.value } : m)} className={INPUT} placeholder="Website Redesign" />
              </Field>
            </div>
            <Field label="Type">
              <select value={pr.project_type || 'Build'} onChange={e => setProjectModal(m => m ? { ...m, project_type: e.target.value } : m)} className={INPUT}>
                {PROJECT_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </Field>
            <Field label="Status">
              <select value={pr.status || 'Planning'} onChange={e => setProjectModal(m => m ? { ...m, status: e.target.value } : m)} className={INPUT}>
                {PROJECT_STATUSES.map(s => <option key={s}>{s}</option>)}
              </select>
            </Field>
            <Field label="Priority">
              <select value={pr.priority || 'Medium'} onChange={e => setProjectModal(m => m ? { ...m, priority: e.target.value } : m)} className={INPUT}>
                {PRIORITIES.map(p => <option key={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Value ($)">
              <input type="number" min="0" value={pr.value || ''} onChange={e => setProjectModal(m => m ? { ...m, value: parseFloat(e.target.value) || 0 } : m)} className={INPUT} placeholder="0" />
            </Field>
            <Field label="Start Date">
              <input type="date" value={pr.start_date?.split('T')[0] || ''} onChange={e => setProjectModal(m => m ? { ...m, start_date: e.target.value } : m)} className={INPUT} />
            </Field>
            <Field label="Due Date">
              <input type="date" value={pr.due_date?.split('T')[0] || ''} onChange={e => setProjectModal(m => m ? { ...m, due_date: e.target.value } : m)} className={INPUT} />
            </Field>
            <div className="col-span-2">
              <Field label="Notes">
                <textarea value={pr.notes || ''} onChange={e => setProjectModal(m => m ? { ...m, notes: e.target.value } : m)} rows={2} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
              </Field>
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-5">
            <button onClick={() => setProjectModal(null)} className="px-4 py-2 text-sm text-gray-500">Cancel</button>
            <button onClick={saveProject} disabled={saving || !pr.project_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
              {saving ? 'Saving...' : pr.id ? 'Save' : 'Add Project'}
            </button>
          </div>
        </Modal>
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

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold">{title}</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400"><X size={17} /></button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  )
}
