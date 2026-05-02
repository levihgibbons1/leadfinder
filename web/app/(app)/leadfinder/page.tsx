'use client'

import { useState, useRef, useMemo } from 'react'
import { Search, Zap, Globe, Phone, Star, AlertCircle, Shuffle, Filter } from 'lucide-react'

interface LeadResult {
  business_name: string
  category: string
  city: string
  state: string
  phone: string
  website: string
  rating: number | null
  reviews: number | null
  key_signals: string[]
  personalized_openers: string[]
  website_summary: string
  status: string
}

const SUGGESTED_CATEGORIES = [
  'roofing contractor',
  'HVAC contractor',
  'pool builder',
  'general contractor',
  'siding contractor',
  'excavation contractor',
  'concrete contractor',
  'ventilation contractor',
  'remodeling contractor',
  'insulation contractor',
]

const STATES: [string, string][] = [
  ['Alabama', 'AL'], ['Alaska', 'AK'], ['Arizona', 'AZ'], ['Arkansas', 'AR'],
  ['California', 'CA'], ['Colorado', 'CO'], ['Connecticut', 'CT'], ['Delaware', 'DE'],
  ['Florida', 'FL'], ['Georgia', 'GA'], ['Hawaii', 'HI'], ['Idaho', 'ID'],
  ['Illinois', 'IL'], ['Indiana', 'IN'], ['Iowa', 'IA'], ['Kansas', 'KS'],
  ['Kentucky', 'KY'], ['Louisiana', 'LA'], ['Maine', 'ME'], ['Maryland', 'MD'],
  ['Massachusetts', 'MA'], ['Michigan', 'MI'], ['Minnesota', 'MN'], ['Mississippi', 'MS'],
  ['Missouri', 'MO'], ['Montana', 'MT'], ['Nebraska', 'NE'], ['Nevada', 'NV'],
  ['New Hampshire', 'NH'], ['New Jersey', 'NJ'], ['New Mexico', 'NM'], ['New York', 'NY'],
  ['North Carolina', 'NC'], ['North Dakota', 'ND'], ['Ohio', 'OH'], ['Oklahoma', 'OK'],
  ['Oregon', 'OR'], ['Pennsylvania', 'PA'], ['Rhode Island', 'RI'], ['South Carolina', 'SC'],
  ['South Dakota', 'SD'], ['Tennessee', 'TN'], ['Texas', 'TX'], ['Utah', 'UT'],
  ['Vermont', 'VT'], ['Virginia', 'VA'], ['Washington', 'WA'], ['West Virginia', 'WV'],
  ['Wisconsin', 'WI'], ['Wyoming', 'WY'],
]

const STATE_NAME_TO_ABBR = Object.fromEntries(STATES)

const SMALL_TOWN_MARKETS: [string, string][] = [
  ['Bozeman', 'MT'], ['Cody', 'WY'], ['Laramie', 'WY'], ['Sheridan', 'WY'],
  ['Sandpoint', 'ID'], ['Twin Falls', 'ID'], ['Lewiston', 'ID'], ['Bend', 'OR'],
  ['Roseburg', 'OR'], ['Grants Pass', 'OR'], ['Wenatchee', 'WA'], ['Ellensburg', 'WA'],
  ['Yakima', 'WA'], ['St. George', 'UT'], ['Cedar City', 'UT'], ['Durango', 'CO'],
  ['Montrose', 'CO'], ['Grand Junction', 'CO'], ['Farmington', 'NM'], ['Carlsbad', 'NM'],
  ['Pueblo', 'CO'], ['Hutchinson', 'KS'], ['Salina', 'KS'], ['Manhattan', 'KS'],
  ['Joplin', 'MO'], ['Branson', 'MO'], ['Cape Girardeau', 'MO'], ['Bentonville', 'AR'],
  ['Russellville', 'AR'], ['Pine Bluff', 'AR'], ['Muskogee', 'OK'], ['Stillwater', 'OK'],
  ['Enid', 'OK'], ['Waco', 'TX'], ['Abilene', 'TX'], ['Nacogdoches', 'TX'],
  ['Lake Charles', 'LA'], ['Monroe', 'LA'], ['Hattiesburg', 'MS'], ['Meridian', 'MS'],
  ['Dothan', 'AL'], ['Gadsden', 'AL'], ['Rome', 'GA'], ['Valdosta', 'GA'],
  ['Tifton', 'GA'], ['Ocala', 'FL'], ['Sebring', 'FL'], ['Punta Gorda', 'FL'],
  ['Kingsport', 'TN'], ['Cookeville', 'TN'], ['Bowling Green', 'KY'], ['Paducah', 'KY'],
  ['Muncie', 'IN'], ['Kokomo', 'IN'], ['Lima', 'OH'], ['Mansfield', 'OH'],
  ['Erie', 'PA'], ['Altoona', 'PA'], ['Johnstown', 'PA'], ['Morgantown', 'WV'],
  ['Beckley', 'WV'], ['Traverse City', 'MI'], ['Midland', 'MI'], ['Eau Claire', 'WI'],
  ['La Crosse', 'WI'], ['Mankato', 'MN'], ['Bemidji', 'MN'], ['Sioux City', 'IA'],
  ['Dubuque', 'IA'], ['Bismarck', 'ND'], ['Minot', 'ND'], ['Rapid City', 'SD'],
  ['Brookings', 'SD'], ['Augusta', 'ME'], ['Bangor', 'ME'], ['Burlington', 'VT'],
  ['Rutland', 'VT'], ['Concord', 'NH'], ['Keene', 'NH'],
]

export default function LeadFinderPage() {
  const [category, setCategory] = useState(SUGGESTED_CATEGORIES[0])
  const [customCategory, setCustomCategory] = useState('')
  const [city, setCity] = useState('')
  const [stateName, setStateName] = useState('Texas')
  const [limit, setLimit] = useState(10)
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)
  const [statusMsg, setStatusMsg] = useState('')
  const [results, setResults] = useState<LeadResult[]>([])
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Filters
  const [filterHasWebsite, setFilterHasWebsite] = useState(false)
  const [filterHasPhone, setFilterHasPhone] = useState(false)
  const [filterMinRating, setFilterMinRating] = useState(0)

  const filteredResults = useMemo(() => {
    return results.filter(lead => {
      if (filterHasWebsite && !lead.website) return false
      if (filterHasPhone && !lead.phone) return false
      if (filterMinRating > 0 && lead.rating !== null && lead.rating < filterMinRating) return false
      return true
    })
  }, [results, filterHasWebsite, filterHasPhone, filterMinRating])

  function randomize() {
    const [randCity, randStateAbbr] = SMALL_TOWN_MARKETS[Math.floor(Math.random() * SMALL_TOWN_MARKETS.length)]
    const randCategory = SUGGESTED_CATEGORIES[Math.floor(Math.random() * SUGGESTED_CATEGORIES.length)]
    const randStateName = STATES.find(([, abbr]) => abbr === randStateAbbr)?.[0] ?? 'Texas'
    setCity(randCity)
    setStateName(randStateName)
    setCategory(randCategory)
    setCustomCategory('')
  }

  async function runSearch() {
    const finalCategory = customCategory.trim() || category
    if (!finalCategory || !city) return

    setRunning(true)
    setProgress(0)
    setStatusMsg('Starting search...')
    setResults([])
    setError('')
    setExpanded(null)
    setFilterHasWebsite(false)
    setFilterHasPhone(false)
    setFilterMinRating(0)

    abortRef.current = new AbortController()

    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8502'
      const resp = await fetch(`${apiBase}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: finalCategory,
          city,
          state: STATE_NAME_TO_ABBR[stateName] ?? stateName,
          limit,
        }),
        signal: abortRef.current.signal,
      })

      const reader = resp.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const event = JSON.parse(line.slice(6))
          if (event.type === 'progress') {
            setProgress(event.pct)
            setStatusMsg(event.msg)
          } else if (event.type === 'done') {
            setResults(event.results)
            setProgress(1)
            setStatusMsg(`Found ${event.results.length} leads — saved to your Leads page`)
          } else if (event.type === 'error') {
            setError(event.msg)
          }
        }
      }
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setError(`Could not connect to LeadFinder API at ${process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8502'}`)
      }
    }

    setRunning(false)
  }

  function stop() {
    abortRef.current?.abort()
    setRunning(false)
    setStatusMsg('Stopped.')
  }

  const finalCategory = customCategory.trim() || category
  const canSearch = !!finalCategory && !!city

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
          <Zap size={22} className="text-blue-600" />
          LeadFinder
        </h1>
        <p className="text-sm text-gray-400 mt-1">Search local businesses, analyze their sites, and generate personalized outreach</p>
      </div>

      {/* Search form */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">

          {/* Category dropdown */}
          <div className="lg:col-span-1">
            <label className="block text-xs font-medium text-gray-600 mb-1">Business Category</label>
            <select
              value={category}
              onChange={e => { setCategory(e.target.value); setCustomCategory('') }}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white capitalize"
            >
              {SUGGESTED_CATEGORIES.map(c => (
                <option key={c} value={c} className="capitalize">{c}</option>
              ))}
              <option value="__other__">Other (type your own)</option>
            </select>
            {(category === '__other__' || customCategory) && (
              <input
                value={customCategory}
                onChange={e => setCustomCategory(e.target.value)}
                placeholder="e.g. landscaping company"
                className="mt-2 w-full px-3 py-2 border border-blue-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                autoFocus
              />
            )}
          </div>

          {/* City */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">City</label>
            <input
              value={city}
              onChange={e => setCity(e.target.value)}
              placeholder="Austin"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* State */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">State</label>
            <select
              value={stateName}
              onChange={e => setStateName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {STATES.map(([name]) => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
          </div>

          {/* Amount of leads */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Amount of Leads</label>
            <select
              value={limit}
              onChange={e => setLimit(Number(e.target.value))}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            >
              {[5, 10, 20, 30].map(n => <option key={n} value={n}>{n} leads</option>)}
            </select>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {!running ? (
            <button
              onClick={runSearch}
              disabled={!canSearch}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-40 text-sm font-medium"
            >
              <Search size={15} />
              Find Leads
            </button>
          ) : (
            <button
              onClick={stop}
              className="flex items-center gap-2 bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600 text-sm font-medium"
            >
              Stop
            </button>
          )}

          <button
            onClick={randomize}
            disabled={running}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-40"
          >
            <Shuffle size={14} />
            Random Market
          </button>

          {city && stateName && (
            <span className="text-xs text-gray-400">{city}, {stateName} · {finalCategory}</span>
          )}

          {(running || statusMsg) && (
            <div className="flex-1 min-w-[200px]">
              {running && (
                <div className="w-full bg-gray-100 rounded-full h-1.5 mb-1">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${Math.round(progress * 100)}%` }}
                  />
                </div>
              )}
              <p className="text-xs text-gray-500">
                {running ? `${Math.round(progress * 100)}% — ` : ''}{statusMsg}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 p-4 bg-red-50 border border-red-200 rounded-xl mb-4 text-sm text-red-700">
          <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          {/* Filter bar */}
          <div className="flex items-center gap-3 flex-wrap bg-white border border-gray-200 rounded-xl px-4 py-3">
            <Filter size={13} className="text-gray-400 flex-shrink-0" />
            <span className="text-xs font-medium text-gray-500">Filter:</span>

            <button
              onClick={() => setFilterHasWebsite(v => !v)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                filterHasWebsite
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Globe size={11} /> Has Website
            </button>

            <button
              onClick={() => setFilterHasPhone(v => !v)}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                filterHasPhone
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              <Phone size={11} /> Has Phone
            </button>

            <div className="flex items-center gap-2">
              <Star size={11} className="text-yellow-400 flex-shrink-0" />
              <span className="text-xs text-gray-500 whitespace-nowrap">Min rating:</span>
              <input
                type="range"
                min={0}
                max={5}
                step={0.5}
                value={filterMinRating}
                onChange={e => setFilterMinRating(Number(e.target.value))}
                className="w-24 accent-blue-600"
              />
              <span className="text-xs font-medium text-gray-700 w-6">{filterMinRating > 0 ? filterMinRating : 'Any'}</span>
            </div>

            <span className="ml-auto text-xs text-gray-400">
              {filteredResults.length} of {results.length} shown
            </span>
          </div>

          {filteredResults.map((lead, i) => (
            <div key={i} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <button
                className="w-full text-left px-5 py-4 hover:bg-gray-50/60 transition-colors"
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900">{lead.business_name}</h3>
                    <div className="flex items-center gap-3 mt-1 flex-wrap">
                      <span className="text-xs text-gray-400 capitalize">{lead.category}</span>
                      <span className="text-xs text-gray-400">{lead.city}, {lead.state}</span>
                      {lead.phone && (
                        <span className="flex items-center gap-1 text-xs text-gray-400">
                          <Phone size={10} />{lead.phone}
                        </span>
                      )}
                      {lead.rating && (
                        <span className="flex items-center gap-1 text-xs text-gray-400">
                          <Star size={10} className="text-yellow-400" />{lead.rating} ({lead.reviews})
                        </span>
                      )}
                      {lead.website && (
                        <a
                          href={lead.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="flex items-center gap-1 text-xs text-blue-500 hover:underline"
                        >
                          <Globe size={10} />{lead.website.replace(/^https?:\/\//, '').split('/')[0]}
                        </a>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {lead.key_signals.length > 0 && (
                      <span className="text-xs bg-orange-50 text-orange-700 px-2 py-0.5 rounded-full font-medium border border-orange-100">
                        {lead.key_signals.length} signals
                      </span>
                    )}
                    <span className="text-gray-300 text-xs">{expanded === i ? '▲' : '▼'}</span>
                  </div>
                </div>
              </button>

              {expanded === i && (
                <div className="border-t border-gray-100 px-5 py-4 space-y-4">
                  {lead.website_summary && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Website Summary</p>
                      <p className="text-sm text-gray-700">{lead.website_summary}</p>
                    </div>
                  )}
                  {lead.key_signals.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-2">Key Signals</p>
                      <ul className="space-y-1">
                        {lead.key_signals.map((s, j) => (
                          <li key={j} className="text-sm text-gray-700 flex gap-2">
                            <span className="text-orange-400 flex-shrink-0">•</span>{s}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {lead.personalized_openers.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-2">Personalized Openers</p>
                      <div className="space-y-2">
                        {lead.personalized_openers.map((opener, j) => (
                          <div key={j} className="bg-blue-50 rounded-lg p-3 text-sm text-gray-800 border border-blue-100">
                            {opener}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {filteredResults.length === 0 && (
            <div className="text-center py-10 text-sm text-gray-400">No leads match the current filters.</div>
          )}
        </div>
      )}
    </div>
  )
}
