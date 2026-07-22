# Task 4 Report: Request Lifecycle and Loading Journey

## Status

Implemented and verified. The implementation commit is `d29851d` (`feat: add prompt loading transition`).

## RED evidence

1. `npm test -- src/hooks/useRecommendation.test.tsx src/App.test.tsx`
   - Restricted sandbox: Vite startup was blocked by Tailwind's native binary and `spawn EPERM` before test collection.
   - Elevated rerun: exit 1 as expected. `useRecommendation.test.tsx` failed to resolve the absent `./useRecommendation`; App tests failed because the hero remained rendered, `scrollIntoView` was not called, and no error Alert existed.

## GREEN evidence

1. `npm test -- src/hooks/useRecommendation.test.tsx src/components/LoadingJourney.test.tsx src/App.test.tsx`
   - Passed: 3 test files, 9 tests.
   - Covers deferred request lifecycle, payload mapping (`target_count`, `agentic_mode`), duplicate-submit guard, plain error state, semantic four-stage progress, hero-to-compact transition, smooth scroll, reduced-motion `{ behavior: "auto", block: "start" }`, and prompt preservation after error.
2. `npm run typecheck`
   - Passed: `tsc -b --pretty false`.
3. `npm run build`
   - Passed: `tsc -b && vite build`; Vite built the production bundle successfully.
4. `git diff --check`
   - Passed before the implementation commit.

## Files

- `frontend/src/hooks/useRecommendation.ts`
- `frontend/src/hooks/useRecommendation.test.tsx`
- `frontend/src/components/LoadingJourney.tsx`
- `frontend/src/components/LoadingJourney.test.tsx`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`

## Concerns

- No recommendation cards were added; rendering actual results remains the next task.
- `graphify-out/` was already untracked and was not staged or modified.