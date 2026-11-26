# -*- coding: utf-8 -*-
"""
乾隆大藏经（龙藏）TXT → 网站目录与阅读数据，全部自动生成，不必逐篇编辑。

用法：python scripts/qianlong_build.py <乾隆大藏经TXT版 文件夹>

生成：
  docs/乾隆大藏经/index.md          十七部类，一行两个豆腐块
  docs/乾隆大藏经/<部类>.md          该部类所收各经，按龙藏原编号（第几部）排列
  docs/乾隆大藏经/read.md            阅读页（<QianlongReader />）
  docs/public/canon/qianlong/catalog.json
  docs/public/canon/qianlong/<经号>/<分册>.json

排序依据：每个 TXT 第一行都写着“某部·第0011部……”，这就是龙藏本来的编次
（第1部《大般若经》到第1669部），部类的先后也由此而来：
大乘经（般若、宝积、大集、华严、涅槃、五大部外重译、单译）→ 小乘经（阿含、单译）
→ 宋元入藏诸大小乘经 → 大乘律 → 小乘律 → 大乘论 → 小乘论 → 宋元续入藏诸论
→ 西土圣贤撰集 → 此土著述。
一部经分成几个 TXT 的（如《大般若经》每十卷一个文件），按文件名里的卷次接续，
“目录”文件放在最前。
"""
import glob
import json
import os
import re
import shutil
import sys

SRC = sys.argv[1]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs', '乾隆大藏经')
DATA = os.path.join(ROOT, 'docs', 'public', 'canon', 'qianlong')
NAME = '乾隆大藏经'

# 部类分组（只用于部类页顶上的一句说明）
GROUP = {
    '大乘般若部': '大乘经', '大乘宝积部': '大乘经', '大乘大集部': '大乘经', '大乘华严部': '大乘经',
    '大乘涅槃部': '大乘经', '大乘五大部外重译经': '大乘经', '大乘单译经': '大乘经',
    '小乘阿含部': '小乘经', '小乘单译经': '小乘经', '宋元入藏诸大小乘经': '宋元入藏经',
    '大乘律': '律', '小乘律': '律', '大乘论': '论', '小乘论': '论', '宋元续入藏诸论': '论',
    '西土圣贤撰集': '杂藏', '此土著述': '杂藏',
}

CN = {'零': 0, '〇': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}


def cn2int(s):
    """一百 → 100，六百 → 600，三十 → 30，十二 → 12"""
    total, num = 0, 0
    for ch in s:
        if ch in CN:
            num = CN[ch]
        elif ch == '十':
            total += (num or 1) * 10; num = 0
        elif ch == '百':
            total += (num or 1) * 100; num = 0
        elif ch == '千':
            total += (num or 1) * 1000; num = 0
    return total + num


def read(f):
    b = open(f, 'rb').read()
    try:
        t = b.decode('utf-8')
    except UnicodeDecodeError:
        t = b.decode('gb18030', errors='replace')
    return t.lstrip('﻿').replace('\r', '').split('\n')


HEAD = re.compile(r'^v*(?:佛说)?(.+?)[·、]?第(\d+)部(.*)$')
TITLE = re.compile(r'^(.+?)([一二三四五六七八九十百千零〇两]+卷)(（[^）]*）|\([^)]*\))?(.*)$')
JUAN = re.compile(r'卷(?:第*([一二三四五六七八九十百千零〇]+)(之?[上中下])?|([上中下]))(?:\(.*\)|（.*）)?$')
BYLINE = re.compile(r'(译|譯|撰|述|造|集|制|製|注|註|解|编|編|录|錄|说|說|书|書|作|序|颂|頌|疏|记|記)$')
IND = '　'


def split(L):
    """去掉第一行题记、两行网页残留，以及正文前重复的一份目录；去掉文末“上一部/下一部”。"""
    i = 1
    while i < len(L) and L[i].startswith('·'):
        i += 1
    j = i
    while j < len(L) and L[j].strip() and not L[j].startswith(IND):
        j += 1
    block = L[i:j]
    start = i
    for k in range(1, len(block)):
        if block[k] == block[0]:
            start = i + k
            break
    body = L[start:]
    while body and (not body[-1].strip() or body[-1].startswith(('上一部', '下一部', '乾隆大藏经·'))):
        body.pop()
    return body


def blocks(body):
    """
    正文排成几种块：
      j  卷名（如“大智度论卷第一”），阅读页可跳到某一卷
      h  其他标题（经名、品名、序名）
      b  译者、撰者一行
      p  段落（原文每段开头两个全角空格，网页上用首行缩进代替）
      v  偈颂（几行连在一起不空行的，保留分行）
      k  注疏里顶格引出的经文（不缩进，字色稍深）
    """
    out = []
    para = []

    def flush():
        if not para:
            return
        lines = [x.strip(IND + ' \t') for x in para]
        lines = [x for x in lines if x]
        if not lines:
            para.clear(); return
        if len(lines) == 1:
            out.append(['p', lines[0]])
        else:
            # 几行连写：偈颂保留分行；散文被硬换行的（每行都很长）就接成一段
            if all(len(x) <= 40 for x in lines):
                out.append(['v', '\n'.join(x.replace(IND * 2, IND) for x in lines)])
            else:
                out.append(['p', ''.join(lines)])
        para.clear()

    for raw in body:
        s = raw.rstrip()
        if not s.strip():
            flush(); continue
        if not s.startswith(IND) and not s.startswith(' '):
            flush()
            t = s.strip()
            if JUAN.search(t):
                out.append(['j', t])
            elif len(t) <= 40 and BYLINE.search(t) and out and out[-1][0] in 'jh':
                out.append(['b', t])
            elif len(t) > 40 or t[-1] in '。？！；：”」』':
                # 不缩进的长行：注疏里顶格引出的经文、论文，排成不缩进的一段
                out.append(['k', t])
            else:
                out.append(['h', t])
            continue
        para.append(s)
    flush()
    return out


MAX_CHARS = 150000   # 一个分册太长（手机上载入慢）时，在卷与卷之间切开


def juan_tag(t):
    """“大智度论卷第十一” → “11”，“法华文句记卷第一上” → “1上”，“卷下” → “下”"""
    m = JUAN.search(t)
    if not m:
        return ''
    if m.group(3):
        return m.group(3)
    return str(cn2int(m.group(1))) + (m.group(2) or '').lstrip('之')


def cut(bl):
    """太长的分册按卷切成几册，返回 [(blocks, 标签或空)]。"""
    size = sum(len(x[1]) for x in bl)
    if size <= MAX_CHARS * 1.3:
        return [(bl, '')]
    out, cur, n = [], [], 0
    for b in bl:
        if b[0] == 'j' and n >= MAX_CHARS and cur:
            out.append(cur); cur, n = [], 0
        cur.append(b); n += len(b[1])
    if cur:
        out.append(cur)
    if len(out) == 1:
        return [(bl, '')]
    res = []
    for c in out:
        js = [juan_tag(x[1]) for x in c if x[0] == 'j']
        js = [j for j in js if j]
        label = ('卷' + (js[0] if len(js) == 1 else f'{js[0]}～{js[-1]}')) if js else ''
        res.append((c, label))
    return res


def drop_toc(bl):
    """分册开头若是一串卷名、品名（正文前重复的目录），只留最后一个卷名起的部分。"""
    f = next((i for i, b in enumerate(bl) if b[0] in 'pvk'), len(bl))
    js = [i for i in range(f) if bl[i][0] == 'j']
    if len(js) >= 2:
        return bl[js[-1]:]
    return bl


def part_order(fname):
    base = os.path.basename(fname)
    if base.startswith('a') and '目录' in base:
        return -1
    m = re.search(r'第(\d+)卷', base)
    return int(m.group(1)) if m else 0


def part_label(fname, n_parts):
    base = os.path.basename(fname)
    if base.startswith('a') and '目录' in base:
        return '目录'
    m = re.search(r'第(\d+)卷[～~\-－至]+第(\d+)卷', base)
    if m:
        return f'卷{int(m.group(1))}～{int(m.group(2))}'
    return '全文' if n_parts == 1 else '正文'


def main():
    files = sorted(glob.glob(os.path.join(SRC, '**', '*.txt'), recursive=True))
    works = {}      # (部类, 部号) → dict
    skipped = []
    for f in files:
        L = read(f)
        if len(L) < 3 or not ''.join(L).strip():
            skipped.append(os.path.relpath(f, SRC)); continue
        if os.path.basename(f).startswith('a') and '目录' in os.path.basename(f):
            # 《大般若经》《大宝积经》各有一个“目录”TXT，只是卷名、品名的清单，
            # 不能点、又和正文重复；改由阅读页的“卷目”（可点）代替
            continue
        sec = os.path.relpath(f, SRC).split(os.sep)[0]
        m = HEAD.match(L[0].strip())
        if m:
            no, rest = int(m.group(2)), m.group(3)
        else:
            # 第一行缺“·”的（如“大乘般若部第0002部……”）已由上式兼容；仍不合的放到本部类最后
            no, rest = 99999, L[0].strip()
        key = (sec, no)
        w = works.setdefault(key, {'sec': sec, 'no': no, 'files': [], 'head': rest})
        w['files'].append(f)
        if '目录' not in os.path.basename(f) and len(rest) > len(w['head']):
            pass

    # 目录 TXT 没有第一行题记时，归到同一文件夹的经
    catalog = []
    for (sec, no), w in sorted(works.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        w['files'].sort(key=part_order)
        # 题名：取正文文件（非目录）的题记
        head = ''
        for f in w['files']:
            if '目录' in os.path.basename(f):
                continue
            m = HEAD.match(read(f)[0].strip())
            if m:
                head = m.group(3); break
        head = head or w['head']
        m = TITLE.match(head)
        if m:
            title, juan, by = m.group(1), m.group(2), m.group(4)
        else:
            title, juan, by = os.path.splitext(os.path.basename(w['files'][0]))[0], '', ''
        title = re.sub(r'[（(][^）)]*[）)]$', '', title).strip('·· ')
        title = re.sub(r'卷$', '', title)
        by = by.strip()
        t = str(no)
        catalog.append({'t': t, 'no': no, 'title': title, 'juan': juan, 'by': by, 'sec': sec, 'files': w['files']})

    # 同一部类里编号相同、却是不同的经（极少）：加后缀区分
    seen = {}
    for e in catalog:
        if e['t'] in seen:
            seen[e['t']] += 1
            e['t'] = f"{e['t']}-{seen[e['t']]}"
        else:
            seen[e['t']] = 1

    if os.path.isdir(DATA):
        shutil.rmtree(DATA)
    os.makedirs(DATA)
    out_cat = []
    total_parts = 0
    for e in catalog:
        n = len(e['files'])
        parts = []
        os.makedirs(os.path.join(DATA, e['t']))
        chunks = []
        for f in e['files']:
            bl = drop_toc(blocks(split(read(f))))
            label = part_label(f, n)
            for k, (sub, sub_label) in enumerate(cut(bl)):
                chunks.append((sub, sub_label or label))
        if len(chunks) == 1 and chunks[0][1] == '正文':
            chunks = [(chunks[0][0], '全文')]
        for p, (bl, label) in enumerate(chunks, 1):
            with open(os.path.join(DATA, e['t'], f'{p}.json'), 'w', encoding='utf-8') as fp:
                json.dump({'t': e['t'], 'p': p, 'blocks': bl}, fp, ensure_ascii=False, separators=(',', ':'))
            parts.append(label)
            total_parts += 1
        # 卷目：每卷在第几册、第几块，以及紧跟的品名；多册的经单独存一个 toc.json，阅读页可直接点到任一卷
        toc = []
        for p, (bl, label) in enumerate(chunks, 1):
            for i, b in enumerate(bl):
                if b[0] == 'j':
                    pin = bl[i + 1][1] if i + 1 < len(bl) and bl[i + 1][0] == 'h' else ''
                    toc.append([p, i, b[1], pin[:40]])
        if len(chunks) > 1 and toc:
            with open(os.path.join(DATA, e['t'], 'toc.json'), 'w', encoding='utf-8') as fp:
                json.dump(toc, fp, ensure_ascii=False, separators=(',', ':'))
        out_cat.append({'t': e['t'], 'no': e['no'], 'title': e['title'], 'juan': e['juan'],
                        'by': e['by'], 'sec': e['sec'], 'parts': parts, 'toc': 1 if (len(chunks) > 1 and toc) else 0})
    with open(os.path.join(DATA, 'catalog.json'), 'w', encoding='utf-8') as fp:
        json.dump(out_cat, fp, ensure_ascii=False, separators=(',', ':'))

    # ---------- 页面 ----------
    secs = []
    for e in out_cat:
        if e['sec'] not in secs:
            secs.append(e['sec'])
    # 部类按各自最小编号排先后（即龙藏原次第）
    secs.sort(key=lambda s: min(x['no'] for x in out_cat if x['sec'] == s))

    if os.path.isdir(DOCS):
        shutil.rmtree(DOCS)
    os.makedirs(DOCS)

    def juan_n(e):
        return cn2int(e['juan'].rstrip('卷')) if e['juan'] else 0

    L = ['---', f'title: {NAME}', 'aside: false', 'sidebar: false', 'prev: false', 'next: false', '---', '', f'# {NAME}', '',
         '《乾隆大藏经》，又称《龙藏》，清雍正十一年（1733）开雕，乾隆三年（1738）完成，'
         '共收经、律、论及中土撰述一千六百六十九部。下列各部类按龙藏原有的编次排列，'
         '点进去可以看到所收各经，点经名即可阅读原文。阅读时可以选中文字划线收藏，'
         '也可以随时切换简体、繁体。', '',
         '<div class="dt-secgrid dt-secgrid-2">']
    for s in secs:
        es = [x for x in out_cat if x['sec'] == s]
        nj = sum(juan_n(x) for x in es)
        L.append(f'<a class="dt-secbtn dt-secbtn-zh" href="/{NAME}/{s}"><span class="dt-sec-zh">{s}</span>'
                 f'<span class="dt-sec-n">{len(es)} 部 · {nj} 卷</span></a>')
    L += ['</div>', '']
    open(os.path.join(DOCS, 'index.md'), 'w', encoding='utf-8').write('\n'.join(L))

    for s in secs:
        es = [x for x in out_cat if x['sec'] == s]
        L = ['---', f'title: {s}', 'aside: false', 'sidebar: false', 'prev: false', 'next: false', '---', '',
             f'<p class="dt-crumb"><a href="/{NAME}/">{NAME}</a></p>', '', f'# {s}', '',
             f'<p class="dt-ql-sub">{GROUP.get(s, "")} · 共 {len(es)} 部 · 按龙藏原编号排列</p>', '',
             '<ol class="dt-texts dt-ql-texts">']
        for e in es:
            no = f'第{e["no"]}部' if e['no'] < 99999 else ''
            meta = ' '.join(x for x in [e['juan'], e['by']] if x)
            L.append(f'<li><a href="/{NAME}/read?t={e["t"]}&p=1">{e["title"]}</a>'
                     f'<span class="dt-ql-no">{no}</span>'
                     + (f'<span class="dt-ql-meta">{meta}</span>' if meta else '') + '</li>')
        L += ['</ol>', '']
        open(os.path.join(DOCS, f'{s}.md'), 'w', encoding='utf-8').write('\n'.join(L))

    open(os.path.join(DOCS, 'read.md'), 'w', encoding='utf-8').write(
        '---\ntitle: 乾隆大藏经\naside: false\nsidebar: false\nprev: false\nnext: false\n---\n\n<QianlongReader />\n')

    print(f'{NAME}：{len(secs)} 部类，{len(out_cat)} 部经，{total_parts} 个分册')
    if skipped:
        print('跳过空文件：', '；'.join(skipped))


if __name__ == '__main__':
    main()
