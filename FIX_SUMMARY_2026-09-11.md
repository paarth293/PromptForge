# PromptForge Frontend — Fix & Redesign Pass (2026-09-11)

Supersedes nothing; this is additive to the three prior audit docs (build audit, optimization plan, verification pass 3) — those covered mostly backend/seam issues. This pass covers the frontend crash you hit, a couple of bugs those audits couldn't see (they had no shell/npm), and a UI decluttering pass.

## 1. The crash you saw

`app/page.tsx` rendered `<AuditModeEntry ... />` (the AUDIT-mode / "Mode 2" entry screen) but never imported it — `components/AuditModeEntry.tsx` exists and is correct, it just wasn't wired into `page.tsx`'s import list. That's the exact `ReferenceError: AuditModeEntry is not defined` from your screenshot.

**Fix:** added a `next/dynamic` import for it alongside the other 7 dynamically-imported views, and passed it a `tenantId` prop (see #3).

## 2. A second, invisible bug: every entrance animation in the app was dead

Every card, banner and dropdown in the codebase is styled with `animate-in fade-in zoom-in-95 duration-200/300` — that's the class vocabulary of the `tailwindcss-animate` plugin. That plugin is **not** in `package.json` and never was, so every one of those classes has always been a no-op. Nothing has ever faded or zoomed in; it was all inert markup.

**Fix:** added a small hand-written CSS shim in `app/globals.css` that implements just the combinations actually used (`fade-in`, `zoom-in-95`, `duration-150/200/300`) as real `@keyframes`, so the animations the app was designed with actually run. No new dependency needed. Also added the `.no-scrollbar` utility class that `UnifiedNavigationShell.tsx` referenced but that didn't exist anywhere.

## 3. Auth token never sent (a blocker the prior audit already flagged, still open)

`lib/api.ts` was built to mint a JWT and attach `Authorization: Bearer <token>` to every request — but nothing in the app ever imported it. Every single fetch call across the app used the raw `fetch()` API with only an `X-Tenant-ID` header, no bearer token. Pass-3 verification called this out explicitly as a production blocker ("the frontend never sends Authorization... the only runnable mode is the unauthenticated one").

**Fix:** wired `apiFetch()`/`getAuthToken()` from `lib/api.ts` into every API call in `page.tsx`, `AgentChatWindow.tsx`, `ArenaView.tsx`, `AuditModeEntry.tsx`, `DossierView.tsx`, `DeepForgeLineageViewer.tsx`, `RedTeamFeed.tsx`, `MonitorDashboardView.tsx`, and the standalone `app/monitor/page.tsx` / `app/agents/[agentId]/page.tsx` routes.

Also fixed a related bug while in there: `AgentChatWindow`, `ArenaView`, and `AuditModeEntry` had no `tenantId` prop at all and silently hardcoded `'tenant-demo'` — meaning switching tenants in the nav bar never actually affected live chat, Arena battles, or Audit-mode ingestion. All three now accept and use `tenantId` from `page.tsx`'s `activeTenant` state.

**Still open (backend, not touched here):** `POST /api/auth/token` reportedly accepts any `api_key` with no real validation (per the pass-3 doc). Wiring the frontend to send a token doesn't close that gap — the backend still needs to check the key. Worth verifying that's fixed before treating auth as solved end-to-end. Also, `EventSource` (used for the Red Team live stream) can't carry an `Authorization` header at all — if the backend ever enforces auth on that route, the stream will need a signed token passed as a query param instead.

## 4. Verification method

No network access to `registry.npmjs.org` in this sandbox (same limitation the prior three audits hit), so a real `next build` wasn't possible here. Instead: ran a standalone `tsc` parse across every `.ts`/`.tsx` file in the project with `react-jsx`/`dom` libs enabled, filtering out only the expected "missing @types package" noise. Result: **0 syntax errors, 0 undefined-name errors** across the whole frontend, both before shipping the fix (confirmed `AuditModeEntry` was the only undefined reference) and after (confirmed no new ones introduced). This is not a substitute for actually running `npm run build` on your machine once — please do that before your next demo.

## 5. UI redesign — decluttering pass

The brief was "too crowded, not clean, must stand out." The worst offender was the top of the page stacking four full-width banners before you saw any content: the nav header, a large "audience" persona banner (with its own icon block, badge, and paragraph), a duplicate audience badge already shown in the header, and an 11-item breadcrumb strip with every stage's icon+label always visible.

**Changes in `UnifiedNavigationShell.tsx`:**
- Collapsed 3 stacked chrome rows into 2. The persona banner and the full breadcrumb-with-progress-bar are gone.
- Added a compact "current view" pill in the header (icon + label + "Step X of N") that opens the same Views menu.
- Replaced the always-expanded 11-button breadcrumb with a single slim progress row (surface name · audience · thin progress bar · %). Jumping to any of the 11 views still works from the "Views" dropdown — nothing lost, just not shown all at once.
- Segmented Ask/Deploy toggle and tenant switcher tightened up (smaller, less bordered/shadowed).

**Changes in `page.tsx`:**
- The FORGE/AUDIT mode switcher and the Ask/Deploy "surface" banners were rewritten as single slim toolbar rows (icon + one line + action buttons) instead of large cards with icon blocks, duplicate audience badges, and multi-sentence descriptions — that context now lives once, in the shell's progress row.
- Deployment result panel and cost ledger drawer kept as-is functionally, just re-indented to match the slimmer container.
- Hero heading bumped up a size, given a small "Forge Mode" kicker badge, and the primary CTA now uses a subtle glow instead of a flat shadow.

**Design tokens (`tailwind.config.js`, `app/globals.css`, `app/layout.tsx`):**
- Added `Inter` via `next/font/google` (the app had no webfont before — default system sans only).
- Added `forge.surface2`, `forge.borderSoft`, `shadow-glow`, `shadow-panel`, and a subtle `bg-grid-fade` radial background for depth on the main canvas.
- Added a thin custom scrollbar and a consistent `:focus-visible` ring app-wide.

**Visual consistency:** `/arena`, `/dossier`, `/evolve`, `/monitor`, and `/agents/[agentId]` are standalone routes that don't use the shared shell — they previously rendered on `bg-slate-950` with a generic "Return to PromptForge Home" bar, visually a different app from the main SPA (`bg-[#0B0F17]`/now `bg-forge-dark`). Swapped their outer backgrounds and border tokens to match the shared theme so navigating between the SPA and these routes doesn't feel like a context switch.

**Not done in this pass, by scope:** the 6 large view components (`ArenaView`, `DossierView`, `MonitorDashboardView`, `DeepForgeLineageViewer`, `RedTeamFeed`, `HardeningLogView`, `VerificationScorecardView`) were left visually as-is beyond the auth wiring — they're internally consistent with each other already, just information-dense by nature (red-team feeds, dossiers, monitoring dashboards). If you want the same decluttering treatment applied there, that's a good next pass.

## Files touched
`app/page.tsx`, `app/layout.tsx`, `app/globals.css`, `app/monitor/page.tsx`, `app/arena/page.tsx`, `app/dossier/page.tsx`, `app/evolve/page.tsx`, `app/agents/[agentId]/page.tsx`, `components/UnifiedNavigationShell.tsx`, `components/AuditModeEntry.tsx`, `components/AgentChatWindow.tsx`, `components/ArenaView.tsx`, `components/DossierView.tsx`, `components/DeepForgeLineageViewer.tsx`, `components/RedTeamFeed.tsx`, `components/MonitorDashboardView.tsx`, `tailwind.config.js`.
