#!/usr/bin/env python3
"""新客户一键接入：飞书文件夹链接 → 私有 repo + 首次同步 + GitHub Actions 定时同步。

  onboard.py <飞书文件夹URL> --name <客户slug> [--dir ~/Documents/customers] [--owner lmanxue]

步骤：校验机器人能读该文件夹 → 确保 team-skills 的只读 deploy key → 建私有 repo →
脚手架（feishu-sync.toml / workflow / CLAUDE.md）→ 本地首次同步并 push（走 SSH，不需要 workflow scope）→
写 3 个 secret → 触发一次 workflow 并等结果。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(HERE.parents[1] / 'feishu-meeting-note' / 'scripts'))
from feishu_api import FeishuError, _load_secrets, tenant_token  # noqa: E402
import sync as syncmod  # noqa: E402

KEY_PATH = Path('~/.config/feishu/team-skills-deploy-key').expanduser()


def run(*cmd, cwd=None, inp=None, check=True):
    r = subprocess.run(cmd, cwd=cwd, input=inp, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f'命令失败：{" ".join(cmd)}\n{r.stdout}{r.stderr}')
    return r.stdout.strip()


def step(msg):
    print(f'==> {msg}', flush=True)


def ensure_deploy_key(skills_repo):
    if not KEY_PATH.exists():
        step('生成 team-skills 只读 deploy key（一次性）')
        run('ssh-keygen', '-t', 'ed25519', '-N', '', '-C', 'feishu-sync-actions', '-f', str(KEY_PATH))
    pub = Path(str(KEY_PATH) + '.pub').read_text().strip()
    keys = json.loads(run('gh', 'api', f'repos/{skills_repo}/keys'))
    if not any(k['key'].split()[:2] == pub.split()[:2] for k in keys):
        run('gh', 'repo', 'deploy-key', 'add', str(KEY_PATH) + '.pub', '-R', skills_repo, '-t', 'feishu-sync-actions')
        print('   已把公钥加到 team-skills（只读）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--name', required=True, help='客户 slug，如 mingpeng（同时是 repo 名）')
    ap.add_argument('--dir', default='~/Documents/customers')
    ap.add_argument('--owner')
    ap.add_argument('--skills-repo', default='lmanxue/team-skills')
    a = ap.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', a.name):
        sys.exit('--name 只能用小写字母、数字、连字符')
    owner = a.owner or run('gh', 'api', 'user', '--jq', '.login')
    full = f'{owner}/{a.name}'
    dest = Path(a.dir).expanduser() / a.name
    if dest.exists():
        sys.exit(f'{dest} 已存在，换个 --name 或先处理掉')

    step('校验机器人能读该飞书文件夹')
    token = syncmod.folder_token(a.folder)
    try:
        files = list(syncmod.walk(tenant_token(), token))
    except FeishuError as e:
        sys.exit(f'读不到文件夹（{e}）。请在飞书里把该文件夹共享给「告警机器人」（可查看即可）后重试。')
    if not files:
        sys.exit('文件夹是空的，先放资料或确认共享对了文件夹')
    print(f'   可读，共 {len(files)} 个文件')

    ensure_deploy_key(a.skills_repo)

    step(f'创建私有 repo {full}')
    run('gh', 'repo', 'create', full, '--private', '--description', f'{a.name} 客户资料（飞书镜像）')
    dest.parent.mkdir(parents=True, exist_ok=True)
    run('git', 'clone', f'git@github.com:{full}.git', str(dest))

    step('脚手架')
    (dest / '.github/workflows').mkdir(parents=True)
    wf = (SKILL / 'templates/feishu-sync.yml').read_text().replace('__SKILLS_REPO__', a.skills_repo)
    (dest / '.github/workflows/feishu-sync.yml').write_text(wf)
    (dest / 'CLAUDE.md').write_text((SKILL / 'templates/CLAUDE.md').read_text().replace('__NAME__', a.name))
    (dest / 'feishu-sync.toml').write_text(f'[[source]]\nfolder = "{a.folder.split("?")[0]}"\nout = "feishu"\n')
    (dest / '.gitignore').write_text('.DS_Store\n')

    step('首次同步')
    rc = subprocess.run([sys.executable, str(HERE / 'sync.py'), '--config', 'feishu-sync.toml'], cwd=dest).returncode
    if rc:
        print('   部分文档同步失败（见上），其余已写入')
    run('git', 'add', '-A', cwd=dest)
    run('git', 'commit', '-m', 'init: feishu-sync scaffold + first sync', cwd=dest)
    run('git', 'branch', '-M', 'main', cwd=dest)
    run('git', 'push', '-u', 'origin', 'main', cwd=dest)

    step('写入 Actions secrets')
    app_id, app_secret = _load_secrets()
    for k, v in (('FEISHU_ALERT_APP_ID', app_id), ('FEISHU_ALERT_APP_SECRET', app_secret),
                 ('TEAM_SKILLS_DEPLOY_KEY', KEY_PATH.read_text())):
        run('gh', 'secret', 'set', k, '-R', full, '--body', v)

    step('触发一次 workflow 验证')
    run('gh', 'workflow', 'run', 'feishu-sync.yml', '-R', full)
    import time
    time.sleep(8)
    rid = run('gh', 'run', 'list', '-R', full, '--workflow', 'feishu-sync.yml', '--limit', '1', '--json', 'databaseId', '--jq', '.[0].databaseId')
    r = subprocess.run(['gh', 'run', 'watch', rid, '-R', full, '--exit-status'], text=True)
    print(f'\n本地：{dest}\n仓库：https://github.com/{full}\nActions：{"✅ 通过" if r.returncode == 0 else "❌ 失败，gh run view " + rid + " -R " + full + " --log-failed"}')
    sys.exit(r.returncode)


if __name__ == '__main__':
    main()
