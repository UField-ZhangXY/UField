# -*- coding: utf-8 -*-
"""
masterize.py — UField 模板 V3.x 后处理（在 deck.py finalize 之后运行）

做四件事：
1. 版式化：把「满幅底图 / 页面底色 / 侧栏 / 竖排 slogan / 右上 Logo / 页码」这些
   每页重复出现的东西，从页面层提升到独立的 slideLayout（版式）里。
   - 页面只留自己的内容，不再逐页复制同一张图、同一段文字；
   - 同类页（多个内容页、多个章节页）复制 N 页，底图/侧栏/Logo 只存 1 份；
   - 以后改 slogan、改 Logo、改底色，只改版式一处，全套跟着变。
2. 页码域化：页脚不再逐页画文本，改为版式上的「幻灯片编号」域
   （<a:fld type="slidenum">），在 PowerPoint/WPS 普通视图增删页时自动更新。
   注：OOXML 只有 slidenum/datetime/header/footer 四种域，没有「总页数」域
   （微软官方文档亦明确需手写固定值），因此页脚只保留页码、不保留总页数。
3. 母版配套：打开 slideMaster 的 <p:hf sldNum="1">，否则页码域不显示；
   并在 slideMaster 上补一个 sldNum 占位符（版式占位符需有母版对应项）。
4. 减重：过大位图转 JPEG q85（限边 1920）；清理已无任何引用的孤儿媒体。

用法：
  python masterize.py <某.pptx>          # 原地处理（先自动备份 .bak）
依赖：Pillow（用装好 Pillow 的 venv 解释器运行）

注意：masterize 之后不要再跑 deck.py finalize / write（会重建页面、丢失版式化结果）。
"""
import io
import os
import re
import shutil
import sys
import tempfile
import zipfile
from PIL import Image

PX = 9525
FULL_W, FULL_H = 12192000, 6858000  # 16:9 EMU

NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_CT_LAYOUT = "application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"
NS_CT_MEDIA = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".svg": "image/svg+xml",
}

# 页脚（页码）统一定位：右下角，right=48px bottom≈24px
FOOT = dict(x=11334750, y=6486525, w=400050, h=142875, sz=900)

# 侧栏里可复用的文字（版式化后改这里 → 全站内容页一起变）
SLOGANS = ["陪育商业新生态", "催化集体创造力"]

# ------------------------------------------------------------------ 版式定义
# num      版式编号（slideLayoutN.xml）
# name     版式名
# bg       页面底色：None=透明（交给底图） / ('solid','RRGGBB') / ('grad','A','B',ang)
# bgpic    满幅底图落位名（从样板页搬入版式）
# sldnum   页码颜色 (RRGGBB, alpha|None)，None = 该版式不显示页码
# sample   样板页（1 起）
# pages    挂该版式的页（1 起）
# chrome   True = 把侧栏图 + 竖排 slogan + 右上 Logo 也搬进版式
LAYOUTS = [
    dict(num=2, name="封面·满幅底图", bg=None, bgpic="bg_cover_earth",
         sldnum=None, sample=1, pages=[1]),
    dict(num=3, name="章节·满幅底图", bg=None, bgpic="bg_circle_sprout",
         sldnum=("FFFFFF", 70000), sample=5, pages=[5]),
    dict(num=4, name="转场·暗色底图", bg=None, bgpic="bg_dark_cover",
         sldnum=("FFFFFF", 60000), sample=13, pages=[13]),
    dict(num=5, name="结尾·满幅底图", bg=None, bgpic="bg_earth_people",
         sldnum=None, sample=16, pages=[16]),
    dict(num=6, name="内容页·白底+侧栏", bg=("solid", "FDFBF7"), bgpic=None,
         sldnum=("8A9296", None), sample=6, chrome=True,
         pages=[6, 7, 8, 9, 10, 11, 12, 14]),
    dict(num=7, name="呼吸页·白底", bg=("solid", "FDFBF7"), bgpic=None,
         sldnum=("8A9296", None), sample=2, pages=[2, 3, 15]),
    dict(num=8, name="章节·渐变底", bg=("grad", "0E2A47", "024A3C", 2700000), bgpic=None,
         sldnum=("FFFFFF", 60000), sample=4, pages=[4]),
]

SIDE_BAR_EXT = (819150, 6858000)     # 侧栏图 86×720
LOGO_EXT = (914400, 466725)          # 右上 Logo 96×49


# ------------------------------------------------------------------ 包操作
def unpack(pptx, d):
    with zipfile.ZipFile(pptx) as z:
        z.extractall(d)


def repack(d, pptx):
    tmp = pptx + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(d, "[Content_Types].xml"), "[Content_Types].xml")
        for root, _, files in os.walk(d):
            for f in files:
                full = os.path.join(root, f)
                arc = os.path.relpath(full, d).replace("\\", "/")
                if arc == "[Content_Types].xml":
                    continue
                z.write(full, arc)
    shutil.move(tmp, pptx)


def slide_order(d):
    """按 presentation.xml 的 sldIdLst 还原真实页序 → ['slide1.xml', ...]"""
    pres = open(os.path.join(d, "ppt", "presentation.xml"), encoding="utf-8").read()
    rels = open(os.path.join(d, "ppt", "_rels", "presentation.xml.rels"), encoding="utf-8").read()
    rid2file = dict(re.findall(
        r'<Relationship Id="(rId\d+)"[^>]*Target="slides/(slide\d+\.xml)"', rels))
    order = [rid2file[r] for r in re.findall(r'<p:sldId[^>]*r:id="(rId\d+)"', pres) if r in rid2file]
    if not order:
        order = sorted((f for f in os.listdir(os.path.join(d, "ppt", "slides"))
                        if re.match(r"slide\d+\.xml$", f)),
                       key=lambda n: int(re.search(r"(\d+)", n).group(1)))
    return order


def slide_paths(d, n):
    """页码(1 起) → (slide.xml 路径, rels 路径)"""
    fn = slide_order(d)[n - 1]
    return (os.path.join(d, "ppt", "slides", fn),
            os.path.join(d, "ppt", "slides", "_rels", fn + ".rels"))


# ------------------------------------------------------------------ XML 工具
def iter_blocks(xml, tag):
    """产出 (start, end, block) —— 仅顶层（slidep 输出无嵌套 sp/pic）"""
    for m in re.finditer(r"<%s>.*?</%s>" % (tag, tag), xml, re.S):
        yield m.start(), m.end(), m.group(0)


def all_shapes(xml):
    """把所有顶层 p:sp / p:pic 按出现顺序产出 (start, end, block)"""
    out = []
    for tag in ("p:sp", "p:pic"):
        out += list(iter_blocks(xml, tag))
    return sorted(out)


def block_rid(block):
    m = re.search(r'r:embed="(rId\d+)"', block)
    return m.group(1) if m else None


def media_target(rels, rid):
    m = re.search(r'<Relationship Id="%s"[^>]*Target="([^"]+)"' % rid, rels)
    return m.group(1) if m else None


def rel_rids(xml):
    return set(re.findall(r'r:(?:embed|id|link)="(rId\d+)"', xml))


def is_full_bg_shape(block):
    """全幅纯色/渐变矩形（slidep 给 Slide.background 画的那块，无文字）"""
    return ('cx="%d" cy="%d"' % (FULL_W, FULL_H) in block
            and "<a:t>" not in block
            and ("<a:solidFill>" in block or "<a:gradFill>" in block))


def is_footer_shape(block):
    return "@PAGE@" in block or ('type="slidenum"' in block)


def pick_block(xml, pred):
    for s, e, b in all_shapes(xml):
        if pred(b):
            return s, e, b
    return None


def drop_block(xml, block_tuple):
    s, e, b = block_tuple
    return xml[:s] + xml[e:]


# ------------------------------------------------------------------ 版式生成
def bg_xml(spec):
    return '<p:bg><p:bgRef idx="1001"><a:schemeClr val="bg1"/></p:bgRef></p:bg>'


def bg_shape_xml(spec):
    """底色矩形 → 版式层普通形状。
    注：不能写成版式 <p:bg><p:bgPr> 自定义填充 —— LibreOffice 不渲染版式层的
    自定义背景（渐变会整页变白），普通形状则与侧栏/Logo 一样可靠渲染。"""
    if not spec:
        return None
    if spec[0] == "solid":
        fill = '<a:solidFill><a:srgbClr val="%s"/></a:solidFill>' % spec[1]
    elif spec[0] == "grad":
        fill = ('<a:gradFill><a:gsLst>'
                '<a:gs pos="0"><a:srgbClr val="%s"/></a:gs>'
                '<a:gs pos="100000"><a:srgbClr val="%s"/></a:gs>'
                '</a:gsLst><a:lin ang="%d" scaled="1"/></a:gradFill>'
                % (spec[1], spec[2], spec[3]))
    else:
        raise ValueError("bad bg spec: %r" % (spec,))
    return (
        '<p:sp>'
        '<p:nvSpPr><p:cNvPr id="{id}" name="背景底色"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm rot="0" flipH="0" flipV="0"><a:off x="0" y="0"/>'
        '<a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>%s<a:ln/></p:spPr>'
        '<p:txBody><a:bodyPr/><a:p><a:pPr/><a:endParaRPr/></a:p></p:txBody>'
        '</p:sp>' % (FULL_W, FULL_H, fill))


def sldnum_xml(shape_id, color, alpha):
    """版式上的页码 = 普通文本框 + slidenum 域（微软官方 Slide Master 方案）。
    注：不用 <p:ph type="sldNum"> 占位符 —— LibreOffice 不渲染版式层占位符，
    而普通文本框 + 域在 PowerPoint 与 LibreOffice 中都会渲染并自动更新。"""
    fill = '<a:srgbClr val="%s">%s</a:srgbClr>' % (
        color, ('<a:alpha val="%d"/>' % alpha) if alpha else "")
    return (
        '<p:sp>'
        '<p:nvSpPr>'
        '<p:cNvPr id="%d" name="页码"/>'
        '<p:cNvSpPr txBox="1"/>'
        '<p:nvPr/>'
        '</p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="%d" y="%d"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0"/><a:lstStyle/>'
        '<a:p><a:pPr algn="r"><a:lnSpc><a:spcPct val="100000"/></a:lnSpc></a:pPr>'
        '<a:fld id="{{7C4A1E90-3B21-4A6E-9F55-%012d}}" type="slidenum">'
        '<a:rPr lang="en-US" sz="%d"><a:solidFill>%s</a:solidFill>'
        '<a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:rPr>'
        '<a:t>1</a:t></a:fld>'
        '<a:endParaRPr lang="zh-CN"/></a:p></p:txBody></p:sp>'
        % (shape_id, FOOT["x"], FOOT["y"], FOOT["w"], FOOT["h"], shape_id, FOOT["sz"], fill))


def renumber(block, new_id):
    return re.sub(r'id="\d+"', 'id="%d"' % new_id, block, count=1)


def make_layout_xml2(name, bg, shape_list, sldnum):
    """bg 与形状列表拼进 spTree"""
    inner = bg + "".join(shape_list) + (sldnum or "")
    return (
        "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
        '<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="%s">'
        '<p:cSld name="%s"><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '%s'
        '</p:spTree></p:cSld>'
        '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>'
    ) % (NS_R, name, inner)


# ------------------------------------------------------------------ 主流程
def main():
    pptx = sys.argv[1]
    bak = pptx + ".bak"
    shutil.copy2(pptx, bak)

    d = tempfile.mkdtemp(prefix="mst_")
    unpack(pptx, d)

    master_p = os.path.join(d, "ppt", "slideMasters", "slideMaster1.xml")
    master_rels_p = os.path.join(d, "ppt", "slideMasters", "_rels", "slideMaster1.xml.rels")
    ct_p = os.path.join(d, "[Content_Types].xml")

    master = open(master_p, encoding="utf-8").read()
    master_rels = open(master_rels_p, encoding="utf-8").read()
    ct = open(ct_p, encoding="utf-8").read()

    next_rid = max([int(x) for x in re.findall(r'Id="rId(\d+)"', master_rels)] or [0]) + 1
    next_lay_id = max([int(x) for x in re.findall(r'<p:sldLayoutId id="(\d+)"', master)] or [0]) + 1
    if next_lay_id < 2147483649:
        next_lay_id = 2147483649

    def register_layout(num):
        """把 slideLayoutN 挂进 master 并注册 Content_Types"""
        nonlocal master, master_rels, ct, next_rid, next_lay_id
        master_rels = master_rels.replace(
            "</Relationships>",
            '<Relationship Id="rId%d" Type="%s/slideLayout" Target="../slideLayouts/slideLayout%d.xml"/>'
            "</Relationships>" % (next_rid, NS_R, num))
        master = master.replace(
            "</p:sldLayoutIdLst>",
            '<p:sldLayoutId id="%d" r:id="rId%d"/></p:sldLayoutIdLst>' % (next_lay_id, next_rid))
        if 'PartName="/ppt/slideLayouts/slideLayout%d.xml"' % num not in ct:
            ct = ct.replace(
                "</Types>",
                '<Override PartName="/ppt/slideLayouts/slideLayout%d.xml" ContentType="%s"/></Types>'
                % (num, NS_CT_LAYOUT))
        next_rid += 1
        next_lay_id += 1

    for spec in LAYOUTS:
        num = spec["num"]
        lay_p = os.path.join(d, "ppt", "slideLayouts", "slideLayout%d.xml" % num)
        if os.path.exists(lay_p):
            print("  layout%d 已存在，跳过" % num)
            continue

        sp_p, sr_p = slide_paths(d, spec["sample"])
        sample = open(sp_p, encoding="utf-8").read()
        sample_rels = open(sr_p, encoding="utf-8").read()

        layout_rels = [('rId0', "%s/slideMaster" % NS_R, "../slideMasters/slideMaster1.xml")]
        shape_out = []
        sid = 2
        # 底色矩形放最底层（版式层普通形状，LO/PowerPoint 均可靠渲染）
        bgsp = bg_shape_xml(spec.get("bg"))
        if bgsp:
            shape_out.append(renumber(bgsp, sid))
            sid += 1
        used_media = {}   # 页面 media 相对路径 → 版式新名
        media_rid = {}    # 页面 media 相对路径 → 版式 rId

        def take(block, nice_name):
            """把抽出的块重映射 rId / 重编 id，登记媒体，返回新块"""
            nonlocal sid
            for rid in re.findall(r'r:embed="(rId\d+)"', block):
                target = media_target(sample_rels, rid)
                if not target:
                    continue
                if target not in used_media:
                    ext = os.path.splitext(target)[1].lower()
                    base = nice_name or ("img%d" % (len(used_media) + 1))
                    newname = base + ext
                    used_media[target] = newname
                    media_rid[target] = "rId%d" % (101 + len(used_media) - 1)
                    src = os.path.join(d, "ppt", "slides", target.replace("/", os.sep))
                    os.makedirs(os.path.join(d, "ppt", "media"), exist_ok=True)
                    shutil.copy2(src, os.path.join(d, "ppt", "media", newname))
                    layout_rels.append((media_rid[target], "%s/image" % NS_R,
                                        "../media/%s" % newname))
                block = block.replace('r:embed="%s"' % rid, 'r:embed="%s"' % media_rid[target])
            block = renumber(block, sid)
            sid += 1
            shape_out.append(block)
            return block

        # a) 满幅底图
        if spec.get("bgpic"):
            hit = pick_block(sample, lambda b: b.startswith("<p:pic>")
                             and 'cx="%d" cy="%d"' % (FULL_W, FULL_H) in b)
            assert hit, "第 %d 页未找到满幅底图" % spec["sample"]
            take(hit[2], spec["bgpic"])

        # b) 侧栏图 + 竖排 slogan + 右上 Logo
        if spec.get("chrome"):
            hit = pick_block(sample, lambda b: b.startswith("<p:pic>")
                             and 'cx="%d" cy="%d"' % SIDE_BAR_EXT in b)
            assert hit, "第 %d 页未找到侧栏图" % spec["sample"]
            take(hit[2], "side_bar")
            for txt in SLOGANS:
                hit = pick_block(sample, lambda b, t=txt: b.startswith("<p:sp>")
                                 and "<a:t>%s</a:t>" % t in b)
                assert hit, "第 %d 页未找到 slogan「%s」" % (spec["sample"], txt)
                take(hit[2], None)
            hit = pick_block(sample, lambda b: b.startswith("<p:pic>")
                             and 'cx="%d" cy="%d"' % LOGO_EXT in b)
            assert hit, "第 %d 页未找到 Logo" % spec["sample"]
            take(hit[2], "ufield_logo")

        # c) 页码域
        sn = spec.get("sldnum")
        sn_xml = sldnum_xml(sid, sn[0], sn[1]) if sn else None

        open(lay_p, "w", encoding="utf-8").write(
            make_layout_xml2(spec["name"], bg_xml(spec.get("bg")), shape_out, sn_xml))
        seen, rels_clean = set(), []
        for r in layout_rels:
            if r[0] in seen:
                continue
            seen.add(r[0])
            rels_clean.append(r)
        rels_items = "".join('<Relationship Id="%s" Type="%s" Target="%s"/>' % r for r in rels_clean)
        open(lay_p.replace(os.sep + "slideLayouts" + os.sep,
                           os.sep + "slideLayouts" + os.sep + "_rels" + os.sep) + ".rels",
             "w", encoding="utf-8").write(
            "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '%s</Relationships>' % rels_items)
        register_layout(num)

        # d) 逐页剥离 + 换版式
        for pg in spec["pages"]:
            sp, srp = slide_paths(d, pg)
            xml = open(sp, encoding="utf-8").read()
            rels = open(srp, encoding="utf-8").read()

            # 收集本页要换的 slideLayout 关系
            lay_old = re.search(r'Type="%s/slideLayout" Target="([^"]+)"' % NS_R, rels)
            removed = []
            # 满幅页：搬走底图
            if spec.get("bgpic"):
                hit = pick_block(xml, lambda b: b.startswith("<p:pic>")
                                 and 'cx="%d" cy="%d"' % (FULL_W, FULL_H) in b)
                if hit:
                    xml = drop_block(xml, hit)
                    removed += re.findall(r'r:embed="(rId\d+)"', hit[2])
            # 底色矩形
            hit = pick_block(xml, is_full_bg_shape)
            if hit:
                xml = drop_block(xml, hit)
            # 侧栏 / slogan / Logo（循环删，同类元素可能不止一个）
            if spec.get("chrome"):
                preds = (
                    lambda b: b.startswith("<p:pic>") and 'cx="%d" cy="%d"' % SIDE_BAR_EXT in b,
                    lambda b: b.startswith("<p:pic>") and 'cx="%d" cy="%d"' % LOGO_EXT in b,
                    lambda b: b.startswith("<p:sp>") and any("<a:t>%s</a:t>" % t in b for t in SLOGANS),
                )
                for pred in preds:
                    while True:
                        hit = pick_block(xml, pred)
                        if not hit:
                            break
                        xml = drop_block(xml, hit)
                        removed += re.findall(r'r:embed="(rId\d+)"', hit[2])
            # 页脚
            hit = pick_block(xml, is_footer_shape)
            if hit:
                xml = drop_block(xml, hit)

            for rid in removed:
                rels = re.sub(r'<Relationship Id="%s"[^>]*/>' % rid, "", rels)
            if lay_old:
                rels = rels.replace(lay_old.group(1), "../slideLayouts/slideLayout%d.xml" % num)
            open(sp, "w", encoding="utf-8").write(xml)
            open(srp, "w", encoding="utf-8").write(rels)

        print("  slideLayout%d「%s」← 第%s页（%d 页挂载）"
              % (num, spec["name"], ",".join(map(str, spec["pages"])), len(spec["pages"])))

    # ---------- 3. 母版：打开页码域开关 ----------
    # （页码本体放在各版式上，为普通文本框+域，无需母版占位符）
    master = re.sub(r'<p:hf sldNum="0"', '<p:hf sldNum="1"', master)

    open(master_rels_p, "w", encoding="utf-8").write(master_rels)
    open(master_p, "w", encoding="utf-8").write(master)
    open(ct_p, "w", encoding="utf-8").write(ct)

    # ---------- 4. 孤儿媒体清理 + 减重 ----------
    referenced = set()
    for root, _, files in os.walk(d):
        for f in files:
            if not f.endswith(".rels"):
                continue
            s = open(os.path.join(root, f), encoding="utf-8").read()
            referenced |= set(re.findall(r'Target="(?:\.\./)*media/([^"]+)"', s))

    orphans = 0
    for sub in ("media", os.path.join("slides", "media")):
        sdir = os.path.join(d, "ppt", sub)
        if not os.path.isdir(sdir):
            continue
        for f in os.listdir(sdir):
            if f == "":
                continue
            if f not in referenced:
                os.remove(os.path.join(sdir, f))
                orphans += 1
    if orphans:
        print("  清理孤儿媒体 %d 个" % orphans)

    saved = 0
    targets = []
    for sub in ("media", os.path.join("slides", "media")):
        sdir = os.path.join(d, "ppt", sub)
        if os.path.isdir(sdir):
            targets += [os.path.join(sdir, f) for f in os.listdir(sdir)]

    for p in targets:
        if not p.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        size = os.path.getsize(p)
        if size < 250 * 1024:
            continue
        try:
            im = Image.open(p)
        except Exception:
            continue
        try:
            if p.lower().endswith(".png"):
                has_alpha = False
                if im.mode == "RGBA":
                    lo, _ = im.getchannel("A").getextrema()
                    has_alpha = lo < 255
                if not has_alpha:
                    if max(im.size) > 1920:
                        im.thumbnail((1920, 1920), Image.LANCZOS)
                    buf = io.BytesIO()
                    im.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
                    newp = os.path.splitext(p)[0] + ".jpg"
                    with open(newp, "wb") as f:
                        f.write(buf.getvalue())
                    os.remove(p)
                    _retarget(d, os.path.basename(p), os.path.basename(newp))
                    saved += size - os.path.getsize(newp)
                    print("  %s (%.0fKB) -> %s (%.0fKB)" % (
                        os.path.basename(p), size / 1024,
                        os.path.basename(newp), os.path.getsize(newp) / 1024))
                elif size > 800 * 1024:
                    if max(im.size) > 1536:
                        im.thumbnail((1536, 1536), Image.LANCZOS)
                        buf = io.BytesIO()
                        im.save(buf, "PNG", optimize=True)
                        if buf.tell() < size:
                            with open(p, "wb") as f:
                                f.write(buf.getvalue())
                            saved += size - buf.tell()
                            print("  %s 缩至 %dx%d (%.0fKB)" % (
                                os.path.basename(p), im.width, im.height, buf.tell() / 1024))
            else:
                if max(im.size) > 1920:
                    im.thumbnail((1920, 1920), Image.LANCZOS)
                buf = io.BytesIO()
                im.save(buf, "JPEG", quality=85, optimize=True)
                if buf.tell() < size * 0.9:
                    with open(p, "wb") as f:
                        f.write(buf.getvalue())
                    saved += size - buf.tell()
                    print("  %s 重压 (%.0fKB -> %.0fKB)" % (
                        os.path.basename(p), size / 1024, buf.tell() / 1024))
        except Exception as e:
            print("  ! 跳过 %s: %s" % (os.path.basename(p), e))

    repack(d, pptx)
    shutil.rmtree(d, ignore_errors=True)
    print("完成：省 %.1f MB，备份在 %s" % (saved / 1048576, bak))


def _retarget(d, old, new):
    for root, _, files in os.walk(d):
        for f in files:
            if not f.endswith(".rels"):
                continue
            p = os.path.join(root, f)
            s = open(p, encoding="utf-8").read()
            if old in s:
                open(p, "w", encoding="utf-8").write(s.replace(old, new))


if __name__ == "__main__":
    main()
