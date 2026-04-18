# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Target Vocabulary Checker — a client-side single-page application for Japanese English learners to study vocabulary from the Target 1400/1900 series. No backend, no build step, no package manager.

## Running the App

Open `index.html` directly in a browser, or serve it with any static file server:

```bash
python3 -m http.server 8080
# then visit http://localhost:8080
```

The CSV data files (`target1400.csv`, `target1900.csv`) must be in the same directory as `index.html`. If they are missing, the app falls back to inline sample data automatically.

## Architecture

The entire application lives in `index.html` — all HTML, CSS, and JavaScript are inline in a single file. There is no build pipeline, no transpilation, and no external dependencies beyond Google Fonts.

### State

All mutable state is plain global variables:

| Variable | Purpose |
|---|---|
| `allWords` | `{ '1400': [...], '1900': [...] }` — all loaded vocabulary |
| `currentWords` | Words currently shown in the table (filtered + ordered) |
| `maskStates` | `{ '${book}-${no}': bool }` — per-word mask visibility |
| `flashWords` / `flashIndex` | Words and position for flashcard mode |
| `tableSwapped` | Whether meaning→word column order is active |
| `currentBook` | `'1400'` or `'1900'` |

State is persisted to `localStorage` under four keys: `vocab_settings`, `vocab_masks`, `vocab_table`, `vocab_collapsed`.

### Data Flow

1. Page load → `loadSettings()` restores UI state → `loadBook()` fetches CSV → `parseCSV()` → stored in `allWords`
2. User changes filter/order → `generateTable()` filters and optionally shuffles `currentWords` → `renderTable()` builds DOM
3. User taps a mask cell → `tapMask()` toggles visibility → `saveMasks()`
4. Flashcard open → `openFlash()` copies `currentWords` to `flashWords` → `renderFlashCard()` per navigation step

### CSV Format

```
no,word,meaning
1,ability,能力・才能
```

`meaning` may contain commas; the parser handles this by joining all fields after index 1.

### Key Functions

- `loadBook(book)` — fetch + parse CSV, fallback to `generateSampleData()`
- `generateTable()` — filter by range, apply order mode, call `renderTable()`
- `renderTable(words)` — build table HTML; respects `tableSwapped` and `maskStates`
- `tapMask(tdEl)` — toggle a single mask cell and persist
- `swapColumns()` — toggle `tableSwapped`, re-render table
- `openFlash()` / `closeFlash()` / `renderFlashCard()` — flashcard modal lifecycle
- `saveSettings()` / `loadSettings()` — persist/restore form state

### CSS Conventions

- CSS custom properties (`--color-*`, `--radius`, etc.) are defined on `:root` at the top of the `<style>` block — change theme values there.
- Dark theme only; accent color is `#5b6af0`.
- Font family switches between Outfit (English) and Noto Sans JP (Japanese) dynamically via JS class/style on cells.
- Fluid typography uses `clamp()`.
