# React + Vite Cinematic Frontend Redesign Design

## Goal

Replace the current vanilla HTML, CSS, and JavaScript frontend with a React +
Vite + TypeScript application that preserves SmartDiscover's existing FastAPI
behavior while delivering the approved prompt-first cinematic flow:

1. The first viewport focuses on the recommendation prompt.
2. Submission starts a visible loading journey.
3. The large prompt transitions into a compact prompt bar.
4. The page scrolls smoothly to the processing/results area.
5. Recommendation cards appear progressively when real results arrive.

This design supersedes the frontend implementation constraints in
`2026-07-19-frontend-redesign-design.md`. Its user-facing hierarchy remains a
useful baseline, but the earlier requirement to keep vanilla JavaScript no
longer applies.

## Approved Decisions

- Use React, Vite, TypeScript, Tailwind CSS, shadcn/ui, and Motion.
- Keep FastAPI as the only backend and API owner.
- Use the cinematic editorial visual direction.
- After submission, shrink the hero prompt into a compact prompt bar instead
  of removing it completely.
- Keep the refine control in the result area.
- Preserve Indonesian as the initial language and retain the ID/EN switch.
- Preserve the existing dark warm palette, coral accent, Fraunces display type,
  Inter body type, logo, and editorial recommendation cards.
- Use 21st.dev references as visual inspiration, not as a reason to import an
  unnecessary component stack. The relevant references are AI Input Hero
  (prompt focus), Music Card (track hierarchy), and Animated Collection
  (progressive list reveal).

## Technology and Dependency Boundaries

### Frontend stack

- React for component composition and local UI state.
- Vite for development, TypeScript compilation, and production assets.
- TypeScript for API contracts and component props.
- Tailwind CSS for layout and theme-token utilities.
- shadcn/ui with Radix primitives for accessible controls.
- Motion for the hero-to-bar layout transition, result entrances, and reduced
  motion-aware sequencing.
- Vitest and Testing Library for component behavior tests.

### Explicitly excluded

- Next.js or another frontend server runtime.
- Redux or another global state library.
- React Router for this single-screen application.
- A second animation package.
- A second component system alongside shadcn/ui.
- Backend schema changes solely to support the redesign.
- Album-art fetching or image enrichment.

## Runtime Architecture

FastAPI remains responsible for recommendation, refinement, health, Spotify
OAuth, Spotify session cookies, and playlist creation. React calls those same
relative endpoints and does not proxy secrets through a new server.

During development, Vite serves the frontend and proxies API and authentication
requests to the local FastAPI process. In production, `vite build` creates the
static frontend bundle and FastAPI serves the generated entry point and assets.
The build and local-run instructions must be updated together so a clean clone
has one documented setup path.

The production boundary is:

```text
Browser
  -> FastAPI root/static frontend response
  -> React application
  -> existing relative FastAPI endpoints
  -> existing recommendation and Spotify services
```

## Frontend Source Structure

```text
frontend/
  src/
    components/
      PromptComposer.tsx
      LoadingJourney.tsx
      ResultsSection.tsx
      SongCard.tsx
      IntentSummary.tsx
      RefineBar.tsx
      ExportActions.tsx
      TrackDetailDialog.tsx
      ui/
    hooks/
      useRecommendation.ts
    lib/
      api.ts
      i18n.ts
    types/
      recommendation.ts
    App.tsx
    main.tsx
    index.css
  index.html
  package.json
  tsconfig.json
  vite.config.ts
```

These are responsibility boundaries, not a requirement to split trivial code.
Small helpers should remain beside their only consumer. New abstractions are
added only when more than one component genuinely uses them.

## Application State and Data Flow

`App` owns one explicit view state: `idle`, `loading`, `success`, or `error`.
It also owns the prompt value, advanced form values, latest result, and latest
error. A focused `useRecommendation` hook performs request cancellation and
state transitions; it does not become a general store.

### Initial submission

1. The user submits a trimmed non-empty prompt with Enter or the primary button.
2. React preserves the prompt, disables duplicate submission, and enters
   `loading`.
3. `PromptComposer` changes from its hero layout to the compact layout.
4. `LoadingJourney` mounts and receives focus/status updates without stealing
   keyboard focus.
5. The document scrolls smoothly to the loading region when motion is allowed.
6. The existing recommendation endpoint is called with the current payload.

### Success

1. The loading timeline is finalized using response timing metadata when
   available.
2. The intent summary and result actions appear before the song list.
3. Song cards enter in response order with a short stagger.
4. Only one preview may play at a time.
5. The compact prompt bar remains usable for a completely new request.
6. Refine continues to call the existing refine endpoint and excludes already
   seen tracks through the current backend behavior.

### Error and empty results

- A blank prompt keeps focus in the composer and shows localized validation.
- A request failure cancels the timeline, preserves all form values, re-enables
  the compact prompt bar, and shows one actionable alert.
- Empty recommendations display a concise suggestion to broaden the prompt.
- Spotify authentication failures affect only Spotify actions, not music
  recommendation.
- Technical stack traces and raw exception bodies never appear in the UI.

## Screen and Component Design

### App shell

The header remains minimal: SmartDiscover brand, language switch, and Spotify
connection. Automatic health checks continue, but system detail stays inside
advanced or diagnostic disclosure unless it affects the result.

### Prompt composer

The initial composer occupies the visual center of the first viewport. It uses
a large textarea, one clear primary action, quick prompts, and collapsed
advanced settings. Enter submits; Shift+Enter adds a line.

Motion uses a shared layout identity so the composer visually becomes the
compact prompt bar rather than disappearing and reappearing. In compact form,
the current prompt remains editable and the primary action becomes a concise
search-again action.

### Loading journey

Loading shows the existing four plain-language phases:

1. Memahami suasana.
2. Mencari lagu.
3. Menyusun pilihan.
4. Menyiapkan hasil.

No recommendation skeleton cards are shown before recommendation data exists.
The loading surface uses the current orb/progress concept in a quieter,
responsive React component.

### Results and song cards

Results appear in this order:

1. Interpreted intent summary.
2. Refine and Spotify export actions.
3. Actionable quality notices.
4. Ordered recommendation cards.
5. Collapsed AI diagnostics.

Each song card prioritizes rank, title, artist, recommendation reason, preview,
Spotify link, and details. Score, audio features, genre, and lyric signals stay
secondary. Cards do not require album artwork because the current response
does not guarantee it.

shadcn/ui provides accessible Button, Textarea, Card, Collapsible, Dialog,
Skeleton, Alert, Badge, Label, Select, and Input primitives. Components are
customized through the shared theme rather than mixing visual systems.

## Visual Language and Motion

- Keep the near-black canvas, warm paper song surfaces, coral accent, and
  restrained green status color.
- Keep Fraunces for expressive headings and Inter for controls and body text.
- Use one accent color and a consistent radius/spacing system.
- Avoid pervasive glassmorphism, decorative gradients, and nested cards.
- The hero-to-bar transition should finish in roughly 350-500 ms.
- Native smooth scrolling follows the layout transition.
- Result cards use a roughly 70-100 ms stagger with a short fade-up.
- Hover motion stays subtle and never moves primary controls away from the
  pointer.
- Under `prefers-reduced-motion: reduce`, state changes are immediate, scrolling
  is not animated, and stagger is disabled.

## Compatibility and Feature Parity

The migration must preserve:

- recommendation and refinement request payloads;
- recommendation response fields and quality metadata;
- Indonesian and English copy switching;
- quick prompts and advanced settings;
- Spotify OAuth login, status, logout/session behavior, and playlist creation;
- preview fallback and single-active-preview behavior;
- track detail dialog;
- quality/degraded-mode notices;
- agent stage progress and collapsed diagnostics;
- desktop and mobile behavior.

The existing vanilla frontend is removed only after the React implementation
reaches this parity and the production build is served successfully by FastAPI.

## Accessibility and Responsive Requirements

- Preserve semantic heading order and visible labels.
- Keep primary touch targets at least 44 px high.
- Keep visible keyboard focus and Escape-to-close dialog behavior.
- Use `aria-live` for request status without repeatedly interrupting screen
  readers during animation.
- Do not use color as the only status indicator.
- Maintain a usable single-column layout at 360 px width.
- Prevent horizontal overflow at all supported widths.
- Keep the compact prompt bar readable and operable on small screens; it may
  wrap rather than compress controls below their usable size.

## Testing and Verification

### Test-first component coverage

- Initial state shows the hero composer and hides results.
- Enter submits while Shift+Enter preserves multiline editing.
- Loading converts the composer to compact mode and exposes the progress region.
- Success renders the returned recommendations in order.
- Error preserves prompt content and restores submission.
- Reduced-motion disables animated scroll/stagger behavior.
- Language switching updates primary and result copy.
- Preview playback stops a previously active preview.

### Integration verification

- TypeScript type-check and Vite production build pass.
- Vitest component suite passes.
- Existing Python suite passes without changing backend behavior.
- FastAPI serves the built application and its hashed assets.
- Browser verification covers idle, loading, success, empty, error, refine,
  Spotify disconnected, desktop, and 360 px mobile states.

## Success Criteria

- The first viewport has one unmistakable prompt action.
- Submission visibly transitions the prompt into a compact bar.
- The viewport moves smoothly to the active process and results.
- Real recommendation cards appear progressively after data arrives.
- Users can immediately start a new search from the compact bar.
- Existing recommendation, refine, preview, OAuth, playlist, i18n, and
  diagnostics behavior remains functional.
- The frontend is implemented in the approved stack with no second server or
  unnecessary state framework.
- A clean documented build produces assets that FastAPI serves successfully.

## Non-goals

- Recommendation, ranking, agent, embedding, or lyric-understanding changes.
- API schema redesign.
- New authentication or user-account storage.
- Search history or persistent frontend preferences.
- Album-art enrichment.
- Multi-page routing, SSR, or SEO infrastructure.
- Rebuilding FastAPI behavior inside JavaScript.
