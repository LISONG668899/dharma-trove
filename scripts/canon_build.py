# -*- coding: utf-8 -*-
"""
德格版《甘珠尔》《丹珠尔》网页自动生成
=====================================
把 esukhia 整理的德格版逐函 TXT（如 001_འདུལ་བ།_ཀ.txt）自动排版成网站页面，不用逐篇手改。

用法（在 E:\\dharma-trove 里运行）：
    python scripts/canon_build.py  <TXT 文件夹>  kangyur
    python scripts/canon_build.py  <TXT 文件夹>  tengyur

生成：
    docs/甘珠尔/index.md            二级目录：各部（藏文部名 + 中文）
    docs/甘珠尔/<部名>.md            三级目录：该部各函，函下列出每部经的藏文经名
    docs/甘珠尔/read.md              阅读页（只有一个，按 ?t=经号&p=分段 显示）
    docs/public/canon/kangyur/catalog.json        全部经目
    docs/public/canon/kangyur/<经号>/<分段>.json   经文正文（每段约两万个藏文字符）

TXT 里的记号怎么处理：
    [1b] [1b.3]     叶码、行码：一面（如 1b）排成一个自然段，段首用小字标出“函 叶码”；
                    行与行直接相连（原书换行常在一个音节中间，不能加空格）
    {T1} {T1-1}     经号（Toh）：{T1} 开始一部新经；{T1-1} 是经内的分品，只在分段时优先断在这里
    (原字,改字)     esukhia 的校勘：显示校正后的字
经名取法（依次试，取第一个像样的）：
    1. 梵名之后“བོད་སྐད་དུ།”（藏语名）后面的经名
    2. 卷首题记“……བཞུགས་སོ།”
    3. 卷首标题：开头第一句后面紧跟礼敬（……ཕྱག་འཚལ་ལོ）或“བམ་པོ་དང་པོ”“ལེའུ་དང་པོ”
    4. 卷末题记“……རྫོགས་སོ།”：取前面的经论名，去掉“སློབ་དཔོན་某某ཀྱིས་མཛད་པ”和译者题记
    5. 卷末任何“……ཞེས་བྱ་བ”
    6. 开头第一句（跳过礼敬、ན་མོ、咒语起头的句子）
    经名里的 # 号、开头多余的 ། ༄༅、结尾的“བཞུགས”都去掉。礼敬句、咒语、以“སོ/རོ/ཏོ”收尾的叙述句不当经名。

只重取经名、重排目录页（不用 TXT，用网站里已有的正文 JSON）：
    python scripts/canon_build.py  retitle  kangyur
    python scripts/canon_build.py  retitle  tengyur
"""
import json, os, re, sys, glob, shutil

COLL = {
    'kangyur': {'zh': '甘珠尔', 'bo': 'སྡེ་དགེ་བཀའ་འགྱུར།', 'about': '佛陀所说经、律、密续的藏文译本汇编'},
    'tengyur': {'zh': '丹珠尔', 'bo': 'སྡེ་དགེ་བསྟན་འགྱུར།', 'about': '印度历代论师所造论典与注疏的藏文译本汇编'},
}
# 各部中文名（没有列出的部，只显示藏文）
SEC_ZH = {
    'འདུལ་བ།': '律部', 'འབུམ།': '十万颂般若', 'ཉི་ཁྲི།': '二万五千颂般若', 'ཁྲི་བརྒྱད།': '一万八千颂般若',
    'ཁྲི་པ།': '一万颂般若', 'བརྒྱད་སྟོང་པ།': '八千颂般若', 'ཤེས་རབ་སྣ་ཚོགས།': '般若杂部', 'ཕལ་ཆེན།': '华严部',
    'དཀོན་བརྩེགས།': '宝积部', 'མདོ་སྡེ།': '经部', 'རྒྱུད་འབུམ།': '十万续部', 'རྙིང་རྒྱུད།': '旧译续部',
    'གཟུངས་འདུས།': '陀罗尼集', 'དྲི་མེད་འོད།': '时轮释·无垢光', 'དཀར་ཆག': '目录',
    # 丹珠尔
    'བསྟོད་ཚོགས།': '赞颂部', 'རྒྱུད།': '续部', 'ཤེར་ཕྱིན།': '般若部', 'དབུ་མ།': '中观部', 'མདོ་འགྲེལ།': '经释部',
    'སེམས་ཙམ།': '唯识部', 'མངོན་པ།': '对法部', 'སྐྱེས་རབས།': '本生部', 'སྤྲིང་ཡིག': '书翰部', 'ཚད་མ།': '量论部',
    'སྒྲ་མདོ།': '声明部', 'གསོ་རིག': '医方明部', 'བཟོ་རིག': '工巧明部', 'ཐུན་མོང་བ།': '共通部',
    'ཇོ་བོའི་ཆོས་ཆུང་།': '阿底峡小法集', 'སྣ་ཚོགས།': '杂部', 'ཕྲན་ཚེགས།': '杂部',
    'རྒྱུད་འགྲེལ།': '续释部', 'འཁྲི་ཤིང།': '如意藤',
}
# 同名的部在丹珠尔里意思不同
# 各部的通行次第（德格版，依东北目录 Toh 编号先后）。
# 甘珠尔：律、般若（十万、二万五千、一万八千、一万、八千、般若杂）、华严、宝积、经、续（十万续、旧译续、时轮释无垢光）、陀罗尼集、目录。
# 丹珠尔：赞颂、续释、般若、中观、经释、唯识、对法、律释、本生（含如意藤）、书翰、量论、声明、医方明及工巧、世间论典、杂部、目录。
SEC_ORDER = {
    'kangyur': ['འདུལ་བ།', 'འབུམ།', 'ཉི་ཁྲི།', 'ཁྲི་བརྒྱད།', 'ཁྲི་པ།', 'བརྒྱད་སྟོང་པ།', 'ཤེས་རབ་སྣ་ཚོགས།',
                'ཕལ་ཆེན།', 'དཀོན་བརྩེགས།', 'མདོ་སྡེ།', 'རྒྱུད་འབུམ།', 'རྙིང་རྒྱུད།', 'དྲི་མེད་འོད།', 'གཟུངས་འདུས།', 'དཀར་ཆག'],
    'tengyur': ['བསྟོད་ཚོགས།', 'རྒྱུད་འགྲེལ།', 'ཤེར་ཕྱིན།', 'དབུ་མ།', 'མདོ་སྡེ།', 'སེམས་ཙམ།', 'མངོན་པ།', 'འདུལ་བ།',
                'སྐྱེས་རབས།', 'འཁྲི་ཤིང།', 'སྤྲིང་ཡིག', 'ཚད་མ།', 'སྒྲ་མདོ།', 'གསོ་རིག', 'སྣ་ཚོགས།', 'དཀར་ཆག'],
}
# 跨两部开刻的经：一万颂般若（Toh 11）在德格版里从一万八千颂第三函（ག）后半开始，应归一万颂。
SEC_OF_TOH = {'kangyur': {'11': 'ཁྲི་པ།'}}
SEC_ZH_COLL = {'tengyur': {'མདོ་སྡེ།': '经释部', 'མངོན་པ།': '对法部', 'འདུལ་བ།': '律释部', 'དཀར་ཆག': '目录'}}
TARGET = 40000          # 每段大约多少个字符（Cloudflare 每个网站最多两万个文件，段不能太碎）
SHAD_END = re.compile(r'[།༎༑༔]\s*$')


def clean(s):
    s = re.sub(r'\(([^(),]*),([^(),]*)\)', r'\2', s)   # (原字,改字) → 改字
    s = re.sub(r'\{(?![TD]\d)([^}]*)\}', r'\1', s)       # 经号以外的花括号：只留文字
    return s


def read_volume(path):
    """逐行读一函，返回 [(叶面, 行文字)]，行文字里还保留 {T..} 记号"""
    out = []
    for line in open(path, encoding='utf-8-sig'):
        line = line.rstrip('\r\n')
        m = re.match(r'\[(\d+[ab])(?:\.\d+)?\](.*)', line)
        if not m:
            continue
        side, text = m.group(1), m.group(2)
        if text:
            out.append((side, clean(text)))
    return out


# ---------- 经名 ----------
def tidy(t):
    t = t.replace('#', '')
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'^[\s༄༅།༑༎༔་]+', '', t)
    t = re.sub(r'[\s།༑༎༔]+$', '', t)
    t = re.sub(r'\s*བཞུགས(?:་སོ)?་?$', '', t)
    return t.strip().rstrip('་') if t.endswith('་') and not t.endswith('ང་') else t.strip()

def clauses(s, n=6):
    """开头几句（按 shad 断开），去掉 ༄༅ 和空句"""
    out = []
    for c in re.split(r'[།༑༎༔]+', s[:2000]):
        c = c.replace('#', '').strip(' ༄༅་')
        if c:
            out.append(c)
        if len(out) >= n:
            break
    return out

HOMAGE = re.compile(r'ཕྱག་འཚལ་ལོ|བམ་པོ་དང་པོ|ལེའུ་དང་པོ|ཕྱག་བྱས')
AUTHOR = re.compile(r'(?:གྱིས|ཀྱིས|གིས|ཡིས)་?(?:མཛད|སྦྱར|བྱས|བཀོད|བསྡུས)|མཛད་པ$|ལོ་ཙཱ|ལོཙྪ|ལོ་ཙྪ|བསྒྱུར|ཞུས')

def ok(t):
    return t and len(t) >= 6 and len(t) <= 300

BAD_START = re.compile(r'^(?:ན་མོ|ཕྱག་འཚལ|དཀོན་མཆོག་གསུམ་ལ|རྒྱ་གར་གྱི་མཁན་པོ|ཞུ་ཆེན|འདི་སྐད་བདག་གིས)')

PROSE_END = re.compile(r'(?:^|་)(?:སོ|ངོ|རོ|ཏོ|དོ|ལོ)$|[^་]འོ$|ནུས་སོ|འགྱུར་རོ')

def good(t):
    return ok(t) and not BAD_START.search(t) and not HOMAGE.search(t) and not PROSE_END.search(t)

def end_title(tail):
    ms = list(re.finditer(r'(?:རྫོགས|ཚར)\s*་?\s*(?:སོ|སྷོ|རོ|ཏོ)', tail))
    if not ms:
        return None
    before = tail[:ms[-1].start()]
    cl = [c.strip(' ༄༅་') for c in re.split(r'[།༑༎]+', before)][-3:]
    for c in reversed(cl):
        if not c:
            continue
        # “སློབ་དཔོན་某某ཀྱིས་མཛད་པ + 经论名”：去掉前面的作者
        m = re.match(r'^.{2,80}?(?:གྱིས|ཀྱིས|གིས|ཡིས|པོས|བས|མས|ས)་?(?:མཛད|སྦྱར|བཀོད)་པ(?:འི་|་)(.{6,})$', c)
        if m and not AUTHOR.search(m.group(1)):
            c = m.group(1)
        if AUTHOR.search(c):
            # “经论名 + སློབ་དཔོན་某某ཀྱིས་མཛད་པ”同在一句：取作者前面的经论名
            m = re.search(r'^(.{6,}?)\s*(?:སློབ་དཔོན|མཁན་པོ|ཨཱ་ཙཱ་རྱ|རྣལ་འབྱོར་གྱི་དབང་ཕྱུག|པཎྜི་ཏ|བླ་མ་)', c)
            if m and not AUTHOR.search(m.group(1)):
                c = m.group(1)
            else:
                continue
        m = re.search(r'^(.*?)\s*[ཞཅཤ]ེས་བྱ་བ(?:་|$)', c)
        if m and len(m.group(1)) >= 4:
            # “……ཞེས་བྱ་བ་ཐེག་པ་ཆེན་པོའི་མདོ”这类，ཞེས་བྱ་བ 后面还有经名的，整句保留
            rest = c[m.end():]
            return c if re.match(r'[^་]*(?:མདོ|རྒྱུད|གཟུངས|ཆོས་ཀྱི་རྣམ་གྲངས|ལེའུ|རབ་ཏུ་བྱེད་པ|ཚིག་ལེའུར)', rest) else m.group(1)
        i = cl.index(c) if c in cl else -1
        if i > 0 and re.search(r'(?:དང|ལས)$', cl[i-1].strip()) and not AUTHOR.search(cl[i-1]):
            c = cl[i-1].strip() + '། ' + c
        return c
    return None

def find_title(body):
    flat = re.sub(r'\{[^}]*\}', '', body).replace('#', '')
    head = flat[:3000]
    tail = flat[-2000:]
    opens = bool(re.match(r'[\s།]*༄', head))   # 正文从“༄”起头，才是一部经论真正的开头
    cands = []
    # 1. 梵名之后的藏语名
    m = re.search(r'བོད་སྐད་དུ[།༑]\s*(.+?)[།༑]', head)
    if m: cands.append(m.group(1))
    # 2. 卷首题记“……བཞུགས་སོ”
    m = opens and re.match(r'[\s༄༅།༑]*([^།༑]{4,200}?)\s*བཞུགས(?:་སོ|་ལགས་སོ)?\s*[།༑]', head)
    if m: cands.append(m.group(1))
    # 3. 卷首标题：第一句之后紧接着礼敬、“第一卷”“第一品”
    cs = clauses(head)
    if opens and len(cs) >= 2 and HOMAGE.search(' '.join(cs[1:3])):
        cands.append(cs[0])
    # 4. 卷末题记“……རྫོགས་སོ”：取“རྫོགས”前一两句，跳过作者、译者一句
    t3 = end_title(tail)
    if t3: cands.append(t3)
    # 5. 卷末任何“……ཞེས་བྱ་བ”
    ms = list(re.finditer(r'([^།༑]{4,120}?)\s*[ཞཅཤ]ེས་བྱ་བ', tail))
    if ms: cands.append(ms[-1].group(1))
    for c in cands:
        t = tidy(c)
        if good(t):
            return t
    # 6. 开头第一句
    for c in cs:
        t = tidy(c)
        if good(t):
            return t[:80] + ('…' if len(t) > 80 else '')
    return tidy(flat[:60])


SYL_SPLIT = re.compile(r'[\u0F0B\u0F0C\u0F0D-\u0F14\u0F01-\u0F0A\u0F34\u0F3A-\u0F3D\s]+')
NSHARD = 256


def syllables(text):
    return [x for x in SYL_SPLIT.split(text) if x and re.search(r'[\u0F40-\u0FBC]', x)]


def shard_of(syl):
    """FNV-1a（按 UTF-16 编码单位），网页里的搜索程序用同一个算法"""
    h = 0x811c9dc5
    for ch in syl:
        for u in ([ord(ch)] if ord(ch) < 0x10000 else [0xD800 + ((ord(ch) - 0x10000) >> 10), 0xDC00 + ((ord(ch) - 0x10000) & 0x3FF)]):
            h ^= u
            h = (h * 0x01000193) & 0xFFFFFFFF
    return h % NSHARD


def b36(n):
    d = '0123456789abcdefghijklmnopqrstuvwxyz'
    s = ''
    while True:
        n, r = divmod(n, 36)
        s = d[r] + s
        if n == 0:
            return s


def build_index(data_dir, catalog):
    parts = []
    post = {}
    for e in catalog:
        for i in range(1, len(e['parts']) + 1):
            pid = len(parts)
            parts.append([e['t'], i])
            d = json.load(open(os.path.join(data_dir, e['t'], f'{i}.json'), encoding='utf-8'))
            seen = set()
            for _, txt in d['paras']:
                seen.update(syllables(txt))
            for syl in seen:
                post.setdefault(syl, []).append(pid)
    sdir = os.path.join(data_dir, 'search')
    os.makedirs(sdir, exist_ok=True)
    with open(os.path.join(sdir, 'parts.json'), 'w', encoding='utf-8') as fh:
        json.dump(parts, fh, separators=(',', ':'))
    shards = [dict() for _ in range(NSHARD)]
    for syl, ids in post.items():
        prev, out = 0, []
        for x in ids:
            out.append(b36(x - prev))
            prev = x
        shards[shard_of(syl)][syl] = ','.join(out)
    for i, sh in enumerate(shards):
        with open(os.path.join(sdir, f'{i}.json'), 'w', encoding='utf-8') as fh:
            json.dump(sh, fh, ensure_ascii=False, separators=(',', ':'))
    print(f'  检索索引：{len(post)} 个音节，{len(parts)} 个分段')


def write_pages(key, catalog, vols):
    c = COLL[key]
    secname = lambda sec: SEC_ZH_COLL.get(key, {}).get(sec) or SEC_ZH.get(sec, '')
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    page_dir = os.path.join(repo, 'docs', c['zh'])
    os.makedirs(page_dir, exist_ok=True)
    # ---------- 页面 ----------
    sec_order = []
    for no, sec, letter in vols:
        if sec not in sec_order:
            sec_order.append(sec)
    order = SEC_ORDER.get(key, [])
    first = list(sec_order)
    sec_order.sort(key=lambda x: (order.index(x) if x in order else len(order), first.index(x)))
    slug = lambda sec: re.sub(r'[།༎\s]', '', sec)

    lines = ['---', f"title: {c['zh']}", 'aside: false', 'sidebar: false', '---', '', f"# {c['zh']}", '',
             f"<p class=\"dt-bo-title notranslate\" translate=\"no\">{c['bo']}</p>", '',
             f"德格版《{c['zh']}》，即{c['about']}。下列各部，点进去可以看到每一函所收的经论，点经论名即可阅读藏文原文。阅读时选中一段藏文，可以请机器译成白话；目录上的藏文名称也一样可以选中翻译。", '',
             '<div class="dt-secgrid notranslate" translate="no">']
    for sec in sec_order:
        nvol = sum(1 for v in vols if v[1] == sec)
        nt = sum(1 for e in catalog if e['sec'] == sec)
        zh = secname(sec)
        lines.append(f'<a class="dt-secbtn" href="/{c["zh"]}/{slug(sec)}"><span class="dt-bo">{sec}</span>'
                     + (f'<span class="dt-sec-zh">{zh}</span>' if zh else '')
                     + f'<span class="dt-sec-n">{nvol} 函 · {nt} 部</span></a>')
    lines.append('</div>')
    open(os.path.join(page_dir, 'index.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

    for sec in sec_order:
        zh = secname(sec)
        L = ['---', f"title: {zh or sec}", 'aside: false', 'sidebar: false', '---', '',
             f'<p class="dt-crumb"><a href="/{c["zh"]}/">{c["zh"]}</a></p>', '', f"# {zh or sec}", '', f'<p class="dt-bo-title notranslate" translate="no">{sec}</p>', '']
        for no, s2, letter in vols:
            if s2 != sec:
                continue
            L.append(f'<h2 class="dt-vol notranslate" translate="no"><span class="dt-bo">{letter or sec}</span><span class="dt-vol-no">第 {int(no)} 函</span></h2>')
            L.append('<ol class="dt-texts notranslate" translate="no">')
            for e in catalog:
                for pi, (vno, start) in enumerate(e['parts'], 1):
                    if vno != no:
                        continue
                    first_in_vol = pi == 1 or e['parts'][pi - 2][0] != no
                    if not first_in_vol:
                        continue
                    cont = pi > 1
                    toh = f'<span class="dt-toh">Toh {e["toh"]}</span>' if e['toh'] else ''
                    L.append(f'<li><a href="/{c["zh"]}/read?t={e["t"]}&p={pi}"><span class="dt-bo">{e["title"]}</span></a>'
                             f'{toh}<span class="dt-folio-ref">{start}{"（续）" if cont else ""}</span></li>')
            L.append('</ol>')
            L.append('')
        open(os.path.join(page_dir, f'{slug(sec)}.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

    open(os.path.join(page_dir, 'read.md'), 'w', encoding='utf-8').write(
        f"---\ntitle: {c['zh']}\naside: false\nsidebar: false\nprev: false\nnext: false\n---\n\n<CanonReader coll=\"{key}\" />\n")


def vols_from_catalog(catalog):
    """旧版没有存 vols.json 时，从经目里各段的起点推出各函：函的部别取该函第一段所属经论的部别"""
    seen = {}
    for e in catalog:
        for vno, start in e['parts']:
            if vno not in seen:
                seen[vno] = (vno, e['sec'], start.split(' ')[0] if ' ' in start else '')
    return [seen[k] for k in sorted(seen)]


def retitle(key):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(repo, 'docs', 'public', 'canon', key)
    catalog = json.load(open(os.path.join(data_dir, 'catalog.json'), encoding='utf-8'))
    vp = os.path.join(data_dir, 'vols.json')
    vols = [tuple(v) for v in json.load(open(vp, encoding='utf-8'))] if os.path.exists(vp) else vols_from_catalog(catalog)
    n = 0
    for e in catalog:
        rd = lambda i: ''.join(p[1] for p in json.load(open(os.path.join(data_dir, e['t'], f'{i}.json'), encoding='utf-8'))['paras'])
        head = rd(1)
        body = head if len(e['parts']) == 1 else head[:6000] + rd(len(e['parts']))[-6000:]
        t = find_title(body)
        if t != e['title']:
            n += 1
            e['title'] = t
    with open(os.path.join(data_dir, 'catalog.json'), 'w', encoding='utf-8') as fh:
        json.dump(catalog, fh, ensure_ascii=False, separators=(',', ':'))
    if not os.path.exists(vp):
        with open(vp, 'w', encoding='utf-8') as fh:
            json.dump(vols, fh, ensure_ascii=False)
    write_pages(key, catalog, vols)
    print(f"{COLL[key]['zh']}：重取经名，改了 {n} 部；目录页已重排")


def build(src, key):
    c = COLL[key]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    page_dir = os.path.join(repo, 'docs', c['zh'])
    data_dir = os.path.join(repo, 'docs', 'public', 'canon', key)
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(page_dir, exist_ok=True)

    # 空文件（如丹珠尔资料里的 213_དཀར་ཆག.txt 是 0 字节）不列入目录
    files = sorted(f for f in glob.glob(os.path.join(src, '*.txt')) if os.path.getsize(f) > 0)
    texts = {}          # 经号 → {id, sec, paras:[(函字, 叶面, 文字, 是否分品起点)]}
    order = []
    vols = []           # [(序号, 部, 函字)]
    cur = None
    for f in files:
        name = os.path.splitext(os.path.basename(f))[0]
        parts = name.split('_')
        no, sec = parts[0], parts[1]
        letter = parts[2] if len(parts) > 2 else ''
        vols.append((no, sec, letter))
        # 整函没有经号：一般是上一部经的续函；只有目录卷（或开头第一函）自成一部
        if not re.search(r'\{[TD]\d', open(f, encoding='utf-8-sig').read()) and (cur is None or sec == 'དཀར་ཆག'):
            cur = 'x' + no
            texts[cur] = {'id': cur, 'toh': '', 'sec': sec, 'paras': []}
            order.append(cur)
        side_buf = {}                          # 同一叶面的行合成一段
        for side, line in read_volume(f):
            pieces = re.split(r'(\{[TD]\d[^}]*\})', line)
            for pc in pieces:
                if not pc:
                    continue
                m = re.fullmatch(r'\{[TD](\d[^}-]*)(-[^}]*)?\}', pc)
                if m:
                    if not m.group(2):         # {T12} 新的一部经
                        cur = m.group(1)
                        if cur not in texts:
                            texts[cur] = {'id': cur, 'toh': cur, 'sec': sec, 'paras': []}
                            order.append(cur)
                        side_buf = {}
                    else:                      # {T12-3} 分品：在这里另起一段
                        side_buf = {}
                        side_buf['brk'] = True
                    continue
                if cur is None:                # 函首“某某函在此”之类，不属于任何经
                    continue
                t = texts[cur]
                k = (no, side)
                if t['paras'] and t['paras'][-1][4] == k and not side_buf.get('brk'):
                    t['paras'][-1][2] += pc
                else:
                    t['paras'].append([letter, side, pc, bool(side_buf.get('brk')), k])
                    side_buf = {}

    catalog = []
    for tid in order:
        t = texts[tid]
        paras = [p for p in t['paras'] if p[2].strip()]
        if not paras:
            continue
        body = ''.join(p[2] for p in paras)
        title = find_title(body)
        # 分段：累计约 TARGET 字后，在下一个分品处或下一面处断开
        chunks, buf, n = [], [], 0
        for p in paras:
            if buf and (n >= TARGET or (p[3] and n >= TARGET * 0.4)):
                chunks.append(buf); buf, n = [], 0
            buf.append(p); n += len(p[2])
        if buf:
            chunks.append(buf)
        os.makedirs(os.path.join(data_dir, tid), exist_ok=True)
        part_meta = []
        for i, ch in enumerate(chunks, 1):
            out = {'t': tid, 'p': i, 'paras': [[f'{p[0]} {p[1]}'.strip(), p[2].strip()] for p in ch]}
            with open(os.path.join(data_dir, tid, f'{i}.json'), 'w', encoding='utf-8') as fh:
                json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
            part_meta.append([ch[0][4][0], f'{ch[0][0]} {ch[0][1]}'.strip()])   # 段起点：函序号、函字+叶面
        sec_t = SEC_OF_TOH.get(key, {}).get(t['toh'], t['sec'])
        catalog.append({'t': tid, 'toh': t['toh'], 'title': title, 'sec': sec_t, 'parts': part_meta})

    with open(os.path.join(data_dir, 'catalog.json'), 'w', encoding='utf-8') as fh:
        json.dump(catalog, fh, ensure_ascii=False, separators=(',', ':'))

    # ---------- 藏文全文检索索引 ----------
    # 按音节（以“་”“།”等分开）建倒排索引：音节 → 出现过它的正文分段编号。
    # 分成 256 个小文件，搜索时只下载查询里那几个音节所在的小文件，再到候选分段里逐字核对。
    build_index(data_dir, catalog)

    with open(os.path.join(data_dir, 'vols.json'), 'w', encoding='utf-8') as fh:
        json.dump(vols, fh, ensure_ascii=False)
    write_pages(key, catalog, vols)

    total = sum(len(e['parts']) for e in catalog)
    print(f"{c['zh']}：{len(set(v[1] for v in vols))} 部，{len(vols)} 函，{len(catalog)} 部经论，{total} 个正文分段")


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'retitle' and sys.argv[2] in COLL:
        retitle(sys.argv[2])
        sys.exit(0)
    if len(sys.argv) != 3 or sys.argv[2] not in COLL:
        print(__doc__)
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
