# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Target Vocabulary Checker — a client-side single-page application for Japanese English learners to study vocabulary from the Target 1400/1900 series and the Target 1000 idiom list, plus a grammar reference mode (「超特急英文法 攻略ポイント集」全23講) for browsing example sentences and memorization lists. No backend, no build step, no package manager.

## Running the App

```bash
python3 -m http.server 8080
# then visit http://localhost:8080
```

The CSV data files (`target1400.csv`, `target1900.csv`, `target1000.csv`) and `grammar.json` must be in the same directory as `index.html`. If the CSVs are missing, the app falls back to inline sample data automatically; if `grammar.json` fails to load, 文法モード shows an error message in place of the content.

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
- **fetch API**: CSV ファイルの非同期読み込み（`async/await`）。GitHub Pages の CDN/ブラウザキャッシュを回避するため、`loadBook()` は `?_=${Date.now()}` のキャッシュバスター付きURLで fetch する（`<head>` の `Cache-Control`/`Pragma`/`Expires` meta タグだけでは静的ホスティングの実 HTTP ヘッダーを上書きできないため）。

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
| `allWords` | `{ '1400': WordObj[], '1900': WordObj[], '1000': WordObj[] }` | 全語彙（単語1400・単語1900・熟語1000） |
| `currentBook` | `'1400' \| '1900' \| '1000'` | 現在選択中の冊子 |
| `currentWords` | `WordObj[]` | テーブルに表示中の単語（フィルタ・シャッフル済み） |
| `maskStates` | `{ [key: string]: boolean }` | `${book}-${no}` → `true`=マスク中 |
| `flashWords` | `WordObj[]` | フラッシュカード用コピー（`openFlash` 時に `currentWords` から複製） |
| `flashIndex` | `number` | フラッシュカード現在位置（0-based） |
| `flashResults` | `(boolean\|null)[]` | `flashWords` と対応する正解/不正解の記録。`null`=未回答、`openFlash` 時に全て `null` でリセット |
| `tableSwapped` | `boolean` | `true`=左:単語・右:意味（デフォルト）、`false`=左:意味・右:単語 |
| `theme` | `'dark' \| 'light'` | 現在のカラーテーマ。`document.documentElement`（`<html>`）の `data-theme` 属性として反映 |
| `fontScale` | `1〜5` | 文字サイズ段階（3が標準）。`FONT_SCALE_MAP` で倍率に変換し `#tableArea` の `style.zoom` とフラッシュカードのフォントサイズに適用 |
| `appMode` | `'vocab' \| 'grammar'` | 現在表示中のモード。`#vocabView`/`#grammarView` の表示切り替えとヘッダーアイコンの出し分けに使う |
| `grammarData` | `Lesson[] \| null` | `grammar.json` 読み込み後の文法データ（初回に文法モードへ切り替えたときに遅延フェッチ） |
| `grammarMaskMode` | `'show' \| 'hide'` | 文法モードの日本語訳・暗記リストの「」部分の初期表示（デフォルト `'show'`）。`document.documentElement` の `grammar-masked` クラスとして反映 |

#### 冊子ごとの最大番号

```js
const BOOK_MAX = { '1400': 1400, '1900': 1900, '1000': 1000 };
```

範囲入力（開始番号・終了番号）は `clampRangeInputs()` によって常に `[1, BOOK_MAX[currentBook]]` に収められる。冊子を切り替えたとき（`selectBook()`）と設定復元時（`loadSettings()`）の両方で呼び出す。

#### localStorage キー

| キー定数 | キー文字列 | 保存内容 |
|---|---|---|
| `LS_SETTINGS` | `vocab_settings` | `{ book, from, to, order, mask }` |
| `LS_MASKS` | `vocab_masks` | `maskStates` オブジェクト全体 |
| `LS_TABLE` | `vocab_table` | `{ book, words: number[] }` — 単語番号の順序付きリスト |
| `LS_THEME` | `vocab_theme` | `'dark'` or `'light'` |
| `LS_FONT_SCALE` | `vocab_font_scale` | `'1'`〜`'5'`（文字列） |
| `LS_APP_MODE` | `vocab_app_mode` | `'vocab'` or `'grammar'` |
| `LS_GRAMMAR_MASK` | `vocab_grammar_mask` | `'show'` or `'hide'` |

#### CSV フォーマット

```
no,word,meaning
1,ability,能力・才能
```

`meaning` はカンマを含む場合があるため、パーサーは `parts.slice(2).join(',')` で結合する。パーサーはクォート（`"..."`）を解釈しないため、**CSV 生成時にカンマを含む `meaning` をダブルクォートで囲んではいけない**（そのまま表示に混入する）。カンマはクォートなしでそのまま書く。

`target1000.csv` は Target 1000（熟語）のデータで、`no` は 1〜1000。

#### grammar.json フォーマット

語彙データは CSV だが、文法モードのコンテンツは講→節→例文/暗記ブロックの階層構造を持つため、**この 1 ファイルに限り JSON を使う**（「データファイルはCSVのまま」の例外）。`fetch()` で読み込み、`JSON.parse` 相当の `resp.json()` でそのまま使う。

```ts
Lesson[] = [{
  number: number,        // 第N講
  title: string,
  sections: [{
    number: string, title: string,
    content: [
      // type: 'example' — □アルファベット付きの例文
      { type: 'example', letter: string, sentence: string, tag: string,
        rewrites: [{ sentence: string, tag: string }],  // ＝/→ で始まる書き換え文
        translation: string[], gloss: string[], notes: string[] },
      // type: 'memo' — 〈見出し〉○項目 の暗記リスト
      { type: 'memo', header: string, headerSuffix: string, items: string[], notes: string[] },
    ]
  }]
}]
```

`content` は元 PDF に登場する順序どおり（例文と暗記ブロックが同一節内で混在することがあるため、`examples`/`blocks` を別配列にせず単一の順序付き配列にしている）。このファイルは `parse_grammar.py` で PDF のテキスト抽出結果（`pdftotext -layout` の出力）から生成した。新しい講を追加・修正する場合は `grammar.json` を直接編集するか、PDF を更新して `parse_grammar.py` を再実行する。

### データフロー

```
DOMContentLoaded
  → loadSettings()     UI 状態復元（select・input 値、clampRangeInputs() も実行）
  → loadMasks()        maskStates 復元
  → loadBook('1400')   fetch CSV → parseCSV() → allWords['1400']
  → loadBook('1900')   fetch CSV → parseCSV() → allWords['1900']
  → loadBook('1000')   fetch CSV → parseCSV() → allWords['1000']
  → restoreTable()     LS_TABLE から前回の表を再描画

設定アイコンタップ
  → openSettings()     設定モーダル（範囲・冊子指定フォーム、QRシェア、テーマ・文字サイズ）を開く

設定モーダル外（オーバーレイ）タップ
  → closeSettings()    settingsOverlay に onclick、モーダル本体には event.stopPropagation() で内側クリックは無視

設定モーダル見出し行のQR/テーマ/文字サイズアイコンタップ
  → openQR()           先に closeSettings()（z-indexで設定モーダルの下に隠れるのを防ぐ）→ QRオーバーレイを開く
  → toggleTheme()      <html> の data-theme 属性を切り替え → CSS変数がカスケードし再描画不要で全体に反映
  → cycleFontScale()   fontScale を 1→5→1 とループさせ setFontScale() を呼ぶ、トーストで現在値を通知

ユーザー操作（「✦ 生成」ボタン）
  → generateTable()
      filter by range → optional shuffleArray()
      → maskStates を maskMode に従い初期化
      → saveTable()
      → renderTable()
      → closeSettings()  生成成功時のみモーダルを閉じて表を見せる

テーブルセルタップ
  → tapMask(tdEl)      mask-el の display を toggle → saveMasks()

フラッシュカード
  → openFlash()        currentWords を flashWords にコピー、flashResults を null で初期化
  → renderFlashCard()  flashIndex に対応するカードを描画
  → flashAnswer(correct)  flashResults[flashIndex] を記録して次のカードへ。最後のカードなら showFlashResults()
  → flashPrev()         flashIndex を-1して renderFlashCard()（前のカードの回答を上書きし直せる）
  → showFlashResults()  #flashCardView を隠し #flashResultView に正解/不正解を色分けした一覧を描画

モード切替アイコンタップ（ヘッダー）
  → toggleAppMode()    appMode を 'vocab'⇔'grammar' でトグル
      → applyAppMode()     #vocabView/#grammarView の表示切り替え、ヘッダーアイコンの出し分け
      → 初回 'grammar' 切替時のみ loadGrammarIfNeeded() で grammar.json を遅延フェッチ

文法モード目次アイコンタップ
  → openToc()          grammarData 未読み込みなら先に loadGrammarIfNeeded() を await → populateToc() → モーダルを開く
  → scrollToLesson(n)  目次項目タップで該当 #lesson-N へ scrollIntoView、モーダルを閉じる

目次モーダル内のテーマ/文字サイズ/訳の表示切替アイコンタップ
  → toggleTheme() / cycleFontScale()  単語帳と共通の関数をそのまま呼ぶ（.js-theme-btn クラスで設定・目次の両ボタンを同期）
  → toggleGrammarMask()  grammarMaskMode を 'show'⇔'hide' でトグル → <html> に grammar-masked クラスを付け外し
      → 個別にタップして開いていた .gmask.revealed を全解除（モード変更時にリセット）

文法モードの訳・「」部分タップ
  → #grammarContent への1回限りのイベント委譲（DOMContentLoaded 時に登録）で .gmask 要素の revealed クラスを toggle

？アイコンタップ（ヘッダー、単語帳・文法モード共通）
  → openOnboarding()   onboardingStep をリセットして renderOnboardingStep() → モーダルを開く
  → renderOnboardingStep()  appMode に応じて ONBOARDING_VOCAB / ONBOARDING_GRAMMAR から現在ステップの内容を描画
  → onboardingNext() / onboardingPrev()  ステップを±1。最終ステップで「次へ」を押すと closeOnboarding()
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
| `openFlash()` / `closeFlash()` | モーダルの `.open` クラス付け外し。`openFlash()` は `flashResults` をリセットし `showFlashCardView()` を呼ぶ |
| `showFlashCardView()` / `showFlashResults()` | `#flashCardView`/`#flashResultView` の表示切り替え。`showFlashResults()` は正解/不正解数の集計と一覧描画も行う |
| `renderFlashCard()` | `flashWords[flashIndex]` を描画（フォント・サイズも動的切り替え） |
| `flashAnswer(correct)` | 「正解」「不正解」ボタンのハンドラ。`flashResults[flashIndex]` に記録し、最後のカードなら `showFlashResults()` を呼ぶ |
| `toggleFlashMask()` | フラッシュカードのカバー `.hidden` トグル |
| `saveSettings()` / `loadSettings()` | LS_SETTINGS の読み書き |
| `saveMasks()` / `loadMasks()` | LS_MASKS の読み書き |
| `saveTable(words)` / `restoreTable()` | LS_TABLE の読み書き |
| `selectBook(book, silent)` | currentBook 更新・ボタン active クラス切り替え・`clampRangeInputs()`（silent=true は saveSettings をスキップ） |
| `clampRangeInputs()` | 開始・終了番号を `BOOK_MAX[currentBook]` の範囲に収める |
| `step(id, delta)` | range input を±delta して `BOOK_MAX[currentBook]` を上限にクランプ、saveSettings |
| `openSettings()` / `closeSettings()` | 設定モーダル（範囲・冊子指定フォーム）の `.open` クラス付け外し。閉じるボタンはなく、オーバーレイタップ（`closeSettings()`）と生成/リセット成功時のみで閉じる |
| `resetAll()` | 全状態を初期値（book=1900, from=1, to=100, ordered, hide, tableSwapped=true）に戻し、設定モーダルを閉じる |
| `speak(word)` | Web Speech API で英語発音 |
| `speakCurrentFlash()` | フラッシュカード現在単語を speak |
| `openQR()` / `closeQR()` | QR オーバーレイの `.open` クラス付け外し（`openQR()` は先に `closeSettings()` を呼ぶ） |
| `toggleTheme()` / `applyTheme()` / `loadTheme()` | ダーク/ライト切り替え。`<html data-theme>` を更新し `.js-theme-btn` クラスを持つ全ボタン（設定モーダル・目次モーダル）のアイコンを差し替え |
| `cycleFontScale()` | 文字サイズアイコンのクリックハンドラ。`fontScale` を1→5→1でループさせ `setFontScale()` を呼ぶ |
| `setFontScale(level)` / `applyFontScale()` / `loadFontScale()` | 文字サイズ5段階（`FONT_SCALE_MAP`）の適用・復元。`#tableArea` と `#grammarContent` の両方に `zoom` を適用する |
| `shuffleArray(arr)` | Fisher-Yates in-place シャッフル |
| `escHtml(str)` | `&`/`<`/`>` のエスケープ（innerHTML 挿入前に必ず使用） |
| `showToast(msg)` | 2秒間トースト表示（タイマー重複防止あり） |
| `toggleAppMode()` / `applyAppMode()` / `loadAppMode()` | 単語⇔文法モードの切り替え・復元。`applyAppMode()` がビュー表示とヘッダーアイコンの出し分けを行う |
| `loadGrammarIfNeeded()` | `grammar.json` を初回のみキャッシュバスター付きで fetch（`grammarLoadPromise` で多重フェッチを防止）→ `renderGrammar()` |
| `renderGrammar()` / `renderGrammarExample(ex)` / `renderGrammarMemo(memo)` | `grammarData` から文法モードの HTML を構築（□レター・〈タグ〉・▶注釈・パステルバッジ付き暗記リストを描画）。暗記リスト自身に付く▶注釈（`memo.notes`）も例文と同じ `.grammar-note` 見た目で描画する |
| `maskBracketed(escapedText)` | 暗記リスト項目の `「...」` 部分だけを `.gmask` span で包む（複数箇所あればすべて個別にラップ）。`▶` 注釈にも適用する |
| `markCU(escapedText)` | 暗記リスト項目内の `「□C」`「□U」`（可算/不可算）を `.grammar-cu-badge` span に変換する。`maskBracketed()` より先に適用し、バッジごと `.gmask` で包まれるようにする |
| `toggleGrammarMask()` / `applyGrammarMask()` / `loadGrammarMask()` | 文法モードの訳・「」部分の表示/非表示切り替え・復元。`<html>` に `grammar-masked` クラスを付け外しし、モード変更時は個別展開状態をリセット |
| `openToc()` / `closeToc()` / `populateToc()` | 目次モーダルの `.open` クラス付け外しと一覧生成（初回のみ） |
| `scrollToLesson(n)` | 目次から該当講へ `scrollIntoView`、モーダルを閉じる |
| `openOnboarding()` / `closeOnboarding()` / `renderOnboardingStep()` | ？アイコンから開くオンボーディングモーダル。`appMode` に応じて `ONBOARDING_VOCAB`/`ONBOARDING_GRAMMAR` の内容を出し分ける |
| `onboardingNext()` / `onboardingPrev()` | オンボーディングのステップを±1。最終ステップでは「次へ」ボタンが「始める」に変わり、押すと閉じる |

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
  --header-grad-1: #1a1d27; /* ヘッダーグラデーション開始色 */
  --header-grad-2: #131620; /* ヘッダーグラデーション終了色 */
  --memo-bg:   #3d3564;   /* 文法モード：暗記グループ見出しバッジの背景（パステル） */
  --memo-text: #c9baff;   /* 文法モード：暗記グループ見出しバッジの文字色 */
  --correct-bg:   #244a3a; /* フラッシュチェック結果：正解行の背景（パステル） */
  --correct-text: #97e8bd; /* フラッシュチェック結果：正解行の文字色 */
  --incorrect-bg:   #4a2c2e; /* フラッシュチェック結果：不正解行の背景（パステル） */
  --incorrect-text: #f2acac; /* フラッシュチェック結果：不正解行の文字色 */
  --radius:    12px;      /* 標準角丸 */
  --radius-sm:  8px;      /* 小さい角丸（行セル・小ボタン） */
}
```

### ライトモード

`:root[data-theme="light"]` で上記トークンをすべて上書きする（`--accent`/`--accent2` はほぼ据え置き、背景・テキスト・赤系のみ明るい配色に変更）。JS の `toggleTheme()` が `document.documentElement` に `data-theme="light"|"dark"` をセットするだけで、CSS変数がカスケードして全体に反映される。

**重要**: `renderTable()` が生成するテーブルセルの inline style は `color:#e8eaf6` のようなハードコードされた16進色ではなく、必ず `color:var(--text)` / `color:var(--red)` を使うこと。ハードコードすると、テーマ切り替え時に再描画なしでは追従できなくなる（既存テーブルは再描画せず、var() の再評価だけで色が変わる設計）。

### ベーススタイル

- `* { box-sizing: border-box; margin: 0; padding: 0; }`
- `body`: `font-family: 'Outfit', 'Noto Sans JP', sans-serif; background: var(--bg); color: var(--text); padding-bottom: 60px;`
- ダーク/ライトの2テーマ（デフォルトはダーク）。`.header` の背景グラデーションも `--header-grad-1`/`-2` 経由でテーマに追従
- スクロールバー: width 4px、border-radius 2px（webkit のみ対応）

### 主要コンポーネントクラス

| クラス | 説明 |
|---|---|
| `.header` | sticky ヘッダー。`linear-gradient(135deg, var(--header-grad-1), var(--header-grad-2))`、z-index:100。タイトルと設定アイコンのみのシンプルな1行構成（上下 padding 16px で対称） |
| `.header-icons` | ヘッダー右端のアイコンボタン群（？アイコン・設定/目次アイコン・モード切替アイコン）をまとめる flex コンテナ。？アイコンは単語帳・文法モード共通で常に表示 |
| `.onboarding-icon` / `.onboarding-title` / `.onboarding-body` | オンボーディングモーダルの絵文字・見出し・本文（`ONBOARDING_VOCAB`/`ONBOARDING_GRAMMAR` の各ステップを描画） |
| `.icon-btn` | ヘッダー／モーダル内のアイコンボタン共通スタイル（opacity:0.85、hover で 1、active でスケールダウン）。QRボタンも設定モーダル内でこのクラスを使う |
| `.book-btn` / `.book-btn.active` | 冊子選択ボタン（単語1400・単語1900・熟語1000 の3つ）。`.active` で accent 背景 |
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
| `.modal-overlay` / `.modal-overlay.open` | モーダル背景（設定・フラッシュカード共通）。`.open` で `opacity:1; pointer-events:all` |
| `.modal` | モーダル本体（max-width:380px、`transform:translateY(20px→0)` でアニメーション） |
| `.settings-modal` | 設定モーダル用の `.modal` 修飾クラス。上下 margin と box-shadow を強めて「浮いている」見た目にする。閉じるボタンは持たず、オーバーレイタップで閉じる |
| `.modal-title-row` | 設定モーダル見出しと `.modal-title-actions`（QR・テーマ・文字サイズアイコン）を横並びにする flex コンテナ |
| `.modal-title` | 設定モーダルの見出しテキスト（15px, 700） |
| `.modal-title-actions` | QR・テーマ・文字サイズの3アイコンをまとめる flex コンテナ。すべて `.icon-btn` を使い QRボタンと同じさりげない見た目に揃える |
| `.modal-close` | モーダル閉じる×ボタン（26×26px 丸ボタン、hover で red 背景）。フラッシュカード・オンボーディングモーダルで使用（設定モーダルは廃止） |
| `.progress-bar` / `.progress-fill` | 進捗バー（accent→accent2 グラデーション） |
| `.flash-word` | フラッシュカードのメイン単語（最大 64px、JS でサイズ動的変更） |
| `.flash-meaning-wrap` | 答えのカバー付きコンテナ（タップでトグル） |
| `.flash-meaning-cover` / `.hidden` | 「タップして表示」カバー。`.hidden` で `display:none` |
| `.flash-speak-btn` | フラッシュカード内音声ボタン（48×48px、surface2 背景、flex 配置） |
| `.btn-next` | 「次へ」ボタン（flex:1、accent グラデーション）。オンボーディングの「次へ/始める」、フラッシュチェック結果画面の「閉じる」でも使用 |
| `.btn-prev` | 「◀戻る」ボタン（48px 固定、surface2 背景）。`disabled` 時は `opacity:0.35` |
| `.flash-answer-actions` / `.btn-incorrect` / `.btn-correct` | フラッシュカードの「✕ 不正解」「◯ 正解」ボタン行（`.btn-prev`/`.flash-speak-btn` の行の下）。押すと `flashResults` に記録して次のカードへ進む |
| `.flash-result-title` / `.flash-result-summary` | フラッシュチェック終了後の結果画面の見出しと正解/不正解数 |
| `.flash-result-list` / `.flash-result-item` | 結果一覧（`overflow-y:auto` でスクロール）。`.correct`/`.incorrect` 修飾クラスで `--correct-bg`/`--incorrect-bg` のパステル背景に分ける |
| `.flash-result-word` / `.flash-result-meaning` | 結果一覧の各行内の単語（Outfit）と意味（Noto Sans JP）表示 |
| `.qr-overlay` / `.qr-overlay.open` | QR モーダル背景（z-index:500、opacity トランジション） |
| `.qr-card` | QR モーダル本体（surface 背景、flex 縦並び） |
| `.toast` / `.toast.show` | トースト通知（fixed、bottom:24px、`translateY(80px→0)` アニメーション、z-index:2000） |
| `.empty-state` | テーブル空時の表示（中央寄せ、絵文字＋テキスト） |
| `.loading-note` | CSV/grammar.json 読み込み中テキスト |
| `.grammar-lesson` | 文法モードの講セクション。`id="lesson-N"` を持ち目次からの `scrollIntoView` 先になる（`scroll-margin-top` で sticky ヘッダー分オフセット） |
| `.grammar-section-title` | 節見出し（「1. 第1文型」等）。左ボーダーで強調 |
| `.grammar-example` | 例文カード全体 |
| `.grammar-example-head` / `.grammar-letter` / `.grammar-tag` | 見出し行。□の通しアルファベットをバッジ化した `.grammar-letter` と〈パターン名〉の `.grammar-tag` を横並びにする（タグがない例文はレターのみ）。文が短いとタグだけ次行に折り返してずれるため、例文本体（`.grammar-sentence`）とは別の行に分離している |
| `.grammar-sentence` | 例文本体。`display:block` で見出し行の下に独立した行として置く（幅いっぱいに折り返す） |
| `.grammar-rewrite` | ＝/→ で始まる書き換え文（`rewrites`）の表示行 |
| `.grammar-translation` / `.grammar-gloss` | 日本語訳と、"it = the dish" のような補足対応関係 |
| `.grammar-note` / `.grammar-note-arrow` / `.grammar-note-text` | ▶ で始まる注釈。`display:flex` で矢印を固定幅の flex item にし、注釈テキストが折り返しても左端が揃う（ぶら下げインデント） |
| `.grammar-memo` / `.grammar-memo-header` / `.memo-badge` / `.memo-header-suffix` | 暗記リストのカード。`.memo-badge` が〈見出し〉をパステルカラー（`--memo-bg`/`--memo-text`）のバッジにする |
| `.grammar-memo-list` | ○項目の箇条書き。`::before` に `border-radius:50%` の空 `div` 相当（em単位）を描画し、文字サイズに追従する丸にする（`list-style:none`）。560px 以上で2カラム |
| `.gmask` | 文法モードの訳・「」部分をタップで隠す/表示する要素。`grammar-masked` クラス下では `color:transparent; background:var(--red-dark)` で単語帳のマスクと同じ見た目にする。`.revealed` が付くと個別に表示される。`「」` 自体は隠さず、`maskBracketed()` が中身だけを `.gmask` で包む |
| `.grammar-cu-badge` | 「□C」「□U」（可算/不可算）の合字を、例文レターと同じ意匠の小さなバッジにする。独自の `color` を持つため `.gmask` の `color:transparent` が上書きされず、マスク中も判別できる |
| `.toc-list` / `.toc-item` / `.toc-num` | 目次モーダルの一覧・各講ボタン・講番号バッジ |

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
- `resetAll()` が戻るべきデフォルト値: book=`'1900'`、from=`1`、to=`100`、order=`ordered`、mask=`hide`、`tableSwapped=true`。処理の最後に `closeSettings()` を呼び設定モーダルを閉じる。
- `selectBook(book, silent=false)`: currentBook 更新後に必ず `clampRangeInputs()` を呼ぶ。`silent=true` のときは `saveSettings()` を呼ばない（`loadSettings()` からの呼び出し時に使用）。
- 冊子ごとの範囲上限は `BOOK_MAX` で一元管理。新しい冊子を追加するときはこのオブジェクトにエントリを追加するだけでよい。
- `generateTable()` は成功時のみ `closeSettings()` を呼ぶ（該当語がない場合はトーストを出してモーダルを開いたままにし、その場で範囲を直せるようにする）。
- `theme` のデフォルトは `'dark'`、`fontScale` のデフォルトは `3`、`grammarMaskMode` のデフォルトは `'show'`。すべて localStorage 未設定時のフォールバック値。
- テーマ切替ボタンは設定モーダルと目次モーダルの2箇所にあるため、`js-theme-btn` クラスで両方まとめて更新する（`id` は使わない）。新しくテーマボタンを追加する場合もこのクラスを付ける。
- QR・テーマ・文字サイズのアイコンは設定モーダルの見出し行にあるため、`openQR()` は必ず `closeSettings()` を先に呼ぶ（`.modal-overlay` の z-index は共通の1000なので、閉じないと設定モーダルの背景が QR モーダルの上に重なり閉じるボタンが押せなくなる）。
- 設定モーダルに閉じるボタン（×）は置かない。`#settingsOverlay` に `onclick="closeSettings()"`、モーダル本体（`.settings-modal`）に `onclick="event.stopPropagation()"` を付け、オーバーレイ部分をタップしたときだけ閉じるようにする（QRオーバーレイと同じパターン）。

### テーブル描画

- `renderTable()` は `tableSwapped` の値を読み取り、`swapped=true` なら左=単語(Outfit)・右=意味(Noto、maskable)。
- セルの色は `color:var(--text)` / `color:var(--red)` の inline style として埋め込む（ハードコード16進色は禁止。テーマ切り替え時に var() の再評価だけで追従させるため）。右セルは `rightStyle.replace('color:var(--text)', 'color:var(--red)')` で強制的に赤にする。
- マスク要素は `.mask-el` クラスの `<span>` で、`style="display:none"` / `display:block` を JS で切り替える（`visible` クラスは使わない）。背景色も `background:var(--red-dark)`。
- 音声ボタン（`.td-speak` 列）は常に4番目の列として追加し、マスクとは独立させる。
- 文字サイズは `#tableArea` 要素に `style.zoom` を設定して実現する（テーブル内容を再描画せずに済む）。`renderTable()`/`restoreTable()` は `#tableArea` の子要素を差し替えるだけなので、`zoom` は保持される。

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
target1000.csv        # Target 1000 熟語データ（no,word,meaning）
grammar.json           # 文法モードのデータ（全23講、講→節→例文/暗記ブロックの階層構造）
parse_grammar.py       # grammar.json 生成スクリプト（pdftotext -layout の出力テキストから変換）
apple-touch-icon.png  # iOS ホーム画面アイコン（180×180 px RGBA PNG）
qr.png                # QR コード画像（サイトURL→シェアモーダルで表示）
resize_icon.py        # アイコン作成用スクリプト（IMG_5804.png → apple-touch-icon.png）
gen_icon.py           # アイコン生成スクリプト（Python stdlib のみ、PIL 不使用）
CLAUDE.md             # 本ファイル
```

### 方針

- **新ファイルを作らない**: 機能追加はすべて `index.html` へのインライン追加で行う。JS ファイル・CSS ファイルの分離は行わない。
- **データファイルはCSVのまま**: JSON や DB への移行は行わない。ただし `grammar.json` は例外（講→節→例文/暗記ブロックという階層構造を持ち、CSV の単純な表形式では表現できないため）。
- **アイコン変更**: `apple-touch-icon.png` の更新は Python スクリプト（`resize_icon.py` or `gen_icon.py`）で行い、PIL/Pillow 等の外部ライブラリは使わない。
- **画像ファイル**: `qr.png` と `apple-touch-icon.png` のみ。スプライトシート・SVGスプライト等は使わない（SVG はインライン HTML に直接記述）。
- **`index.html` 内の構造**: `<style>` → `<body>` → `<script>` の順。スクリプトは `<body>` 末尾に2ブロック（アプリロジック + iOS ズーム無効化）。

### Git・デプロイ

- `main` ブランチが GitHub Pages として公開される。
- 機能ブランチは `main` から切る（`git checkout main && git pull` してから `git checkout -b <branch>`）。
- PR は squash merge でマージし、`main` にコミットが積まれる。
