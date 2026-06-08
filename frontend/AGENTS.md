# Frontend AGENTS

## Purpose

This file describes the existing frontend code in `frontend/` and the current implementation state for the Kanban MVP.

## Current implementation

- Framework: Next.js 16.1.6 with React 19.2.3.
- Styling: Tailwind CSS 4 through `postcss` pipeline.
- Drag and drop: `@dnd-kit/core` and `@dnd-kit/sortable`.
- Testing: `vitest` for unit tests, `@playwright/test` configured for end-to-end tests.

## Key folders and files

- `src/app/page.tsx`
  - Renders the main `KanbanBoard` client component.

- `src/components/KanbanBoard.tsx`
  - Main board state and UI.
  - Uses `useState` to manage local board data.
  - Implements drag-and-drop with `DndContext`, `DragOverlay`, and pointer sensors.
  - Handles column renaming, card creation, card deletion, and moving cards between columns.

- `src/components/KanbanColumn.tsx`
  - Renders a single column.
  - Uses `useDroppable` to accept dragged cards.
  - Uses `SortableContext` to render sortable cards inside the column.
  - Includes an inline column title input and the `NewCardForm`.

- `src/components/KanbanCard.tsx`
  - Represents a draggable card.
  - Uses `useSortable` for drag behavior and CSS transforms.
  - Includes a delete button.

- `src/components/KanbanCardPreview.tsx`
  - Rendered during drag overlay as a preview of the active card.

- `src/components/NewCardForm.tsx`
  - Toggles between a button and a card creation form.
  - Adds cards with title and details.

- `src/lib/kanban.ts`
  - Defines the board data model and types: `Card`, `Column`, `BoardData`.
  - Provides `initialData` with five columns and sample cards.
  - Implements `moveCard` logic for moving cards within and across columns.
  - Provides `createId` helper for generating unique card IDs.

## Existing tests

- `src/components/KanbanBoard.test.tsx`
  - Unit coverage for the board component and interactions.

## Notes on current state

- The frontend is currently a static client-side demo.
- No backend integration exists yet.
- No authentication, persistence, or API calls are implemented.
- The current board state resets on page refresh.

## Recommended immediate tasks

1. Keep the current `KanbanBoard` UI and drag/drop logic.
2. Add backend API integration for board persistence and auth.
3. Add an AI sidebar only after the backend is serving board data.
4. Keep tests focused on component behavior and user flows.
