# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Target Vocabulary Checker — a client-side single-page application for Japanese English learners to study vocabulary from the Target 1400/1900 series. No backend, no build step, no package manager.

## Running the App

```bash
python3 -m http.server 8080
# then visit http://localhost:8080
```

The CSV data files (`target1400.csv`, `target1900.csv`) must be in the same directory as `index.html`. If missing, the app falls back to inline sample data automatically.

---

## 1. アーキテクチャ・技術スタック

### 構成方針

- **単一ファイルSPA**: HTML・CSS・JS すべてが `index.html` にインライン。ビルドパイプライン・トランスパイラ・npm 不使用。
- **外部依存**: Google Fonts CDN のみ（`@import` で読み込み）。
- **デプロイ**: GitHub Pages（`main` ブランチの `index.html` を直接配信）。

### 外部フォント（CDN）

```css
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Noto+Sans+JP:wght@300;400;500;700&display=swap');
```

| フォント | 用途 |
|---|---|
| Outfit | 英単語・数値・UIラベル全般 |
| Noto Sans JP | 日本語の意味テキスト |

英語と日本語はセル生成時に JS で `font-family` を inline style で切り替える。

### Web API

- **Web Speech API** (`window.speechSynthesis`): 英単語の発音再生。`lang: 'en-US'` 固定。対応ブラウザ外では無音で無視される（`if (!window.speechSynthesis) return`）。
- **localStorage**: 全 UI 状態の永続化（後述）。
- **fetch API**: CSV ファイルの非同期読み込み（`async/await`）。

### iOS PWA 対応

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Vocab">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
```

ホーム画面追加時のアイコンは `apple-touch-icon.png`（180×180 px RGBA PNG）。ズーム完全無効化のため `touchstart`/`touchmove`/`touchend` を `passive: false` でハンドリング。

### データ構造

#### 単語オブジェクト

```js
{ no: number, word: string, meaning: string }
```

#### グローバル状態変数

| 変数 | 型 | 説明 |
|---|---|---|
| `allWords` | `{ '1400': WordObj[], '1900': WordObj[] }` | 全語彙（両冊） |
| `currentBook` | `'1400' \| '1900'` | 現在選択中の冊子 |
| `currentWords` | `WordObj[]` | テーブルに表示中の単語（フィルタ・シャッフル済み） |
| `maskStates` | `{ [key: string]: boolean }` | `${book}-${no}` → `true`=マスク中 |
| `flashWords` | `WordObj[]` | フラッシュカード用コピー（`openFlash` 時に `currentWords` から複製） |
| `flashIndex` | `number` | フラッシュカード現在位置（0-based） |
| `tableSwapped` | `boolean` | `true`=左:単語・右:意味（デフォルト）、`false`=左:意味・右:単語 |
| `formCollapsed` | `boolean` | ヘッダーの折り畳み状態 |

#### localStorage キー

| キー定数 | キー文字列 | 保存内容 |
|---|---|---|
| `LS_SETTINGS` | `vocab_settings` | `{ book, from, to, order, mask }` |
| `LS_MASKS` | `vocab_masks` | `maskStates` オブジェクト全体 |
| `LS_TABLE` | `vocab_table` | `{ book, words: number[] }` — 単語番号の順序付きリスト |
| `LS_COLLAPSED` | `vocab_collapsed` | `'0'` or `'1'` |

#### CSV フォーマット

```
no,word,meaning
1,ability,能力・才能
```

`meaning` はカンマを含む場合があるため、パーサーは `parts.slice(2).join(',')` で結合する。

### データフロー

```
DOMContentLoaded
  → loadSettings()     UI 状態復元（select・input 値）
  → loadMasks()        maskStates 復元
  → loadCollapsed()    折り畳み状態復元
  → loadBook('1400')   fetch CSV → parseCSV() → allWords['1400']
  → loadBook('1900')   fetch CSV → parseCSV() → allWords['1900']
  → restoreTable()     LS_TABLE から前回の表を再描画

ユーザー操作（「✦ 生成」ボタン）
  → generateTable()
      filter by range → optional shuffleArray()
      → maskStates を maskMode に従い初期化
      → saveTable()
      → renderTable()

テーブルセルタップ
  → tapMask(tdEl)      mask-el の display を toggle → saveMasks()

フラッシュカード
  → openFlash()        currentWords を flashWords にコピー
  → renderFlashCard()  flashIndex に対応するカードを描画
  → flashNext() / flashPrev()  flashIndex を±1して renderFlashCard()
```

### 主要関数一覧

| 関数 | 役割 |
|---|---|
| `loadBook(book)` | CSV fetch → parseCSV、失敗時 generateSampleData にフォールバック |
| `parseCSV(text)` | CSV テキスト → `WordObj[]`（ヘッダー行スキップ、空 word 除去） |
| `generateTable()` | range フィルタ＋順序適用 → renderTable |
| `renderTable(words)` | テーブル HTML 文字列を構築して `tableArea.innerHTML` に設定 |
| `tapMask(tdEl)` | `.mask-el` の `display` トグル → `maskStates` 更新・保存 |
| `swapColumns()` | `tableSwapped` トグル → maskStates 再初期化 → renderTable |
| `openFlash()` / `closeFlash()` | モーダルの `.open` クラス付け外し |
| `renderFlashCard()` | `flashWords[flashIndex]` を描画（フォント・サイズも動的切り替え） |
| `toggleFlashMask()` | フラッシュカードのカバー `.hidden` トグル |
| `saveSettings()` / `loadSettings()` | LS_SETTINGS の読み書き |
| `saveMasks()` / `loadMasks()` | LS_MASKS の読み書き |
| `saveTable(words)` / `restoreTable()` | LS_TABLE の読み書き |
| `selectBook(book, silent)` | currentBook 更新・ボタン active クラス切り替え（silent=true は saveSettings をスキップ） |
| `step(id, delta)` | range input を±delta して saveSettings |
| `resetAll()` | 全状態を初期値（book=1900, from=1, to=100, ordered, hide, tableSwapped=true）に戻す |
| `speak(word)` | Web Speech API で英語発音 |
| `speakCurrentFlash()` | フラッシュカード現在単語を speak |
| `openQR()` / `closeQR()` | QR オーバーレイの `.open` クラス付け外し |
| `toggleCollapse()` / `applyCollapse()` | ヘッダー折り畳み |
| `shuffleArray(arr)` | Fisher-Yates in-place シャッフル |
| `escHtml(str)` | `&`/`<`/`>` のエスケープ（innerHTML 挿入前に必ず使用） |
| `showToast(msg)` | 2秒間トースト表示（タイマー重複防止あり） |

---

## 2. デザイン方針

### `:root` CSS カスタムプロパティ（デザイントークン）

すべてのテーマ値はここで一元管理。変更するときは必ずここを編集する。

```css
:root {
  /* 背景・サーフェス */
  --bg:        #0f1117;   /* ページ背景（最暗） */
  --surface:   #1a1d27;   /* カード・テーブル行・モーダル背景 */
  --surface2:  #222535;   /* セカンダリサーフェス（hover 先・入力欄など） */
  --border:    #2e3248;   /* 区切り線・枠線 */

  /* アクセントカラー */
  --accent:    #5b6af0;   /* プライマリアクセント（ボタン・グラデーション始点） */
  --accent2:   #7c8cf8;   /* セカンダリアクセント（hover・リンク） */

  /* 意味テキスト・マスク */
  --red:       #e05555;   /* 意味テキスト色 */
  --red-dark:  #c03030;   /* マスク背景色 */

  /* テキスト */
  --text:      #e8eaf6;   /* メインテキスト（英単語など） */
  --text-sub:  #8b90b0;   /* サブテキスト（プレースホルダー・dim より明るい） */
  --text-dim:  #555a7a;   /* 最も暗いテキスト（ヘッダーラベル・#番号など） */

  /* その他 */
  --green:     #4caf84;   /* トースト背景・成功色 */
  --radius:    12px;      /* 標準角丸 */
  --radius-sm:  8px;      /* 小さい角丸（行セル・小ボタン） */
}
```

### ベーススタイル

- `* { box-sizing: border-box; margin: 0; padding: 0; }`
- `body`: `font-family: 'Outfit', 'Noto Sans JP', sans-serif; background: var(--bg); color: var(--text); padding-bottom: 60px;`
- ダークテーマのみ（ライトモード切り替えなし）
- スクロールバー: width 4px、border-radius 2px（webkit のみ対応）

### 主要コンポーネントクラス

| クラス | 説明 |
|---|---|
| `.header` | sticky ヘッダー。`linear-gradient(135deg, #1a1d27, #131620)`、z-index:100 |
| `.collapsible-body` / `.collapsed` | `.collapsed` で `max-height:0; overflow:hidden` に折り畳む |
| `.book-btn` / `.book-btn.active` | 冊子選択ボタン。`.active` で accent 背景 |
| `.step-btn` | 数値入力の±ボタン |
| `.generate-btn` | 生成ボタン（accent グラデーション背景） |
| `.reset-btn` | リセットボタン（surface2 背景、border あり） |
| `.word-table` | 語彙テーブル（border-collapse:separate, border-spacing:0 4px） |
| `.word-row` / `.word-row:hover` | テーブル行（hover で surface2） |
| `.td-word` | 英単語セル（width:50%、Outfit フォント、`clamp(12px,4vw,18px)`） |
| `.td-meaning` | 意味セル（width:50%、position:relative でマスク重ね） |
| `.td-speak` | 音声ボタンセル（width:36px、padding:0 4px） |
| `.speak-btn` | 表内音声ボタン（icon のみ、hover で accent2 色） |
| `.mask-el` | マスク要素（`position:absolute; inset:-2px -4px; background:#c03030`）。JS で `display:none/block` 切り替え |
| `.status-bar` | テーブル上部のステータスバー（語数・スワップ・フラッシュチェックボタン） |
| `.swap-btn` / `.swap-btn.active` | 列入れ替えボタン（active で accent 背景） |
| `.flash-btn` | フラッシュチェック起動ボタン |
| `.modal-overlay` / `.modal-overlay.open` | フラッシュカードモーダル背景。`.open` で `opacity:1; pointer-events:all` |
| `.modal` | モーダル本体（max-width:380px、`transform:translateY(20px→0)` でアニメーション） |
| `.modal-close` | モーダル閉じる×ボタン（26×26px 丸ボタン、hover で red 背景） |
| `.progress-bar` / `.progress-fill` | 進捗バー（accent→accent2 グラデーション） |
| `.flash-word` | フラッシュカードのメイン単語（最大 64px、JS でサイズ動的変更） |
| `.flash-meaning-wrap` | 答えのカバー付きコンテナ（タップでトグル） |
| `.flash-meaning-cover` / `.hidden` | 「タップして表示」カバー。`.hidden` で `display:none` |
| `.flash-speak-btn` | フラッシュカード内音声ボタン（48×48px、surface2 背景、flex 配置） |
| `.btn-next` | 「次へ」ボタン（flex:1、accent グラデーション） |
| `.btn-prev` | 「◀戻る」ボタン（48px 固定、surface2 背景） |
| `.qr-btn` | QR アイコンボタン（ヘッダー右端、opacity:0.85） |
| `.qr-overlay` / `.qr-overlay.open` | QR モーダル背景（z-index:500、opacity トランジション） |
| `.qr-card` | QR モーダル本体（surface 背景、flex 縦並び） |
| `.toast` / `.toast.show` | トースト通知（fixed、bottom:24px、`translateY(80px→0)` アニメーション、z-index:2000） |
| `.empty-state` | テーブル空時の表示（中央寄せ、絵文字＋テキスト） |
| `.loading-note` | CSV 読み込み中テキスト |

### モーダルパターン

モーダルの開閉は CSS クラス `.open` の付け外しで制御する（JS から直接 `display` を変えない）。

```js
// 開く
element.classList.add('open');
// 閉じる
element.classList.remove('open');
```

デフォルト状態: `opacity:0; pointer-events:none`
開いた状態: `opacity:1; pointer-events:all`（または `pointer-events:auto`）

### タイポグラフィ

- 英単語: Outfit、`clamp(12px, 4vw, 18px)`、`font-weight:600`、`color:var(--text)`
- 日本語意味: Noto Sans JP、`font-size:13px`、`font-weight:500`、`color:var(--red)`
- テーブルヘッダー: `font-size:10px; font-weight:600; letter-spacing:0.15em; text-transform:uppercase; color:var(--text-dim)`
- フラッシュカード単語: JS で動的設定（英語: 最大 48px、日本語: 最大 28px）

---

## 3. コーディング規則

### 言語・コメント

- **コメントは日本語**で書く（既存コードに倣う）。
- 英語のコメントは書かない（セクション区切りの `// ─── SECTION NAME ───` パターンのみ例外）。
- コメントは「なぜ」を説明するときのみ書く。処理を説明するだけのコメントは書かない。

### 非同期処理

- `async/await` を使用する（`Promise.then()` チェーンは使わない）。
- CSV 読み込みは両冊を並列フェッチ（`DOMContentLoaded` で `loadBook('1400')` と `loadBook('1900')` を `await` で順次呼び出し）。

### エラーハンドリング

- CSV フェッチ失敗は `catch` でサイレントにフォールバック（`generateSampleData()`）。
- localStorage 読み書きは `try/catch` で囲み、失敗時はデフォルト値を使う。
- エラーをユーザーに表示しない（コンソールにも出さない）。

### DOM 操作

- テーブルは `innerHTML` への HTML 文字列代入で一括更新する（個別 createElement は使わない）。
- ユーザー入力を innerHTML に挿入するときは **必ず `escHtml()`** を通す。
- モーダル開閉は `.open` クラスの付け外しで行う（`display` を直接変えない）。

### 状態管理

- `tableSwapped` のデフォルトは `true`（左:単語、右:意味）。
- `resetAll()` が戻るべきデフォルト値: book=`'1900'`、from=`1`、to=`100`、order=`ordered`、mask=`hide`、`tableSwapped=true`。
- `selectBook(book, silent=false)`: `silent=true` のときは `saveSettings()` を呼ばない（`loadSettings()` からの呼び出し時に使用）。

### テーブル描画

- `renderTable()` は `tableSwapped` の値を読み取り、`swapped=true` なら左=単語(Outfit/白)・右=意味(Noto/赤、maskable)。
- 右セルの色は `rightStyle.replace('color:#e8eaf6', 'color:#e05555')` で強制的に赤にする。
- マスク要素は `.mask-el` クラスの `<span>` で、`style="display:none"` / `display:block` を JS で切り替える（`visible` クラスは使わない）。
- 音声ボタン（`.td-speak` 列）は常に4番目の列として追加し、マスクとは独立させる。

### CSS 追加時のルール

- 新しい色・サイズ値は必ず `:root` のカスタムプロパティとして定義してから参照する。
- コンポーネントクラスは既存のネーミングパターン（BEM ではなくフラットな単語）に合わせる。
- 新しいモーダルは `.modal-overlay` / `.modal-overlay.open` パターンを踏襲する。

---

## 4. ファイル構成の方針

### ファイル一覧

```
index.html            # アプリ本体（HTML + CSS + JS、すべてインライン）
target1400.csv        # Target 1400 語彙データ（no,word,meaning）
target1900.csv        # Target 1900 語彙データ（no,word,meaning）
apple-touch-icon.png  # iOS ホーム画面アイコン（180×180 px RGBA PNG）
qr.png                # QR コード画像（サイトURL→シェアモーダルで表示）
resize_icon.py        # アイコン作成用スクリプト（IMG_5804.png → apple-touch-icon.png）
gen_icon.py           # アイコン生成スクリプト（Python stdlib のみ、PIL 不使用）
CLAUDE.md             # 本ファイル
```

### 方針

- **新ファイルを作らない**: 機能追加はすべて `index.html` へのインライン追加で行う。JS ファイル・CSS ファイルの分離は行わない。
- **データファイルはCSVのまま**: JSON や DB への移行は行わない。
- **アイコン変更**: `apple-touch-icon.png` の更新は Python スクリプト（`resize_icon.py` or `gen_icon.py`）で行い、PIL/Pillow 等の外部ライブラリは使わない。
- **画像ファイル**: `qr.png` と `apple-touch-icon.png` のみ。スプライトシート・SVGスプライト等は使わない（SVG はインライン HTML に直接記述）。
- **`index.html` 内の構造**: `<style>` → `<body>` → `<script>` の順。スクリプトは `<body>` 末尾に2ブロック（アプリロジック + iOS ズーム無効化）。

### Git・デプロイ

- `main` ブランチが GitHub Pages として公開される。
- 機能ブランチは `main` から切る（`git checkout main && git pull` してから `git checkout -b <branch>`）。
- PR は squash merge でマージし、`main` にコミットが積まれる。
