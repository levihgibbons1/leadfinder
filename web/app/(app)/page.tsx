'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { Target, Users, FolderKanban, ArrowRight, TrendingUp } from 'lucide-react'
import type { Lead, Client, Project } from '@/lib/types'

const LEAD_STATUS_COLORS: Record<string, string> = {
  New: 'bg-gray-100 text-gray-600',
  Contacted: 'bg-blue-100 text-blue-700',
  Interested: 'bg-yellow-100 text-yellow-700',
  'Proposal Sent': 'bg-purple-100 text-purple-700',
  Won: 'bg-green-100 text-green-700',
  Lost: 'bg-red-100 text-red-700',
  'On Hold': 'bg-orange-100 text-orange-700',
}

const PROJECT_STATUS_COLORS: Record<string, string> = {
  Planning: 'bg-gray-100 text-gray-600',
  'In Progress': 'bg-blue-100 text-blue-700',
  Review: 'bg-yellow-100 text-yellow-700',
  Done: 'bg-green-100 text-green-700',
  Cancelled: 'bg-red-100 text-red-600',
}

export default function DashboardPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [clients, setClients] = useState<Client[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const supabase = createClient()

  useEffect(() => {
    async function load() {
      const [l, c, p] = await Promise.all([
        supabase.from('leads').select('*').order('created_at', { ascending: false }),
        supabase.from('clients').select('*'),
        supabase.from('projects').select('*').order('created_at', { ascending: false }),
      ])
      if (l.data) setLeads(l.data as Lead[])
      if (c.data) setClients(c.data as Client[])
      if (p.data) setProjects(p.data as Project[])
    }
    load()
  }, [])

  const activeLeads = leads.filter(l => !['Won', 'Lost'].includes(l.status))
  const activeClients = clients.filter(c => c.status === 'Active')
  const activeProjects = projects.filter(p => !['Done', 'Cancelled'].includes(p.status))

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="text-sm text-gray-400 mt-1">{today}</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard href="/leads" label="Active Leads" value={activeLeads.length} icon={<Target size={18} />} color="blue" />
        <StatCard href="/clients" label="Active Clients" value={activeClients.length} icon={<Users size={18} />} color="green" />
        <StatCard href="/projects" label="Active Projects" value={activeProjects.length} icon={<FolderKanban size={18} />} color="purple" />
        <StatCard href="/leads" label="Total Leads" value={leads.length} icon={<TrendingUp size={18} />} color="gray" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Recent Leads</h2>
            <Link href="/leads" className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1">
              View all <ArrowRight size={13} />
            </Link>
          </div>
          <div className="space-y-0">
            {leads.slice(0, 6).map(lead => (
              <div key={lead.id} className="flex items-center justify-between py-2.5 border-b border-gray-50 last:border-0">
                <div className="min-w-0 mr-3">
                  <p className="text-sm font-medium text-gray-900 truncate">{lead.business_name}</p>
                  <p className="text-xs text-gray-400">{[lead.category, lead.city].filter(Boolean).join(' · ')}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${LEAD_STATUS_COLORS[lead.status] || 'bg-gray-100 text-gray-600'}`}>
                  {lead.status}
                </span>
              </div>
            ))}
            {leads.length === 0 && (
              <p className="text-sm text-gray-400 py-6 text-center">No leads yet</p>
            )}
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900">Active Projects</h2>
            <Link href="/projects" className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1">
              View all <ArrowRight size={13} />
            </Link>
          </div>
          <div className="space-y-0">
            {activeProjects.slice(0, 6).map(project => (
              <div key={project.id} className="flex items-center justify-between py-2.5 border-b border-gray-50 last:border-0">
                <div className="min-w-0 mr-3">
                  <p className="text-sm font-medium text-gray-900 truncate">{project.project_name}</p>
                  <p className="text-xs text-gray-400">{[project.client_name, project.project_type].filter(Boolean).join(' · ')}</p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${PROJECT_STATUS_COLORS[project.status] || 'bg-gray-100 text-gray-600'}`}>
                  {project.status}
                </span>
              </div>
            ))}
            {activeProjects.length === 0 && (
              <p className="text-sm text-gray-400 py-6 text-center">No active projects</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ href, label, value, icon, color }: {
  href: string; label: string; value: number; icon: React.ReactNode
  color: 'blue' | 'green' | 'purple' | 'gray'
}) {
  const colors = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    gray: 'bg-gray-100 text-gray-500',
  }
  return (
    <Link href={href} className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 hover:shadow-sm transition-all">
      <div className={`inline-flex p-2 rounded-lg ${colors[color]} mb-3`}>{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </Link>
  )
}
