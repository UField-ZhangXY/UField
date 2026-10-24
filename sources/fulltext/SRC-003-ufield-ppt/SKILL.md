---
name: ufield-ppt
agent_created: true
description: "UField 品牌 PPT 制作技能。用 U 型视觉语言（InkSeed：UField Teal #018985 × Amber #EC9804、手绘色域、U 形笔刷、发光圆点、呼吸留白）与一套母版版式库，把内容（大纲/文档/字幕/会议笔记/网页文章）生成 UField 气质一致的专业演示文稿；也支持对已有 .pptx 重新排版美化，或严格套用固定版式批量产出。当用户提到：做 PPT、生成演示文稿、UField PPT、UField 演示、套模板做 PPT、把这份文档/字幕/大纲/报告做成 PPT、美化这个 PPT、重排这个 PPT、slide、deck，且上下文涉及 UField / 她山 / 内峰 / 敦煌网 / U 型理论品牌演示时触发。工程链路：内容→结构设计→填写 slidep DSL 页面→lint 校验→写入 .pptx→python-pptx 兼容性重存→母版化减重→渲染质检。默认输出 16:9 演示文稿并附逐页渲染图。"
---

# UField PPT 制作

把内容做成一套「像 UField 自己长出来的」演示文稿：手绘色域、青绿×暖橙、U 形笔刷、呼吸留白，而不是通用模板的堆砌。

## 与内置能力的分工

- 需要**从零做 UField 品牌演示 / 套 UField 版式** → 用本 skill。
- 只是**通用 pptx 读写、或与本品牌无关的 PPT** → 用内置 `tencent-pptx`，别调本 skill。
- 需要**UField 手绘视觉单图**（不是幻灯片）→ 用 `ufield-art`；本 skill 幻灯片的配图沿用同一套 InkSeed 资产，不再另调 ufield-art。

## 三种模式（共用同一条工程链路）

| 模式 | 触发 | 输入 | 做法 |
|---|---|---|---|
| **A 内容→成品** | "把这份文档/字幕/大纲做成 PPT" | 大纲 / 文档 / srt 字幕 / 网页 / 笔记 | 提炼结构 → 选版式 → 填 DSL → 成稿 |
| **B 美化已有** | "把这个 PPT 美化/重排" | 已有 .pptx | python-pptx 抽取其文本 → 按 UField 版式重建（本质同 A，只是内容源是原 PPT） |
| **C 套版批量** | "严格套模板生成" | 结构化清单（多条内容） | 沿用固定版式，不自由发挥，批量产出品牌一致的页 |

## 每次调用先读

- [references/design-system.md](references/design-system.md) —— 配色 / 字体 / 栅格 / 侧栏元素 / 视觉资产清单 / 版式基因。**动手前必读**。
- [references/page-types.md](references/page-types.md) —— **16 种**页面版式目录、DSL 骨架、选用指南、页数规划建议。
- [references/engine-guide.md](references/engine-guide.md) —— `scripts/deck.py` / `scripts/masterize.py` 用法、引擎调用、兼容重存、母版化减重、渲染质检、**踩坑清单（必读，能省掉一轮返工）**。
- [references/content-to-deck.md](references/content-to-deck.md) —— 内容→结构的提炼方法与叙事骨架（模式 A/B 必读）。

## 自带资源

- `assets/brand/ufield_logo.png` —— 正式 Logo（透明底，比例约 1.948:1）。**每张内容页右上角放 Logo**（绝对定位统一，见 design-system）；`assets/brand/ufield_logo_shadow.png` 为**深色底专用白影版**（封面用）。
- `assets/elements/side_bar.png` —— **左侧边条**（V3 签名元素，134×1125，落位 86px 宽），内容页统一挂，其上叠两列竖排 slogan（文字层，可换）。
- `assets/visuals/` —— 手绘视觉 + 满幅底图：`cover_earth`（青绿×暖橙地球+橙U弧，主封面）、`circle_sprout`（圆相+新芽，满幅章节）、`earth_people`（地球+人群光点，结尾）、`dark_cover`（暗夜 U 谷）、`cover_u_arc`（白底 U 弧）、`art_closing`（日出丘陵）、`flow_line`（河流笔触）、`quote_figure`（望星人）、`source_diagram`（U+纵轴+横轴 三形状图）、`unity_circle`（圆相）。
- `templates/v2/` —— **16 个母版版式 DSL**（`NN_版式名.slide`，V3 版式集），是页面骨架的直接来源。
- `scripts/deck.py` —— 构建脚本（create / lint / write / finalize / render / all / doctor）。
- `scripts/masterize.py` —— **后处理脚本（V2，一步到位）**：版式化（底图/底色/侧栏/竖排 slogan/Logo 全部提升到 slideLayout 版式层）+ 页码域化（版式层普通文本框 + slidenum 域，增删页自动更新）+ 媒体减重 + 孤儿媒体清理。finalize 之后跑，需 Pillow。
- `scripts/pagenum.py` —— （legacy）旧的逐页页码域化脚本，已被 masterize 内置能力取代；仅老工程兜底用。

## 标准工作流

1. **提炼结构**：读内容，定主题、章节数、页数与叙事骨架（见 content-to-deck.md）。产出「页面清单」：每页写明 页型 + 标题 + 要点。
2. **建项目目录**：在用户工作空间下建 `<主题>-PPT/`，内含 `slides/` 与 `assets/`；把 `assets/visuals/*`、`assets/elements/*` 与 `assets/brand/*` 复制进去（幻灯片里的图片路径写 `assets/xxx.png`，相对项目目录）。
3. **写页面**：从 `templates/v2/` 复制需要的版式到 `slides/`，按 `NN_版式名.slide` **重编号**（NN 决定最终页码，从 01 起），替换占位文案。需要新视觉时，按 ufield-art 的 InkSeed 词法调 `ImageGen` 生成，**务必裁掉右下角 AI 水印**（底部裁 7–8%）。
4. **构建**：
   ```bash
   PY=<python>                                    # 任意 python
   VENV=<装了 Pillow 的 python>                    # masterize 需 Pillow（隔离 venv）
   $PY   <skill>/scripts/deck.py write    <主题>.pptx slides/
   $PY   <skill>/scripts/deck.py finalize <主题>.pptx
   $VENV <skill>/scripts/masterize.py     <主题>.pptx     # 版式化 + 页码域 + 减重（按需改 LAYOUTS 页序）
   $PY   <skill>/scripts/deck.py render   <主题>.pptx render/
   ```
   （首次或换环境时可先 `deck.py all` 走 create+lint+write+finalize。）
   ⚠️ **pptx 必须放在项目目录根（与 assets/ 同级）** —— slidep 以 pptx 所在目录解析 `assets/`，放子目录会让所有图片变成占位符。
5. **质检**：**逐页读渲染图**（用 `Read` 看 `render/pNN.png`），检查裁字、压字、图片比例、溢出、各页 Logo 是否齐平、版式化页底图/侧栏/页码是否正常。发现问题改 DSL → 重走链路 → 重 `render` 复检。
6. **交付**：`present_files` 交付 `.pptx`；清理中间产物（只删本项目内的临时 pptx/pdf/render 目录与 `.bak`，**不要删 slides/ 与 assets/**）。

## 交付约定

- 默认 **16:9**（1280×720）。内容页：左侧青绿边条 + 右上角 Logo（绝对定位统一）+ 右下角页码；封面/章节/金句/结尾等满幅/呼吸页不带边条。
- **DSL 里仍按老写法画侧栏 / Logo / 页脚 `@PAGE@ / @PAGES@`**（模板自包含、可独立预览）；`masterize` 会把它们从页面剥离并收拢到版式层 —— 同类页复制 N 份只存 1 份，改 slogan/Logo/底色只改版式一处。
- **页码 = 版式层幻灯片编号域**，在 PowerPoint/WPS 普通视图增删页时**自动更新**；**OOXML 没有「总页数」域**（微软官方确认），故页脚只显示页码、不带总页数。
- 成品必须经 `finalize`（python-pptx 重存，否则 LibreOffice/WPS 可能打不开）+ `masterize`（版式化减重）。
- 交付时用一段表格说明页型编排，并说明新生成的视觉、版式化与修复过的问题。
- 逐页渲染检查是硬要求：**未目检的页不算完成**。
- 涉及第三方字体（幼圆/方正姚体）时，提醒用户目标机器需装中文 Office，否则回退系统字体。
