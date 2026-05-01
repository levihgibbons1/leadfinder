export interface Lead {
  id: number
  dedupe_key: string
  source_id: string | null
  business_name: string
  category: string
  city: string
  state: string
  location: string
  phone: string
  website: string
  rating: number | null
  reviews: number | null
  key_signals: string
  personalized_openers: string
  website_summary: string
  status: string
  notes: string
  source: string
  priority: string
  contact_method: string
  email: string
  owner_name: string
  last_contacted_at: string
  next_follow_up_at: string
  status_reason: string
  converted_to_client_id: number | null
  created_at: string
  updated_at: string
}

export interface Client {
  id: number
  lead_id: number | null
  business_name: string
  website: string
  phone: string
  email: string
  city: string
  state: string
  category: string
  status: string
  monthly_value: number
  total_value: number
  notes: string
  created_at: string
  updated_at: string
}

export interface Contact {
  id: number
  client_id: number | null
  lead_id: number | null
  first_name: string
  last_name: string
  role: string
  email: string
  phone: string
  notes: string
  created_at: string
}

export interface Project {
  id: number
  lead_id: number | null
  client_id: number | null
  project_name: string
  client_name: string
  project_type: string
  status: string
  priority: string
  start_date: string
  due_date: string
  completion_date: string
  value: number
  notes: string
  created_at: string
  updated_at: string
}
