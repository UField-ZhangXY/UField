#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ufield-ppt 构建脚本
=====================
把 UField PPT 的完整生产链路封装成一条命令，封装了以下已知坑：

  1. slidep 启动 shim 路径可能失效 -> 直接调用 @tencent/slidep 的 dist/index.js
  2. slidep 生成的包 LibreOffice/WPS 可能读不了 -> 用 python-pptx 重存一次（finalize）
  3. slidep 原始包 LibreOffice 转 PDF 会失败 -> 先重存再转

用法（在「幻灯片项目目录」下执行，目录需含 slides/*.slide 与 assets/）：

  python deck.py doctor                      # 打印定位到的引擎/工具路径
  python deck.py create   <deck.pptx>        # 新建空白 pptx
  python deck.py lint     <deck.pptx> <slides_dir>
  python deck.py write    <deck.pptx> <slides_dir>   # 逐页写入（页码取文件名前导数字-1）
  python deck.py finalize <deck.pptx>        # python-pptx 兼容重存（原地）
  python deck.py render   <deck.pptx> <outdir>       # 渲染 png 供质检（不删除任何文件）

  python deck.py all      <deck.pptx> <slides_dir>   # create+lint+write+finalize 一条龙

页面文件命名约定：<两位页码>_<版式名>.slide，例如 01_cover_dark.slide、07_cards_3.slide。
页码 = 文件名前导数字 - 1（slidep 的 page-index 从 0 起）。
"""
import os
import re
import sys
import glob
import shutil
import subprocess

def log(msg):
    print(f"[deck] {msg}", flush=True)

def _newest(paths):
    return sorted(paths)[-1] if paths else None

def find_node():
    home = os.path.expanduser("~")
    cands = glob.glob(os.path.join(home, ".workbuddy", "binaries", "node", "versions", "*", "node.exe"))
    cands += glob.glob(os.path.join(home, ".workbuddy", "binaries", "node", "versions", "*", "bin", "node"))
    if not cands:
        w = shutil.which("node")
        if w:
            return w
    return _newest(cands)

def find_slidep(node_path):
    if not node_path:
        return None
    ver_dir = os.path.dirname(node_path)          # .../versions/<ver>
    cands = glob.glob(os.path.join(ver_dir, "lib", "node_modules", "@tencent", "slidep", "dist", "index.js"))
    return _newest(cands)

def find_soffice():
    cands = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return shutil.which("soffice")

def find_python_with(mod):
    """返回一个能 import <mod> 的 python 解释器路径。"""
    def ok(py):
        try:
            r = subprocess.run([py, "-c", f"import {mod}"], capture_output=True, timeout=60)
            return r.returncode == 0
        except Exception:
            return False
    if ok(sys.executable):
        return sys.executable
    home = os.path.expanduser("~")
    cands = glob.glob(os.path.join(home, ".cache", "codex-runtimes", "*", "dependencies", "python", "python.exe"))
    cands += glob.glob(os.path.join(home, ".cache", "codex-runtimes", "*", "dependencies", "python", "bin", "python*"))
    for c in cands:
        if ok(c):
            return c
    for c in ("python3", "python"):
        if shutil.which(c) and ok(shutil.which(c)):
            return shutil.which(c)
    return None

# ---------------------------------------------------------------- slidep 封装

def slidep(args, node, sp):
    cmd = [node, sp] + args
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    # 过滤 node 的 deprecation 噪音
    lines = [l for l in out.splitlines() if "Deprecation" not in l and "trace-deprecation" not in l]
    return r.returncode, "\n".join(lines).strip()

def page_index(path):
    m = re.match(r"(\d+)", os.path.basename(path))
    if not m:
        raise SystemExit(f"[deck] 文件名缺少前导页码: {path}")
    return int(m.group(1)) - 1

def list_slides(slides_dir):
    files = sorted(glob.glob(os.path.join(slides_dir, "*.slide")))
    if not files:
        raise SystemExit(f"[deck] {slides_dir} 下没有 .slide 文件")
    return sorted(files, key=page_index)

# ---------------------------------------------------------------- 子命令

def cmd_doctor(_a):
    node = find_node(); sp = find_slidep(node); so = find_soffice()
    py_pptx = find_python_with("pptx"); py_pdf = find_python_with("pypdfium2")
    log(f"node      : {node}")
    log(f"slidep    : {sp}")
    log(f"soffice   : {so}")
    log(f"python+pptx       : {py_pptx}")
    log(f"python+pypdfium2  : {py_pdf}")
    ok = all([node, sp, so, py_pptx])
    log("doctor: " + ("OK" if ok else "缺少依赖，见上"))
    return 0

def cmd_create(a):
    node = find_node(); sp = find_slidep(node)
    code, out = slidep(["create", a[0]], node, sp)
    log(out)
    return 0 if '"ok":true' in out else 1

def cmd_lint(a):
    pptx, sdir = a[0], a[1]
    node = find_node(); sp = find_slidep(node)
    bad = 0
    for f in list_slides(sdir):
        code, out = slidep(["lint", pptx, "--dsl-file", f], node, sp)
        ok = '"ok":true' in out
        print(f"  {os.path.basename(f)}: {'OK' if ok else 'FAIL'}")
        if not ok:
            bad += 1
            print("    " + out.replace("\n", "\n    "))
    log(f"lint: {len(list_slides(sdir))-bad} 通过 / {bad} 失败")
    return 0 if bad == 0 else 1

def cmd_write(a):
    pptx, sdir = a[0], a[1]
    node = find_node(); sp = find_slidep(node)
    bad = 0
    for f in list_slides(sdir):
        idx = page_index(f)
        code, out = slidep(["upsert-dsl", pptx, "--dsl-file", f, "--page-index", str(idx)], node, sp)
        ok = '"ok":true' in out
        print(f"  {os.path.basename(f)} (idx {idx}): {'OK' if ok else 'FAIL'}")
        if not ok:
            bad += 1
            print("    " + out.replace("\n", "\n    "))
    log(f"write: {len(list_slides(sdir))-bad} 写入 / {bad} 失败")
    return 0 if bad == 0 else 1

def cmd_finalize(a):
    """python-pptx 原地重存，产出全平台兼容包。"""
    pptx = a[0]
    py = find_python_with("pptx")
    if not py:
        log("找不到带 python-pptx 的解释器，跳过 finalize")
        return 1
    code = (
        "import pptx,sys;"
        f"p=pptx.Presentation(r'{pptx}');"
        f"p.save(r'{pptx}');"
        "print(len(p.slides))"
    )
    r = subprocess.run([py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        log("finalize 失败：" + (r.stderr or "").strip()[:400])
        return 1
    log(f"finalize OK（finalize 后页数：{(r.stdout or '').strip()}）")
    return 0

def cmd_render(a):
    pptx, outdir = a[0], a[1]
    os.makedirs(outdir, exist_ok=True)
    so = find_soffice()
    if not so:
        log("找不到 soffice，无法渲染")
        return 1
    r = subprocess.run([so, "--headless", "--convert-to", "pdf", "--outdir", outdir, os.path.abspath(pptx)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    pdfs = glob.glob(os.path.join(outdir, "*.pdf"))
    if not pdfs:
        log("PDF 转换失败（是否忘了先 finalize？）：" + (r.stderr or r.stdout or "").strip()[:300])
        return 1
    pdf = max(pdfs, key=os.path.getmtime)
    py = find_python_with("pypdfium2")
    if not py:
        log("找不到带 pypdfium2 的解释器，仅产出 PDF：" + pdf)
        return 1
    code = (
        "import pypdfium2 as pdfium,os;"
        f"d=pdfium.PdfDocument(r'{pdf}');"
        f"[p.render(scale=1.2).to_pil().save(os.path.join(r'{outdir}','p%02d.png'%(i+1))) for i,p in enumerate(d)];"
        "print(len(d))"
    )
    r2 = subprocess.run([py, "-c", code], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r2.returncode != 0:
        log("PNG 渲染失败：" + (r2.stderr or "").strip()[:300])
        return 1
    log(f"render OK -> {outdir}（{r2.stdout.strip()} 页 png）")
    return 0

def cmd_all(a):
    pptx, sdir = a[0], a[1]
    for step in (cmd_create, cmd_lint, cmd_write, cmd_finalize):
        rc = step([pptx] if step in (cmd_create, cmd_finalize) else [pptx, sdir])
        if rc != 0:
            log("all: 中断")
            return rc
    log("all: 完成（可再跑 render 做质检）")
    return 0

COMMANDS = {
    "doctor": cmd_doctor, "create": cmd_create, "lint": cmd_lint,
    "write": cmd_write, "finalize": cmd_finalize, "render": cmd_render, "all": cmd_all,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(2)
    sys.exit(COMMANDS[sys.argv[1]](sys.argv[2:]) or 0)
