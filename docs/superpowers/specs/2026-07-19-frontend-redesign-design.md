# Frontend Redesign Design

## Goal

Redesign SmartDiscover for first-time, non-technical users so the main path is
immediately understandable: describe the desired music, wait for curation,
review recommendations, refine them, and optionally save a Spotify playlist.
The redesign must preserve the existing FastAPI API and vanilla JavaScript
architecture.

## User and UX Decisions

- The primary user is a general music listener, not a developer inspecting the
  multi-agent system.
- Use a prompt-first guided layout instead of the current editorial dashboard.
- Keep agent telemetry available through progressive disclosure, but never let
  it compete with the primary action.
- Keep Indonesian as the initial language and preserve the existing ID/EN
  switch.
- Keep the existing dark visual identity, warm surface cards, orange accent,
  logo, and typography. Simplify hierarchy and spacing rather than introducing
  a new brand.
- Do not add a frontend framework, build tool, image dependency, or backend
  field.

## Information Architecture

### Header

The header contains only the SmartDiscover brand, language switch, and Spotify
connection button. Remove the issue-number copy and manual health-check button.
Automatic service checks remain active, but their detailed statuses move into
advanced or diagnostic disclosure. A degraded or mock catalog state is shown
only when it affects the user.

### Prompt composer

The first viewport is centered on one clear composer:

- Headline: `Temukan musik yang cocok dengan suasanamu.`
- Supporting copy: `Ceritakan mood, aktivitas, atau cerita yang ingin kamu
  dengarkan.`
- Input label: `Kamu ingin mendengarkan musik seperti apa?`
- Primary action: `Cari rekomendasi`.
- Quick prompts remain directly below the input as optional examples.

Track count and agent mode move into a collapsed `Pengaturan lanjutan` control.
Their current defaults remain unchanged, so a new user can submit without
understanding either setting. Agent-mode options receive short plain-language
descriptions.

### Processing state

The results region stays hidden until the first valid submission. Submission
reveals it and shows the existing skeleton cards plus one plain-language
progress indicator:

1. `Memahami suasana`
2. `Mencari lagu`
3. `Menyusun pilihan`
4. `Menyiapkan hasil`

The existing pipeline timeline continues driving this indicator. Internal
names such as Profiler, Ranker, and Presenter are shown only inside a collapsed
`Lihat proses AI` disclosure.

### Results

Successful results use this order:

1. A compact summary of the interpreted request and recommendation count.
2. Primary result actions: refine the request and save a Spotify playlist.
3. Quality or mock-mode notices only when actionable.
4. The recommendation list.
5. A collapsed `Lihat proses AI` panel for agent traces and diagnostics.

The existing intent sidebar becomes a compact result summary rather than a
sticky technical column. Desktop results use one readable content column with
a bounded width; mobile uses the same hierarchy without reordering controls.

### Track cards

Each card prioritizes:

1. Rank, title, and artist.
2. The recommendation reason.
3. Preview playback.
4. Open-in-Spotify and detail actions.

Match score, audio features, genres, and lyric metadata remain available in the
existing detail experience but are visually secondary. No album artwork is
introduced because the current response schema does not provide it.

## Interaction States

### Initial

Show the header, composer, examples, and a short three-step explanation. Do not
show an empty recommendation feed, placeholder sidebar, dossier, or idle agent
pipeline.

### Loading

Keep the prompt visible and disable only the submit button. Reveal the results
region, update the four-step progress indicator, and render skeleton cards.
Respect `prefers-reduced-motion`.

### Success

Move focus to the result heading without causing an abrupt scroll for keyboard
users. Keep refine and playlist actions close to the summary. Preview playback
continues allowing only one active track.

### Empty and error

An empty response displays a concise suggestion to broaden the prompt. A
request error appears next to the composer and preserves every input so the
user can submit again. Spotify session expiry points directly to the connection
button. Technical stack traces are never shown.

### Mock and degraded services

Mock Spotify mode is labelled as demo data near the result summary. Disabled
LLM mode is described as basic matching. These notices replace raw health
terminology such as `unreachable` or `degraded` in the primary interface.

## Component and Code Strategy

Reuse the current files and module boundaries:

- `web/index.html` changes page order, copy, and disclosure markup while
  preserving JavaScript-owned element IDs.
- `web/css/tokens.css` keeps the current palette and type system.
- `web/css/layout.css` implements the prompt-first flow and responsive result
  hierarchy.
- Existing component styles are simplified in place; no replacement component
  system is introduced.
- `web/js/main.js` controls initial/loading visibility and keeps existing API,
  language, OAuth, and pipeline bindings.
- `web/js/render.js` switches to the success, empty, and diagnostic result
  states using the existing render modules.
- `web/js/i18n.js` replaces editorial and technical primary copy in both
  languages.

The backend endpoints, request payloads, response models, state module, preview
module, OAuth flow, refine flow, and export flow remain unchanged.

## Responsive and Accessibility Requirements

- One column below `960px`; no sticky result sidebar.
- Primary controls remain at least 44px high on touch devices.
- Labels remain visible; placeholders never replace labels.
- Preserve keyboard activation, modal Escape handling, visible focus styles,
  `aria-live` status updates, semantic headings, and reduced-motion behavior.
- Advanced settings and diagnostics use native `details` and `summary`.
- Color is never the only indicator of loading, success, warning, or error.

## Error Handling

- A blank prompt keeps focus in the textarea and shows the existing localized
  validation message.
- Network and API failures restore the submit button, stop the timeline, keep
  form values, and show one actionable message.
- Missing previews retain the existing disabled preview state.
- Missing Spotify authentication does not block recommendations; it only
  disables playlist creation and points to Connect Spotify.

## Testing and Verification

- Run the complete Python test suite to confirm API and static-app behavior are
  unchanged.
- Add one focused DOM/state self-check only if the redesign introduces
  non-trivial visibility logic that is not covered by existing functions.
- Verify IDs used by `main.js`, OAuth, pipeline, modal, refine, export, and
  result renderers still exist exactly once.
- Check initial, loading, success, empty, error, mock, and disconnected Spotify
  states at desktop and mobile widths.
- Check keyboard navigation, visible focus, modal close behavior, language
  switching, preview playback, refine, and playlist actions.

## Success Criteria

- A first-time user can identify the prompt input and primary action without
  reading agent terminology.
- Track count and agent mode do not block or distract from the default flow.
- No empty result feed or idle telemetry appears before the first request.
- Loading progress uses plain-language steps.
- Results prioritize songs and actions; technical signals remain optional.
- The layout remains usable on a 360px-wide viewport.
- Existing recommendation, refine, preview, Spotify OAuth, playlist, i18n, and
  diagnostic behavior remains functional.

## Non-goals

- Backend or API schema changes.
- Album-art retrieval, user accounts, history, persistence, or personalization.
- A React, Vue, Svelte, or other framework migration.
- New agent behavior, ranking logic, semantic models, or Spotify capabilities.
- A separate admin or developer dashboard.
