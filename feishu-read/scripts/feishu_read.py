#!/usr/bin/env python3
"""读取单篇飞书文档并输出为 markdown。

用法：
  feishu_read.py <URL 或 token>                  # 输出到 stdout
  feishu_read.py <URL> --output doc.md           # 写入文件
  feishu_read.py <URL> --no-images               # 不下载图片
  feishu_read.py <URL> --assets-dir ./images     # 自定义图片目录

支持的文档类型：docx（飞书文档）。
凭证：~/.config/feishu/secrets.env 或环境变量 FEISHU_ALERT_APP_ID / FEISHU_ALERT_APP_SECRET。
文档需先共享给告警机器人（可查看）。
"""
import argparse
import re
import sys
from pathlib import Path

# 复用 feishu-meeting-note 的共享 API 层
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'feishu-meeting-note' / 'scripts'))
from feishu_api import api, tenant_token, FeishuError  # noqa: E402

ASSETS = '_assets'

# ---------- block type 映射（与 feishu-sync 一致） ----------
BT = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 6, 10: 6, 11: 6}
KEY = {2: 'text', 12: 'bullet', 13: 'ordered', 14: 'code', 15: 'quote', 17: 'todo', 19: 'callout',
       **{t: f'heading{t - 2}' for t in range(3, 12)}}


# ---------- token 提取 ----------

def extract_doc_token(s):
    """从飞书文档 URL 或原始 token 中提取 docx token。"""
    s = s.strip()
    # 常见 URL 模式：https://.../docx/XXXXXXXX
    m = re.search(r'/docx/([A-Za-z0-9]+)', s)
    if m:
        return m.group(1)
    # 也可能是直接传 token
    if re.match(r'^[A-Za-z0-9]+$', s):
        return s
    raise ValueError(f'无法从输入中提取文档 token：{s}（支持 docx 文档 URL 或纯 token）')


# ---------- inline 渲染 ----------

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


# ---------- 图片类型嗅探 ----------

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


# ---------- DocRenderer ----------

class DocRenderer:
    def __init__(self, blocks, tok, token, assets_dir, download_images=True):
        self.by_id = {b['block_id']: b for b in blocks}
        self.root = next(b for b in blocks if b['block_type'] == 1)
        self.tok, self.token, self.assets_dir = tok, token, assets_dir
        self.download_images = download_images
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
        if not self.download_images:
            return f'![图片]({ftok})'
        try:
            data = api('GET', f'/drive/v1/medias/{ftok}/download', tok=self.tok, raw=True)
        except FeishuError as e:
            return f'<!-- 图片下载失败 {ftok}: {e} -->'
        self.img_n += 1
        ext = sniff_ext(data)
        name = f'img{self.img_n:02d}{ext}'
        out_dir = self.assets_dir / self.token
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / name).write_bytes(data)
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


# ---------- 读 docx ----------

def fetch_docx(tok, token, assets_dir, download_images=True):
    blocks, pt = [], ''
    while True:
        q = f'/docx/v1/documents/{token}/blocks?page_size=500&document_revision_id=-1' + (f'&page_token={pt}' if pt else '')
        d = api('GET', q, tok=tok)['data']
        blocks += d['items']
        if not d.get('has_more'):
            break
        pt = d['page_token']
    r = DocRenderer(blocks, tok, token, assets_dir, download_images=download_images)
    return r.render(), r.title()


def get_docx_meta(tok, token):
    """获取文档元信息（标题、修改时间等）。"""
    d = api('GET', f'/docx/v1/documents/{token}', tok=tok)['data']
    doc = d.get('document', {})
    return {
        'title': doc.get('title', ''),
        'revision_id': doc.get('revision_id', ''),
        'modified_time': doc.get('modified_time', ''),
        'create_time': doc.get('create_time', ''),
    }


# ---------- frontmatter ----------

def frontmatter(token, url, title, modified):
    lines = ['---']
    lines.append(f'feishu_token: {token}')
    lines.append(f'feishu_url: {url}')
    if title:
        lines.append(f'feishu_title: "{title}"')
    if modified:
        lines.append(f'feishu_modified: {modified}')
    lines.append('---')
    lines.append('')
    return '\n'.join(lines)


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description='读取飞书文档并输出为 markdown')
    parser.add_argument('input', help='飞书文档 URL 或 token')
    parser.add_argument('--output', '-o', help='输出文件路径（默认输出到 stdout）')
    parser.add_argument('--assets-dir', default=ASSETS, help=f'图片下载根目录（默认：{ASSETS}）')
    parser.add_argument('--no-images', action='store_true', help='不下载图片，只留占位符')
    parser.add_argument('--type', default='docx', choices=['docx'], help='文档类型（目前只支持 docx）')
    args = parser.parse_args()

    try:
        token = extract_doc_token(args.input)
    except ValueError as e:
        print(f'错误：{e}', file=sys.stderr)
        sys.exit(1)

    # 构造可回跳的 URL（如果输入本身就是 URL 就用原 URL）
    if args.input.startswith('http'):
        url = args.input
    else:
        url = f'https://bytedance.larkoffice.com/docx/{token}'

    assets_dir = Path(args.assets_dir).resolve()

    try:
        tok = tenant_token()
    except FeishuError as e:
        print(f'凭证错误：{e}', file=sys.stderr)
        print('请确认 ~/.config/feishu/secrets.env 已配置 FEISHU_ALERT_APP_ID / FEISHU_ALERT_APP_SECRET',
              file=sys.stderr)
        sys.exit(1)

    try:
        if args.type == 'docx':
            content, render_title = fetch_docx(tok, token, assets_dir,
                                               download_images=not args.no_images)
            meta = get_docx_meta(tok, token)
            title = meta.get('title') or render_title
            modified = meta.get('modified_time', '')
        else:
            print(f'暂不支持的文档类型：{args.type}', file=sys.stderr)
            sys.exit(1)
    except FeishuError as e:
        if e.code in (99991663, 99991668, 99991672):  # 权限相关错误码
            print(f'权限错误：{e}', file=sys.stderr)
            print('请确认该文档已共享给告警机器人（可查看权限）。', file=sys.stderr)
        else:
            print(f'读取失败：{e}', file=sys.stderr)
        sys.exit(1)

    output = frontmatter(token, url, title, modified) + content

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding='utf-8')
        print(f'已写入 {out_path}', file=sys.stderr)
    else:
        print(output, end='')


if __name__ == '__main__':
    main()
