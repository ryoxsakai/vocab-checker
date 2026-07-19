import re, json

# pdftotext -layout の出力テキストを想定（例: pdftotext -layout grammar.pdf grammar_full.txt）
SRC = 'grammar_full.txt'
OUT = 'grammar.json'

with open(SRC, encoding='utf-8') as f:
    raw_lines = f.read().split('\n')

NOISE_EXACT = {
    '超特急英文法 攻略ポイント集 / 担当：酒井',
    '許可のない複製や再販は',
    ' 禁じられています。',
    'Copyright © All Rights Reserved',
    'name',
}
PAGE_NUM_RE = re.compile(r'^\s*—\s*\d+\s*—\s*$')
DOT_GARBAGE_RE = re.compile(r'^[．\s]+$')
LESSON_RE = re.compile(r'^第\s*(\d+)\s*講\s*(\S.*)$')
SECTION_RE = re.compile(r'^(\d+)\.\s*(\S.*)$')
EXAMPLE_RE = re.compile(r'^□([Ａ-Ｚ])\s*(.+)$')
BARE_BRACKET_RE = re.compile(r'^〈([^〈〉]+)〉\s*(.*)$')
TRAILING_BRACKET_RE = re.compile(r'〈([^〈〉]+)〉\s*$')
JAPANESE_RE = re.compile(r'[぀-ゟ゠-ヿ一-鿿]')
NOTE_MARK_RE = re.compile(r'^[▶❶❷❸❹❺❻❼❽❾❿]')
GLOSS_TAIL_RE = re.compile(r'\s{4,}([A-Za-z][A-Za-z\s]{0,25}[＝=]\s*[A-Za-z][A-Za-z\s]{0,30})$')

def indent_len(line):
    return len(line) - len(line.lstrip(' '))

def split_tag(text):
    m = TRAILING_BRACKET_RE.search(text)
    if m:
        return text[:m.start()].strip(), m.group(1)
    return text.strip(), ''

def classify_line(stripped):
    # 末尾の〈タグ〉を切り離した上で、残りが日本語訳の行か英語の書き換え文かを判定する

    body, tag = split_tag(stripped)
    if JAPANESE_RE.search(body):
        gloss = ''
        gm = GLOSS_TAIL_RE.search(body)
        if gm and not JAPANESE_RE.search(gm.group(1)):
            gloss = gm.group(1).strip()
            body = body[:gm.start()].strip()
        return 'ja', body, tag, gloss
    return 'en', body, tag, ''

lessons = []
cur_lesson = None
cur_section = None
cur_example = None
cur_memo = None

def flush_example():
    global cur_example
    if cur_example is not None and cur_section is not None:
        cur_example.pop('_phase', None)
        cur_example['type'] = 'example'
        cur_section['content'].append(cur_example)
    cur_example = None

def flush_memo():
    global cur_memo
    if cur_memo is not None and cur_section is not None:
        cur_section['content'].append({'type': 'memo', **cur_memo})
    cur_memo = None

def ensure_section():
    global cur_section
    if cur_section is None and cur_lesson is not None:
        cur_section = {'number': '', 'title': '', 'content': []}
        cur_lesson['sections'].append(cur_section)

def new_example(letter, rest):
    sentence, tag = split_tag(rest)
    return {
        'letter': letter, 'sentence': sentence, 'tag': tag,
        'rewrites': [], 'translation': [], 'gloss': [], 'notes': [],
        '_phase': 'pre_translation',
    }

for raw in raw_lines:
    line = raw.rstrip()
    stripped = line.strip()

    if stripped == '':
        continue
    if stripped in NOISE_EXACT or line in NOISE_EXACT:
        continue
    if PAGE_NUM_RE.match(line):
        continue
    if DOT_GARBAGE_RE.match(stripped):
        continue

    m = LESSON_RE.match(stripped)
    if m:
        flush_example(); flush_memo()
        cur_lesson = {'number': int(m.group(1)), 'title': m.group(2).strip(), 'sections': []}
        lessons.append(cur_lesson)
        cur_section = None
        continue

    ind = indent_len(line)

    if ind == 0:
        m = SECTION_RE.match(stripped)
        if m and cur_lesson is not None:
            flush_example(); flush_memo()
            cur_section = {'number': m.group(1), 'title': m.group(2).strip(), 'content': []}
            cur_lesson['sections'].append(cur_section)
            continue

    if ind == 0:
        m = EXAMPLE_RE.match(stripped)
        if m:
            flush_example(); flush_memo()
            ensure_section()
            cur_example = new_example(m.group(1), m.group(2))
            continue

    if ind == 0:
        m = BARE_BRACKET_RE.match(stripped)
        if m:
            flush_example(); flush_memo()
            ensure_section()
            cur_memo = {'header': m.group(1), 'headerSuffix': m.group(2).strip(), 'items': [], 'notes': []}
            continue

    # ---- 現在の例文ブロックに属する行 ----
    if cur_example is not None:
        if cur_example['_phase'] in ('pre_translation', 'translation'):
            if NOTE_MARK_RE.match(stripped):
                cur_example['notes'].append(stripped[1:].strip())
                cur_example['_phase'] = 'notes'
                continue
            kind, body, tag, gloss = classify_line(stripped)
            if kind == 'ja':
                cur_example['translation'].append(body)
                if gloss:
                    cur_example['gloss'].append(gloss)
                cur_example['_phase'] = 'translation'
            else:
                cur_example['rewrites'].append({'sentence': body, 'tag': tag})
            continue
        else:  # ▶ノート段階
            if NOTE_MARK_RE.match(stripped):
                cur_example['notes'].append(stripped[1:].strip())
            else:
                if cur_example['notes']:
                    cur_example['notes'][-1] += ' ' + stripped
            continue

    # ---- 現在の暗記ブロックに属する行 ----
    if cur_memo is not None:
        if NOTE_MARK_RE.match(stripped):
            # ○箇条書きのあとに続く▶注釈は暗記ブロック側の notes に入れる（項目末尾に混ぜない）
            cur_memo['notes'].append(stripped[1:].strip())
            continue
        idx = stripped.find('○')
        if idx == -1:
            if cur_memo['notes']:
                cur_memo['notes'][-1] += ' ' + stripped
            elif cur_memo['items']:
                sep = '' if stripped.startswith('「') else ' '
                cur_memo['items'][-1] += sep + stripped
        else:
            pre = stripped[:idx].strip()
            if pre:
                if cur_memo['notes']:
                    cur_memo['notes'][-1] += ' ' + pre
                elif cur_memo['items']:
                    sep = '' if pre.startswith('「') else ' '
                    cur_memo['items'][-1] += sep + pre
            rest = stripped[idx:]
            parts = re.split(r'○\s*', rest)
            for p in parts:
                p = p.strip()
                if p:
                    cur_memo['items'].append(p)
        continue

    # ---- 例文・暗記ブロックのどちらにも属さない孤立した○箇条書き ----
    if '○' in stripped:
        ensure_section()
        if cur_memo is None:
            cur_memo = {'header': '', 'headerSuffix': '', 'items': [], 'notes': []}
        idx = stripped.find('○')
        pre = stripped[:idx].strip()
        if pre and cur_memo['items']:
            sep = '' if pre.startswith('「') else ' '
            cur_memo['items'][-1] += sep + pre
        rest = stripped[idx:]
        parts = re.split(r'○\s*', rest)
        for p in parts:
            p = p.strip()
            if p:
                cur_memo['items'].append(p)
        continue

flush_example(); flush_memo()

# 原本PDFの「A ↔ B」の↔記号は pdftotext で抽出できず空白の連続になるため復元する
GAP_ARROW_RE = re.compile(r'^(\S+)\s{2,}(\S+)$')
for l in lessons:
    for s in l['sections']:
        for it in s['content']:
            if it['type'] != 'memo':
                continue
            suf = it.get('headerSuffix', '')
            m = GAP_ARROW_RE.match(suf.strip('「」'))
            if m and '→' not in suf and '←' not in suf:
                it['headerSuffix'] = f'「{m.group(1)} ↔ {m.group(2)}」'

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(lessons, f, ensure_ascii=False, separators=(',', ':'))

print('lessons:', len(lessons))
all_content = [it for l in lessons for s in l['sections'] for it in s['content']]
total_examples = sum(1 for it in all_content if it['type'] == 'example')
total_memo = sum(1 for it in all_content if it['type'] == 'memo')
print('examples:', total_examples, 'memo blocks:', total_memo)

# 検証: 訳が空になっている例文がないか確認
empty_tr = [(l['number'], s['number'], it['letter']) for l in lessons for s in l['sections'] for it in s['content'] if it['type'] == 'example' and not it['translation']]
print('examples with empty translation:', len(empty_tr), empty_tr)
