# 引擎指南与踩坑清单

## 一、构建脚本 `scripts/deck.py`

统一封装了引擎调用与兼容处理，**优先用它，不要手敲引擎命令**。

```bash
PY=C:/Users/ZhangXiaoyong/.workbuddy/binaries/python/versions/3.13.12/python.exe   # 任意 python 即可
$PY <skill>/scripts/deck.py doctor                          # 先跑一次，确认引擎/工具都在
$PY <skill>/scripts/deck.py all   <主题>.pptx slides/       # create → lint → write → finalize
$PY <skill>/scripts/deck.py render <主题>.pptx render/      # 渲染逐页 png 供目检
```

**V3 起完整链路**（finalize 之后一步 masterize，见第四节）：

```bash
$PY <skill>/scripts/deck.py write    <主题>.pptx slides/     # 写页
$PY <skill>/scripts/deck.py finalize <主题>.pptx             # 兼容重存
$VENV_PY <skill>/scripts/masterize.py <主题>.pptx            # 版式化 + 页码域 + 减重（需 Pillow 的 venv 解释器）
$PY <skill>/scripts/deck.py render   <主题>.pptx render/     # 渲染目检
```

单步子命令：`create` / `lint` / `write` / `finalize` / `render`。全部在**项目目录**下执行（含 `slides/` 与 `assets/`）。

- 页码 = slide 文件名前导数字 − 1（`01_x.slide` → index 0）。重编号即调整顺序。
- `finalize` 用 python-pptx 原地重存，**产出全平台兼容包**（Office / WPS / LibreOffice）。
- `render` 不删除任何文件，输出 `render/pNN.png` 供 `Read` 目检。
- ⚠️ **pptx 必须放在项目目录根（与 assets/ 同级）**，见踩坑 16。

## 二、底层引擎（deck.py 已封装，了解即可）

渲染引擎是 `@tencent/slidep`，DSL 为 JSX 风格：

```jsx
<Slide style={{ width: 1280, height: 720, background: '#FDFBF7', position: 'relative', padding: 48 }}>
  <Text style={{ fontSize: 30, fontWeight: 'bold', color: '#3D4A4F' }}>标题</Text>
  <Box style={{ flexDirection: 'row', gap: 32 }}>
    <Image src='assets/xxx.png' style={{ width: 560, height: 400, objectFit: 'cover', borderRadius: 16 }} />
  </Box>
</Slide>
```

- 组件：`Slide`（根）/ `Box`（容器）/ `Text` / `Image` / `FAIcon`（FontAwesome 图标，`name` + `fill`）/ `Svg`（内联 SVG，可直接写 `<svg>` 子元素）。
- style 是 React 内联样式对象：camelCase 键、数值可写数字或带单位字符串；支持 `flexDirection` / `gap` / `justifyContent` / `alignItems` / `position` / `boxShadow` / `textShadow` / 线性渐变 `background`。
- 图片路径相对**项目目录**写 `assets/xxx.png`。

## 三、踩坑清单（必读，能省一轮返工）

1. **slidep 启动 shim 可能失效** —— 不要用 `slidep` 命令，直接跑 `@tencent/slidep/dist/index.js`（deck.py 已自动定位）。
2. **slidep 原始包 LibreOffice/WPS 打不开** —— 必须 `finalize`（python-pptx 重存）后再交付。
3. **LibreOffice 转不动 slidep 原始包** —— `render` 前先 `finalize`，否则 PDF 转换失败。
4. **小字号 + `letterSpacing` 会被裁字**（双端各切掉一两个字符）——**≤15px 的文字一律不加 letterSpacing**；居中文本、无显式宽度的绝对定位文本都不能加。大标题（≥40px）加字距是安全的。
5. **`Image` 只给 `width` 不给 `height` 会被渲染成巨型图** —— 宽高必须成对给。
6. **子元素超出父容器** → `lint` 报 `child-containment` 错误 —— 图片尺寸要 ≤ 容器尺寸；若容器内还有图注文字，图片高度要再留出图注的 ~30px。
7. **预检不过就不写** —— `lint` 有 error 时先改 DSL，别急着 `write`（写入会失败或产出坏页）。
8. **预览面板可能锁住 pptx** —— 若转换报「文件被占用」，复制一份副本再转。
9. **水印** —— 新用 `ImageGen` 生成的图右下角有「AI生成」水印，裁掉底部 7–8% 再用。
10. **`lineHeight` 是倍率，且实际行距 = `1.2 × fontSize × lineHeight`** —— 比 `fontSize × lineHeight` 大 20%（引擎默认行距系数 1.2）。排竖排文字、紧凑行间距时**按渲染实测回正**（用 Pillow 量渲染图上字形的实际范围，别只凭公式）。
11. **内容页右上角 Logo 必须绝对定位统一** —— 放进页头 flex 行时，带副标题的页会把 Logo 撑低约 10px，导致各页 Logo 高低不齐。统一写 `position:'absolute', top:38, right:44`（96×49）。
12. **深色底 Logo 用 `ufield_logo_shadow.png`（白影版），不要白色胶囊衬底** —— 白影按字形轮廓错位柔化，是 C3 封面同款效果；胶囊会显得笨重。
13. **母版化/减重（masterize）之后不要再 `finalize` / `write`** —— 会重建页面、丢掉版式（layout）层底图。要改内容就从完整链路重跑一遍（见第四节）。
14. **页码必须走域，不要写死数字** —— DSL 页脚写 `@PAGE@ / @PAGES@`（或干脆不写页脚），masterize 会把它替换/收拢为**版式层页码域**，用户在普通视图增删页后页码自动变。
15. **slidep 把 DSL 源码转义存进页面 descr 属性** —— 在 XML 里查找/替换任何页脚标记时必须带 XML 标签（如 `<a:t>@PAGE@ / @PAGES@</a:t>`），纯文本会误命中转义源码，把替换打在错误位置。
16. **pptx 必须放在项目目录根（与 assets/ 同级）** —— slidep 以 **pptx 所在目录**为基准解析 `assets/xxx.png`；把 pptx 放进子目录（如 `_build/`）后所有图片解析失败，会**静默变成灰色占位 SVG**（ lint 不报错！）。排查特征：包内 media 全是 1KB 左右的 svg。
17. **版式（slideLayout）层的自定义 `<p:bg><p:bgPr>` 背景 LibreOffice 不渲染** —— 渐变章节页会整页变白、白字消失。底色一律用**版式层普通形状**（全幅矩形 + solidFill/gradFill）承载。
18. **版式层页码不能用 `<p:ph type="sldNum">` 占位符** —— LibreOffice 不渲染版式层占位符（页码会消失）；要用**普通文本框 + `<a:fld type="slidenum">` 域**（微软官方 Slide Master 方案，PowerPoint 与 LibreOffice 双端渲染且增删页自动更新）。
19. **OOXML 没有「总页数」域** —— 域只有 slidenum/datetime/header/footer 四种（微软官方文档明确：总页数需手写固定值）。Word 的 `{ numpages }` 在 PPT 里不可用。故页脚只显示页码、不带总页数。
20. **版式化（masterize）之后不要再 finalize / write** —— 会重建页面、丢失版式层结果。要改内容就从完整链路重跑。

## 三·五、页码域化 `scripts/pagenum.py`（legacy，已被 masterize 取代）

> **V3.1 起 masterize 已内置页码域化**（版式层普通文本框 + slidenum 域），新链路不再需要跑本脚本；仅老工程（不跑 masterize）兜底用。

在 `finalize` 之后运行：

```bash
$PY <skill>/scripts/pagenum.py <主题>.pptx     # @PAGE@/@PAGES@ → 页码域
```

- **页码** = `<a:fld type="slidenum">` 域 → 用户在 PowerPoint/WPS 普通视图增删页时**自动更新**；
- **总页数** = 构建时的幻灯片总数（静态文本）。PowerPoint **没有"总页数"域**（OOXML 域只有 slidenum/datetime/header/footer，微软官方确认需手写固定值）；
- 文本框同时改为**固定宽度 + 右对齐**，页码 1 位/2 位数时右边缘不漂移；
- 无标记的页（封面/结尾）自动跳过。

## 四、版式化与减重 `scripts/masterize.py`（V2）

在 `finalize` 之后运行，**四件事**：

1. **版式化**：把每页重复出现的东西提升到**独立 slideLayout（版式）**，页面只留自己的内容 ——
   - 4 个满幅底图版式（封面 / 满幅章节 / 暗色转场 / 结尾）；
   - **「内容页·白底+侧栏」版式**：暖白底 `#FDFBF7` + 侧栏图 + 两列竖排 slogan + 右上 Logo，挂全部内容页（8 页）—— 以后改 slogan、换 Logo、调底色只改版式一处；
   - **「呼吸页·白底」版式**（白底+页码）与**「章节·渐变底」版式**（渐变矩形+页码）。
   页面里的底色矩形、侧栏、slogan、Logo、页脚会被同步剥离；孤儿媒体一并清理。
2. **页码域化**：各版式上放**普通文本框 + `<a:fld type="slidenum">` 域**（颜色随版式：内容/呼吸页灰 `#8A9296`、深色页白），PowerPoint/WPS 普通视图增删页自动更新；同时把 slideMaster 的 `<p:hf sldNum="0">` 打开为 `"1"`。
   注：**不用** `<p:ph type="sldNum">` 占位符（LibreOffice 不渲染版式层占位符，见踩坑 18）。
3. **媒体减重**：包内 >250KB 的不透明位图转 **JPEG q85**（限边 1920）；带透明的大 PNG 等比缩小。
4. **孤儿媒体清理**：删除已无任何 rels 引用的图片。

```bash
VENV_PY=C:/Users/ZhangXiaoyong/.workbuddy/binaries/python/envs/default/Scripts/python.exe   # 装了 Pillow 的 venv
$VENV_PY <skill>/scripts/masterize.py <主题>.pptx        # 原地处理，自动备份 .bak
```

- **依赖 Pillow**，务必用装了 Pillow 的解释器（隔离 venv），系统 python 无 PIL。
- **脚本按页序硬编码**（`LAYOUTS`：sample=样板页、pages=挂载页列表、bg=底色、sldnum=页码颜色、chrome=是否收拢侧栏/Logo）。**换页序或换版式时，先改 `LAYOUTS`**，再跑。
- 处理完删掉 `.bak`；确认版式底图/侧栏/页码正常显示后再交付。

## 五、质检流程（硬要求）

```bash
$PY <skill>/scripts/deck.py render <主题>.pptx render/
```

然后**逐页 `Read` 看 `render/pNN.png`**，逐项检查：

- [ ] 有没有**裁字/断字**（重点看小字、居中字、落款）
- [ ] 有没有**压字**（文字叠在图/笔触上）
- [ ] 图片**比例是否失真**（方图用 contain、横图用 cover）
- [ ] 有没有**元素溢出**页面或与页脚/Logo 打架
- [ ] 深色页文字是否**够亮可读**
- [ ] **内容页 Logo 是否各页齐平**（顶部对齐同一条 y）
- [ ] **版式化页**（封面/章节/转场/结尾 + 全部内容页）底图 / 侧栏 / 竖排 slogan / 页码是否正常显示（masterize 后必查）
- [ ] **页码**是否出现在各页右下角（版式层域；封面/结尾页无页码属正常）

发现问题 → 改 `slides/*.slide` → 从完整链路重跑（write → finalize → masterize → render）复检。**未目检的页不算完成。**
