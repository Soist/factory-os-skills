#!/usr/bin/env python3
"""飞书云盘文件夹 → 本地 markdown 镜像（单向、幂等、纯 stdlib）。

用法：
  sync.py --config feishu-sync.toml            # 读配置里的 [[source]]
  sync.py --folder <URL|token> --out <dir>     # 临时单个文件夹
  加 --dry-run 只打印计划；加 --allow-empty 允许「飞书列表为空 → 清空本地」。

格式统一规则（目标：agent 直接读，且 git diff 可读）：
  docx            → .md（块树转 markdown，图片下载到 _assets/<token>/）
  .md/.txt/.csv/.json → 原样
  .pptx           → .md（每页一节：文字 + 备注 + 页内图片 ≥30KB）
  .xlsx           → .md（每个 sheet 一张表）
  .pdf            → .md（pdftotext -layout；没装 pdftotext 则原样保留 pdf）
  .html/图片       → 原样
  飞书原生 slides/sheet/bitable → .md（slides 走 slides_ai XML 接口，sheet/bitable 走各自 API）；mindnote 等其余类型只告警
镜像语义：飞书里不在了的文档，本地同步删除（git 保留历史）。
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'feishu-meeting-note' / 'scripts'))
from feishu_api import api, tenant_token, FeishuError  # noqa: E402

STATE = '.feishu-sync.json'
ASSETS = '_assets'
PASSTHROUGH = {'.md', '.txt', '.csv', '.json', '.html', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}
MIN_PPTX_IMG = 30 * 1024


# ---------- 飞书 API ----------

def list_folder(tok, folder):
    out, pt = [], ''
    while True:
        q = f'/drive/v1/files?folder_token={folder}&page_size=200' + (f'&page_token={pt}' if pt else '')
        d = api('GET', q, tok=tok)['data']
        out += d.get('files', [])
        if not d.get('has_more'):
            return out
        pt = d['next_page_token']


def walk(tok, folder, rel=''):
    """递归列出 (rel_dir, file_dict)。任何 API 失败直接抛，绝不返回残缺列表（防误删）。"""
    for f in list_folder(tok, folder):
        if f['type'] == 'folder':
            yield from walk(tok, f['token'], f'{rel}/{safe(f["name"])}'.lstrip('/'))
        else:
            yield rel, f


def safe(name):
    return re.sub(r'[\\/:*?"<>|\n\r\t]+', '_', name).strip(' .') or '_'


def folder_token(s):
    m = re.search(r'/folder/([A-Za-z0-9]+)', s)
    return m.group(1) if m else s


# ---------- docx → markdown ----------

BT = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 6, 10: 6, 11: 6}
KEY = {2: 'text', 12: 'bullet', 13: 'ordered', 14: 'code', 15: 'quote', 17: 'todo', 19: 'callout',
       **{t: f'heading{t - 2}' for t in range(3, 12)}}


def inline(elements):
    s = ''
    for e in elements or []:
        if 'text_run' in e:
            tr = e['text_run']
            t = tr.get('content', '')
            st = tr.get('text_element_style', {})
            if not t.strip():
                s += t
                continue
            if st.get('inline_code'):
                t = f'`{t}`'
            if st.get('bold'):
                t = f'**{t}**'
            if st.get('italic'):
                t = f'*{t}*'
            if st.get('strikethrough'):
                t = f'~~{t}~~'
            if st.get('link', {}).get('url'):
                from urllib.parse import unquote
                t = f'[{t}]({unquote(st["link"]["url"])})'
            s += t
        elif 'mention_doc' in e:
            m = e['mention_doc']
            s += f'[{m.get("title", "文档")}]({m.get("url", "")})'
        elif 'mention_user' in e:
            s += '@用户'
        elif 'equation' in e:
            s += f'${e["equation"].get("content", "").strip()}$'
    return s


class DocRenderer:
    def __init__(self, blocks, tok, token, assets_dir):
        self.by_id = {b['block_id']: b for b in blocks}
        self.root = next(b for b in blocks if b['block_type'] == 1)
        self.tok, self.token, self.assets_dir = tok, token, assets_dir
        self.img_n = 0

    def title(self):
        return inline(self.root.get('page', {}).get('elements')).strip()

    def render(self):
        lines = self.children(self.root, 0)
        return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip() + '\n'

    def children(self, b, depth):
        out, n = [], 0
        for cid in b.get('children', []):
            c = self.by_id[cid]
            n = n + 1 if c['block_type'] == 13 else 0
            out += self.block(c, depth, n)
        return out

    def block(self, b, depth, n):
        t = b['block_type']
        ind = '  ' * depth
        text = lambda k: inline(b.get(k, {}).get('elements'))  # noqa: E731
        if t == 2:
            return [ind + text('text'), '']
        if t in BT:
            return ['', '#' * BT[t] + ' ' + text(KEY[t]), '']
        if t == 12:
            return [f'{ind}- {text("bullet")}'] + self.children(b, depth + 1)
        if t == 13:
            return [f'{ind}{n}. {text("ordered")}'] + self.children(b, depth + 1)
        if t == 17:
            mark = 'x' if b['todo'].get('style', {}).get('done') else ' '
            return [f'{ind}- [{mark}] {text("todo")}'] + self.children(b, depth + 1)
        if t == 14:
            return ['', '```', ''.join(e.get('text_run', {}).get('content', '') for e in b['code']['elements']).rstrip('\n'), '```', '']
        if t == 15:
            return ['> ' + text('quote'), '']
        if t in (19, 34):  # callout / quote_container：子块整体加引用前缀
            inner = self.children(b, 0)
            return [''] + [('> ' + l).rstrip() for l in inner] + ['']
        if t == 22:
            return ['', '---', '']
        if t in (24, 25):  # grid / column：顺序展开
            return self.children(b, depth)
        if t == 27:
            return [ind + self.image(b['image'].get('token', '')), '']
        if t == 31:
            return self.table(b)
        if t == 23:
            return [f'{ind}[附件：{b["file"].get("name", "")}]', '']
        if t == 1:
            return []
        kind = next((k for k in b if k not in ('block_id', 'block_type', 'parent_id', 'children')), '')
        inner = self.children(b, depth)
        return [f'{ind}<!-- 未支持的块类型 {t} {kind} -->'] + inner

    def image(self, ftok):
        if not ftok:
            return '![图片]()'
        try:
            data = api('GET', f'/drive/v1/medias/{ftok}/download', tok=self.tok, raw=True)
        except FeishuError as e:
            return f'<!-- 图片下载失败 {ftok}: {e} -->'
        self.img_n += 1
        ext = sniff_ext(data)
        name = f'img{self.img_n:02d}{ext}'
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        (self.assets_dir / name).write_bytes(data)
        return f'![图{self.img_n}](./{ASSETS}/{self.token}/{name})'

    def cell_text(self, cid):
        c = self.by_id[cid]
        parts = []
        for line in self.children(c, 0):
            if line.strip():
                parts.append(line.strip())
        return '<br>'.join(parts).replace('|', '\\|')

    def table(self, b):
        prop = b['table']['property']
        cols = prop['column_size']
        cells = [self.cell_text(c) for c in b['table']['cells']]
        rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
        if not rows:
            return []
        md = ['', '| ' + ' | '.join(rows[0]) + ' |', '|' + ' --- |' * cols]
        md += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
        return md + ['']


def sniff_ext(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return '.png'
    if data[:3] == b'\xff\xd8\xff':
        return '.jpg'
    if data[:4] == b'GIF8':
        return '.gif'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    return '.bin'


def fetch_docx(tok, token, assets_dir):
    blocks, pt = [], ''
    while True:
        q = f'/docx/v1/documents/{token}/blocks?page_size=500&document_revision_id=-1' + (f'&page_token={pt}' if pt else '')
        d = api('GET', q, tok=tok)['data']
        blocks += d['items']
        if not d.get('has_more'):
            break
        pt = d['page_token']
    r = DocRenderer(blocks, tok, token, assets_dir)
    return r.render()


# ---------- pptx / xlsx / pdf → markdown ----------

NS_A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
NS_R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def _paras(xml_bytes):
    root = ET.fromstring(xml_bytes)
    out = []
    for p in root.iter(NS_A + 'p'):
        t = ''.join(x.text or '' for x in p.iter(NS_A + 't')).strip()
        if t:
            out.append(t)
    return out


def pptx_to_md(data, assets_dir, token):
    z = zipfile.ZipFile(__import__('io').BytesIO(data))
    names = set(z.namelist())
    slides = sorted((n for n in names if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                    key=lambda n: int(re.search(r'(\d+)', n.rsplit('/', 1)[1]).group(1)))
    out = []
    for i, sn in enumerate(slides, 1):
        paras = _paras(z.read(sn))
        out += [f'## 第 {i} 页', '']
        out += [f'- {p}' if len(paras) > 1 else p for p in paras] or ['（无文字）']
        # 备注
        rels = f'ppt/slides/_rels/{sn.rsplit("/", 1)[1]}.rels'
        imgs = []
        if rels in names:
            for rel in ET.fromstring(z.read(rels)):
                tgt = rel.get('Target', '')
                full = os.path.normpath(os.path.join('ppt/slides', tgt)).replace('\\', '/')
                if '/notesSlides/' in full and full in names:
                    notes = [p for p in _paras(z.read(full)) if not p.isdigit()]
                    if notes:
                        out += ['', '> 备注：' + ' / '.join(notes)]
                elif '/media/' in full and full in names:
                    info = z.getinfo(full)
                    if info.file_size >= MIN_PPTX_IMG:
                        imgs.append(full)
        for j, full in enumerate(dict.fromkeys(imgs), 1):
            ext = Path(full).suffix.lower()
            if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
                continue
            assets_dir.mkdir(parents=True, exist_ok=True)
            fn = f's{i:02d}-{j}{ext}'
            (assets_dir / fn).write_bytes(z.read(full))
            out += ['', f'![第{i}页图{j}](./{ASSETS}/{token}/{fn})']
        out.append('')
    return '\n'.join(out).strip() + '\n'


def xlsx_to_md(data):
    z = zipfile.ZipFile(__import__('io').BytesIO(data))
    ns = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    sst = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', ns):
            sst.append(''.join(t.text or '' for t in si.iter('{%s}t' % ns['m'])))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = []
    for sh in wb.find('m:sheets', ns):
        rid = sh.get(NS_R + 'id')
        path = 'xl/' + rels[rid].lstrip('/').replace('xl/', '')
        rows = []
        for row in ET.fromstring(z.read(path)).iter('{%s}row' % ns['m']):
            cells = {}
            for c in row.findall('m:c', ns):
                col = re.match(r'[A-Z]+', c.get('r')).group(0)
                v = c.find('m:v', ns)
                if c.get('t') == 's' and v is not None:
                    val = sst[int(v.text)]
                elif c.get('t') == 'inlineStr':
                    val = ''.join(t.text or '' for t in c.iter('{%s}t' % ns['m']))
                else:
                    val = v.text if v is not None else ''
                cells[col] = (val or '').replace('\n', ' ').replace('|', '\\|')
            if cells:
                rows.append(cells)
        out += [f'## {sh.get("name")}', '']
        if not rows:
            out += ['（空）', '']
            continue
        cols = sorted({c for r in rows for c in r}, key=lambda c: (len(c), c))
        out.append('| ' + ' | '.join(cols) + ' |')
        out.append('|' + ' --- |' * len(cols))
        out += ['| ' + ' | '.join(r.get(c, '') for c in cols) + ' |' for r in rows]
        out.append('')
    return '\n'.join(out).strip() + '\n'


# ---------- 飞书原生 slides / sheet / bitable ----------

def _md_table(rows):
    rows = [[('' if c is None else str(c)).replace('\n', ' ').replace('|', '\\|') for c in r] for r in rows]
    if not rows:
        return ['（空）', '']
    n = max(len(r) for r in rows)
    rows = [r + [''] * (n - len(r)) for r in rows]
    return ['| ' + ' | '.join(rows[0]) + ' |', '|' + ' --- |' * n] + ['| ' + ' | '.join(r) + ' |' for r in rows[1:]] + ['']


def slides_to_md(tok, token, assets_dir):
    x = api('GET', f'/slides_ai/v1/xml_presentations/{token}', tok=tok)['data']['xml_presentation']['content']
    root = ET.fromstring(x)
    loc = lambda e: e.tag.rsplit('}', 1)[-1]  # noqa: E731
    out, n_img = [], 0
    for i, sl in enumerate((e for e in root.iter() if loc(e) == 'slide'), 1):
        out += [f'## 第 {i} 页', '']
        texts, imgs = [], []
        for e in sl.iter():
            if loc(e) == 'img' and e.get('src'):
                imgs.append(e.get('src'))
            elif loc(e) not in ('style', 'fill', 'fillColor', 'crop') and (e.text or '').strip():
                texts.append(e.text.strip())
        out += [f'- {t}' for t in texts]
        for j, src in enumerate(dict.fromkeys(imgs), 1):
            try:
                data = api('GET', f'/drive/v1/medias/{src}/download', tok=tok, raw=True)
            except FeishuError as e:
                out.append(f'<!-- 图片下载失败 {src}: {e} -->')
                continue
            assets_dir.mkdir(parents=True, exist_ok=True)
            fn = f's{i:02d}-{j}{sniff_ext(data)}'
            (assets_dir / fn).write_bytes(data)
            out.append(f'![第{i}页图{j}](./{ASSETS}/{token}/{fn})')
        out.append('')
    note = '> 注：飞书原生幻灯片，文字内容取自 XML；整页是图片的页面没有可检索文字，请直接看图。\n\n'
    return note + '\n'.join(out).strip() + '\n'


def sheet_to_md(tok, token):
    sheets = api('GET', f'/sheets/v3/spreadsheets/{token}/sheets/query', tok=tok)['data']['sheets']
    out = []
    for sh in sheets:
        vals = api('GET', f'/sheets/v2/spreadsheets/{token}/values/{sh["sheet_id"]}?valueRenderOption=ToString', tok=tok)
        rows = vals['data']['valueRange'].get('values') or []
        while rows and not any(c not in (None, '') for c in rows[-1]):
            rows.pop()
        out += [f'## {sh.get("title", sh["sheet_id"])}', ''] + _md_table(rows)
    return '\n'.join(out).strip() + '\n'


def _bitable_cell(v):
    if isinstance(v, list):
        return ', '.join(_bitable_cell(x) for x in v)
    if isinstance(v, dict):
        return str(v.get('text') or v.get('name') or v.get('link') or json.dumps(v, ensure_ascii=False))
    return '' if v is None else str(v)


def bitable_to_md(tok, token):
    tables = api('GET', f'/bitable/v1/apps/{token}/tables?page_size=100', tok=tok)['data']['items']
    out = []
    for tb in tables:
        tid, rows, pt = tb['table_id'], [], ''
        while True:
            q = f'/bitable/v1/apps/{token}/tables/{tid}/records?page_size=500' + (f'&page_token={pt}' if pt else '')
            d = api('GET', q, tok=tok)['data']
            rows += [r['fields'] for r in d.get('items', [])]
            if not d.get('has_more'):
                break
            pt = d['page_token']
        cols = list(dict.fromkeys(k for r in rows for k in r))
        out += [f'## {tb.get("name", tid)}', ''] + _md_table([cols] + [[_bitable_cell(r.get(c)) for c in cols] for r in rows])
    return '\n'.join(out).strip() + '\n'



def pdf_to_md(data):
    if not shutil.which('pdftotext'):
        return None
    with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
        f.write(data)
        f.flush()
        r = subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True)
    return r.stdout.decode('utf-8', 'replace').strip() + '\n' if r.returncode == 0 else None


# ---------- 同步主流程 ----------

def frontmatter(f, kind):
    url = f.get('url', '')
    return ('---\n'
            f'title: {json.dumps(f["name"], ensure_ascii=False)}\n'
            f'feishu_token: {f["token"]}\n'
            f'feishu_type: {f["type"]}\n'
            f'feishu_url: {url}\n'
            f'feishu_modified: {f.get("modified_time", "")}\n'
            '---\n\n')


def convert(tok, f, rel_dir, out_root):
    """返回 (相对路径, 内容 bytes) 列表；assets 直接落盘到 out_root/_assets/<token>/。"""
    typ, name, token = f['type'], f['name'], f['token']
    assets_dir = out_root / ASSETS / token
    if typ == 'docx':
        body = fetch_docx(tok, token, assets_dir)
        return f'{safe(name)}.md', (frontmatter(f, 'docx') + f'# {name}\n\n' + body).encode()
    native = {'slides': lambda: slides_to_md(tok, token, assets_dir), 'sheet': lambda: sheet_to_md(tok, token),
              'bitable': lambda: bitable_to_md(tok, token)}
    if typ in native:
        return f'{safe(name)}.md', (frontmatter(f, typ) + f'# {name}\n\n' + native[typ]()).encode()
    if typ != 'file':
        return None, None
    ext = Path(name).suffix.lower()
    stem = safe(Path(name).stem)
    data = api('GET', f'/drive/v1/files/{token}/download', tok=tok, raw=True)
    if ext in PASSTHROUGH:
        return safe(name), data
    if ext == '.pptx':
        return f'{stem}.md', (frontmatter(f, 'pptx') + f'# {name}\n\n' + pptx_to_md(data, assets_dir, token)).encode()
    if ext == '.xlsx':
        return f'{stem}.md', (frontmatter(f, 'xlsx') + f'# {name}\n\n' + xlsx_to_md(data)).encode()
    if ext == '.pdf':
        md = pdf_to_md(data)
        if md is None:
            return safe(name), data
        return f'{stem}.md', (frontmatter(f, 'pdf') + f'# {name}\n\n' + md).encode()
    return None, None


def sync(tok, folder, out_root, dry, allow_empty):
    out_root.mkdir(parents=True, exist_ok=True)
    state_p = out_root / STATE
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    remote = list(walk(tok, folder))
    if not remote and state and not allow_empty:
        sys.exit(f'飞书列表为空但本地有 {len(state)} 个文档，疑似权限/共享异常，拒绝清空（确认无误加 --allow-empty）')

    new_state, used, failed, skipped, failed_tokens = {}, set(), [], [], set()
    for rel_dir, f in remote:
        token = f['token']
        prev = state.get(token)
        mod = str(f.get('modified_time', ''))
        if prev and prev['modified'] == mod and (out_root / prev['path']).exists():
            new_state[token] = prev
            used.add(prev['path'])
            continue
        try:
            fname, content = convert(tok, f, rel_dir, out_root) if not dry else (f['name'], b'')
        except Exception as e:  # 单文档失败：保留旧版本，继续
            failed.append((f['name'], str(e)[:200]))
            failed_tokens.add(token)
            if prev:
                new_state[token] = prev
                used.add(prev['path'])
            continue
        if fname is None:
            skipped.append((f['name'], f['type']))
            continue
        path = f'{rel_dir}/{fname}'.lstrip('/')
        if path in used:  # 同名冲突
            p = Path(path)
            path = str(p.with_name(f'{p.stem}-{token[:6]}{p.suffix}'))
        used.add(path)
        print(('[dry] ' if dry else '写入 ') + path)
        if not dry:
            tgt = out_root / path
            tgt.parent.mkdir(parents=True, exist_ok=True)
            tgt.write_bytes(content)
        new_state[token] = {'path': path, 'modified': mod, 'name': f['name'], 'type': f['type']}

    # 镜像删除：飞书不再有的；以及改名/移动后的旧路径
    remote_tokens = {f['token'] for _, f in remote}
    for token, prev in state.items():
        gone = token not in remote_tokens
        moved = token in new_state and new_state[token]['path'] != prev['path']
        if (gone or moved) and token not in failed_tokens:
            print(('[dry] ' if dry else '删除 ') + prev['path'] + ('（飞书已删除）' if gone else '（路径变更）'))
            if not dry:
                (out_root / prev['path']).unlink(missing_ok=True)
                if gone:
                    shutil.rmtree(out_root / ASSETS / token, ignore_errors=True)
    if not dry:
        # 清空目录
        for d in sorted((p for p in out_root.rglob('*') if p.is_dir()), key=lambda p: -len(p.parts)):
            if not any(d.iterdir()):
                d.rmdir()
        state_p.write_text(json.dumps(new_state, ensure_ascii=False, indent=1, sort_keys=True) + '\n')
    for n, t in skipped:
        print(f'跳过（暂不支持的类型 {t}）：{n}', file=sys.stderr)
    for n, e in failed:
        print(f'失败：{n}: {e}', file=sys.stderr)
    return 1 if failed else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--config')
    ap.add_argument('--folder')
    ap.add_argument('--out')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--allow-empty', action='store_true')
    a = ap.parse_args()
    sources = []
    if a.config:
        import tomllib
        cfg_p = Path(a.config).resolve()
        cfg = tomllib.loads(cfg_p.read_text())
        sources = [(s['folder'], cfg_p.parent / s['out']) for s in cfg['source']]
    elif a.folder and a.out:
        sources = [(a.folder, Path(a.out))]
    else:
        ap.error('需要 --config 或 --folder + --out')
    tok = tenant_token()
    rc = 0
    for folder, out in sources:
        rc |= sync(tok, folder_token(folder), out, a.dry_run, a.allow_empty)
    sys.exit(rc)


if __name__ == '__main__':
    main()
