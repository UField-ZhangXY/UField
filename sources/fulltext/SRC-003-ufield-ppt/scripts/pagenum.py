# -*- coding: utf-8 -*-
"""
pagenum.py — 【legacy】把页脚的 @PAGE@ / @PAGES@ 标记替换为 PowerPoint 页码域。

V3.1 起 masterize.py 已内置页码域化（版式层普通文本框 + slidenum 域），
新链路（write → finalize → masterize → render）不再需要本脚本；
仅老工程（不跑 masterize）兜底用。

用法（在 deck.py finalize 之后）：
    python pagenum.py <deck.pptx>

效果：
  - 页码 = 幻灯片编号域 → 在 PowerPoint/WPS 里增删页时**自动更新**；
  - 总页数 = 构建时的幻灯片总数（静态文本）。
    注：PowerPoint 没有"总页数"域（OOXML 域只有 slidenum/datetime/header/footer，
    微软官方确认总页数需手写固定值）；用 deck.py 重建则自动正确。
  - 文本框改为固定宽度 + 右对齐，页码 1 位/2 位数时右边缘不漂移。

DSL 写法（模板页脚）：
    <Text style={{ fontSize: 12, color: '#8A9296' }}>@PAGE@ / @PAGES@</Text>
"""
import re
import sys
import zipfile
import os

MARK = '@PAGE@ / @PAGES@'
FIXED = '<a:off x="11334750" y="6486525"/><a:ext cx="400050" cy="142875"/>'


def slide_order(z):
    """从 presentation.xml + rels 还原真实页序（slideN.xml 的 N 不可靠时兜底）。"""
    pres = z.read('ppt/presentation.xml').decode('utf-8')
    rels = z.read('ppt/_rels/presentation.xml.rels').decode('utf-8')
    rid2file = dict(re.findall(
        r'<Relationship Id="(rId\d+)"[^>]*Target="(slides/slide\d+\.xml)"', rels))
    order = []
    for rid in re.findall(r'<p:sldId[^>]*r:id="(rId\d+)"', pres):
        if rid in rid2file:
            order.append('ppt/' + rid2file[rid])
    if not order:  # 兜底：按文件名排序
        order = sorted((n for n in z.namelist()
                        if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                       key=lambda n: int(re.search(r'(\d+)', n).group(1)))
    return order


def patch_slide(xml, sid, total):
    """替换页脚标记为 fld 域；返回 (新xml, 是否改动)。"""
    # 带标签查找：slidep 会把 DSL 源码转义存进 descr 属性，
    # 纯文本标记会误命中，必须匹配真实的 <a:t> 节点
    needle = '<a:t>' + MARK + '</a:t>'
    tpos = xml.find(needle)
    if tpos == -1:
        return xml, False

    r_start = xml.rfind('<a:r>', 0, tpos)
    r_end = xml.find('</a:r>', tpos) + len('</a:r>')
    run = xml[r_start:r_end]
    rm = re.match(r'<a:r>(<a:rPr[^>]*(?:/>|>.*?</a:rPr>))<a:t>.*?</a:t></a:r>$', run, re.S)
    if not rm:
        raise RuntimeError('page-footer rPr parse failed: %s' % run[:160])
    rpr = rm.group(1)

    fld = ('<a:fld id="{{61DB1F4A-0000-4F0A-9E7A-%012d}}" type="slidenum">%s<a:t>%d</a:t></a:fld>'
           '<a:r>%s<a:t> / %d</a:t></a:r>' % (sid, rpr, sid, rpr, total))

    sp_start = xml.rfind('<p:sp>', 0, r_start)
    sp_end = xml.find('</p:sp>', r_end) + len('</p:sp>')
    block = xml[sp_start:sp_end]

    block = block.replace(run, fld, 1)
    # 固定宽 + 右对齐：页码位数变化时右边缘不漂移
    block = block.replace('<a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0"/>',
                          '<a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/>', 1)
    block = re.sub(r'<a:off x="\d+" y="\d+"/><a:ext cx="\d+" cy="\d+"/>', FIXED, block, count=1)
    block = block.replace('<a:p><a:pPr><a:lnSpc>', '<a:p><a:pPr algn="r"><a:lnSpc>', 1)

    return xml[:sp_start] + block + xml[sp_end:], True


def main(path):
    z = zipfile.ZipFile(path)
    items = [(i, z.read(i.filename)) for i in z.infolist()]
    z.close()
    buf = {i.filename: d for i, d in items}

    with zipfile.ZipFile(path) as z2:
        order = slide_order(z2)
    total = len(order)

    n = 0
    for idx, name in enumerate(order, start=1):
        s = buf[name].decode('utf-8')
        s2, changed = patch_slide(s, idx, total)
        if changed:
            buf[name] = s2.encode('utf-8')
            n += 1
    print('pagenum: %d/%d slides patched (total=%d)' % (n, total, total))

    tmp = path + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zo:
        for info, data in items:
            zo.writestr(info.filename, buf[info.filename])
    os.replace(tmp, path)
    print('saved:', path)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
