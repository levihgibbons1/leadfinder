'use client'

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { Client } from '@/lib/types'
import { Plus, Building2, Phone, Globe, Mail, X } from 'lucide-react'
import Link from 'next/link'

const CLIENT_STATUSES = ['Active', 'Inactive', 'Churned']

const STATUS_COLORS: Record<string, string> = {
  Active: 'bg-green-100 text-green-700',
  Inactive: 'bg-gray-100 text-gray-600',
  Churned: 'bg-red-100 text-red-600',
}

function blank(): Partial<Client> {
  return {
    business_name: '', website: '', phone: '', email: '',
    city: '', state: '', category: '', status: 'Active',
    monthly_value: 0, total_value: 0, notes: '',
  }
}

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([])
  const [modal, setModal] = useState<Partial<Client> | null>(null)
  const [saving, setSaving] = useState(false)
  const supabase = createClient()

  const load = useCallback(async () => {
    const { data } = await supabase.from('clients').select('*').order('created_at', { ascending: false })
    if (data) setClients(data as Client[])
  }, [supabase])

  useEffect(() => { load() }, [load])

  function set(key: keyof Client, val: string | number) {
    setModal(m => m ? { ...m, [key]: val } : m)
  }

  async function save() {
    if (!modal?.business_name) return
    setSaving(true)
    const now = new Date().toISOString()
    if (!modal.id) {
      await supabase.from('clients').insert([{ ...modal, created_at: now, updated_at: now }])
    } else {
      await supabase.from('clients').update({ ...modal, updated_at: now }).eq('id', modal.id)
    }
    setSaving(false)
    setModal(null)
    load()
  }

  const c = modal

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Clients</h1>
          <p className="text-xs text-gray-400 mt-0.5">{clients.length} clients</p>
        </div>
        <button
          onClick={() => setModal(blank())}
          className="flex items-center gap-1.5 bg-blue-600 text-white px-3.5 py-2 rounded-lg hover:bg-blue-700 text-sm font-medium"
        >
          <Plus size={15} /> Add Client
        </button>
      </div>

      {clients.length === 0 ? (
        <div className="text-center py-24">
          <Building2 size={40} className="mx-auto mb-3 text-gray-200" />
          <p className="text-gray-500 font-medium">No clients yet</p>
          <p className="text-sm text-gray-400 mt-1">Add a client directly or convert a Won lead</p>
          <button onClick={() => setModal(blank())} className="mt-4 text-sm text-blue-600 hover:underline">
            Add your first client →
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {clients.map(client => (
            <Link
              key={client.id}
              href={`/clients/${client.id}`}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-200 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="min-w-0 mr-2">
                  <h3 className="font-semibold text-gray-900 truncate group-hover:text-blue-700 transition-colors">
                    {client.business_name}
                  </h3>
                  {client.category && <p className="text-xs text-gray-400 mt-0.5">{client.category}</p>}
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${STATUS_COLORS[client.status] || 'bg-gray-100 text-gray-600'}`}>
                  {client.status}
                </span>
              </div>

              <div className="space-y-1.5 text-sm text-gray-500">
                {(client.city || client.state) && (
                  <p className="text-xs">{[client.city, client.state].filter(Boolean).join(', ')}</p>
                )}
                {client.phone && (
                  <p className="flex items-center gap-1.5 text-xs">
                    <Phone size={11} className="flex-shrink-0 text-gray-300" />{client.phone}
                  </p>
                )}
                {client.email && (
                  <p className="flex items-center gap-1.5 text-xs truncate">
                    <Mail size={11} className="flex-shrink-0 text-gray-300" />{client.email}
                  </p>
                )}
                {client.website && (
                  <p className="flex items-center gap-1.5 text-xs truncate">
                    <Globe size={11} className="flex-shrink-0 text-gray-300" />
                    {client.website.replace(/^https?:\/\//, '')}
                  </p>
                )}
              </div>

              {client.monthly_value > 0 && (
                <div className="mt-3 pt-3 border-t border-gray-50">
                  <span className="text-sm font-semibold text-gray-900">${client.monthly_value.toLocaleString()}<span className="text-xs font-normal text-gray-400">/mo</span></span>
                </div>
              )}
            </Link>
          ))}
        </div>
      )}

      {/* Modal */}
      {c && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={e => { if (e.target === e.currentTarget) setModal(null) }}>
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[92vh] flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h2 className="text-base font-semibold">{c.id ? 'Edit Client' : 'Add Client'}</h2>
              <button onClick={() => setModal(null)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400">
                <X size={17} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Field label="Business Name *">
                    <input value={c.business_name || ''} onChange={e => set('business_name', e.target.value)} placeholder="ABC Company" className={INPUT} />
                  </Field>
                </div>
                <Field label="Category">
                  <input value={c.category || ''} onChange={e => set('category', e.target.value)} placeholder="Plumber, Restaurant..." className={INPUT} />
                </Field>
                <Field label="Status">
                  <select value={c.status || 'Active'} onChange={e => set('status', e.target.value)} className={INPUT}>
                    {CLIENT_STATUSES.map(s => <option key={s}>{s}</option>)}
                  </select>
                </Field>
                <Field label="City">
                  <input value={c.city || ''} onChange={e => set('city', e.target.value)} placeholder="Austin" className={INPUT} />
                </Field>
                <Field label="State">
                  <input value={c.state || ''} onChange={e => set('state', e.target.value)} placeholder="TX" className={INPUT} />
                </Field>
                <Field label="Phone">
                  <input type="tel" value={c.phone || ''} onChange={e => set('phone', e.target.value)} placeholder="(512) 555-0100" className={INPUT} />
                </Field>
                <Field label="Email">
                  <input type="email" value={c.email || ''} onChange={e => set('email', e.target.value)} placeholder="contact@example.com" className={INPUT} />
                </Field>
                <div className="col-span-2">
                  <Field label="Website">
                    <input value={c.website || ''} onChange={e => set('website', e.target.value)} placeholder="https://example.com" className={INPUT} />
                  </Field>
                </div>
                <Field label="Monthly Value ($)">
                  <input type="number" min="0" value={c.monthly_value || ''} onChange={e => set('monthly_value', parseFloat(e.target.value) || 0)} placeholder="0" className={INPUT} />
                </Field>
                <Field label="Total Contract Value ($)">
                  <input type="number" min="0" value={c.total_value || ''} onChange={e => set('total_value', parseFloat(e.target.value) || 0)} placeholder="0" className={INPUT} />
                </Field>
                <div className="col-span-2">
                  <Field label="Notes">
                    <textarea value={c.notes || ''} onChange={e => set('notes', e.target.value)} rows={3} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none" />
                  </Field>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-100">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
              <button onClick={save} disabled={saving || !c.business_name} className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium">
                {saving ? 'Saving...' : c.id ? 'Save Changes' : 'Add Client'}
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
