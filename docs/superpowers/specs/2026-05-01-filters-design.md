# Filters & Excel View Design
Date: 2026-05-01

## Scope
Add client-side filters to LeadFinder results and the Leads tab. Add an Excel-style dense table toggle to the Leads tab.

## Approach
All filtering is client-side (data already loaded). No additional API calls or Supabase queries.

---

## LeadFinder Results Filters

Shown above results list after a search completes. Hidden when no results.

**Filters:**
- **Has Website** — toggle button, hides leads with no website URL
- **Has Phone** — toggle button, hides leads with no phone number
- **Min Rating** — slider 0–5 (step 0.5), hides leads with rating below threshold; leads with no rating are always shown

All three filters are independent and combinable.

---

## Leads Tab Filters

Horizontal filter bar above the table, always visible.

**Filters:**
- **Priority** — segmented control: All / Low / Medium / High
- **State** — dropdown populated from unique states present in loaded leads; default "All States"
- **Category** — dropdown populated from unique categories present in loaded leads; default "All Categories"
- **Follow-up** — dropdown: All / Overdue (date < today) / Due this week (date within 7 days) / Not set (no date)

Existing status filter buttons remain unchanged above the filter bar.

---

## Leads Tab Excel View Toggle

Button in the top-right of the Leads tab to switch between two view modes:

**Card view (default):** Current table with styled rows, avatar initials, status badges.

**Excel view:** Dense table, all columns visible, horizontal scroll, fixed header, smaller font, no avatars, plain text cells. Columns: Business Name, Category, City, State, Phone, Email, Website, Owner, Status, Priority, Follow-up Date, Notes, Created.

Toggle state is not persisted (resets on page reload).

---

## Data Flow
1. Supabase fetch returns all leads on mount (unchanged).
2. Filter state held in `useState` within each page component.
3. Filtered array derived via `useMemo` from raw leads + active filters.
4. Rendered list/table uses filtered array.

---

## Files Changed
- `web/app/(app)/leadfinder/page.tsx` — add filter bar + filter logic
- `web/app/(app)/leads/page.tsx` — add filter bar, follow-up filter, Excel view toggle + table
