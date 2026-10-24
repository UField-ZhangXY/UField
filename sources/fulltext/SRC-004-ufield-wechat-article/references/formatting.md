# Codex 排版与交付

## 工具选择

优先查找工作区 `writing/xiaohu-wechat-format-main/`、`xiaohu-wechat-format-main/`。存在则先读脚本帮助和配置，确认实际支持的主题、输出位置和依赖，不假定有 30 个主题或固定输出 `/tmp/wechat-format/`。
默认建议 mint-fresh，其次 magazine、bytedance；主题必须最终落实 UField 配色与字号，不能把主题原色盖过品牌。无需每次让用户选主题。
若工具不存在，可用可用的 Markdown 解析器加内联样式生成纯文章 HTML 和 clean 预览；如依赖受阻，保留 Markdown 并报告 HTML 未完成。不要套用 Linux 的 `--break-system-packages`、`python3` 或 `/tmp` 到 Windows。优先现有/内置运行环境。
只在必要时安装缺失依赖，不改无关全局配置。所有新文件用 UTF-8，shell 参数用实际平台安全传参。

## SVG 与图片

1. 原创 SVG 前后留空行。根元素 `width="100%" viewBox="0 0 W H"`，style 白底与圆角；第一个图形为覆盖全图的白色 rect。主文字高对比，至少 12px。
2. Markdown 转 HTML 前提取 SVG，以 `<!-- SVGHOLD0 -->` 等注释占位，转换后回填。不要用双下划线占位符。先确认解析器保留注释；不保留时换可靠处理方式。
3. 用支持嵌套结构的 HTML 解析方法定位节点，不用脆弱的正则从 preview 提取整篇文章。SVG 本体用 XML 解析验证。
4. 回填 wrapper：白底 section、圆角、居中、上下边距，并加 `data-darkmode-bgcolor="#ffffff" data-darkmode-color="#222222"`。检查 article.html 和 clean.html 都已回填、没有残留占位符。
5. 暗色模式属性只是兼容措施，实际表现取决于客户端，不声称三重白底绝对保证显示。
6. 本地图片路径不能直接变成公众号在线图；说明需要上传后台。SVG 粘贴可能被过滤，必要时另附清晰 PNG，保留可编辑 SVG。不伪称已在微信后台验证。

## HTML

- Markdown 先转结构，再应用内联样式；不把 YAML frontmatter 当正文。正文 p 16px、line-height 1.9、color #222。其余层级遵循版式参考，辅助说明段允许 13px。
- 链接、列表、表格、callout 需检查转换结果。微信不适用的外链可转来源说明/脚注，保留原始地址；长表在手机端优先拆成卡片。
- 文章片段 article.html 不含脚本、工具栏或预览壳。不要因为预览需要 JavaScript 就把脚本放进待粘贴文章。
- clean.html 只渲染一次正文，唯一文章容器 `id="wechatHtml"`；不另设屏幕外复制区，也不放一份隐藏文章。
- 复制按钮只复制文章容器。优先 ClipboardItem，同时提供 text/html 与 text/plain；成功后不再走第二条复制路径。API 失败或不可用时，选中文章容器再执行可用的复制回退；失败则保留选区提示手动复制。
- 不建议全页面 Ctrl+A：会选到工具栏与提示。手动回退应选中文章区域。不要声称本地 file:// 的 Clipboard API 一定可用。
- 预览以约 375–415px 手机宽度为主，同时测试 320px 无横向溢出；工具栏不是文章内容。

## 验证与交付

运行自带 check_article.py 检查基础结构、引用与 SVG；再用可用浏览器检查排版、图表、图片与复制范围。微信后台未实际验证时如实说明该项未验证，文件不标为已发布。
交付绝对文件路径链接：`[查看推文](<绝对路径/日期-slug-clean.html>)` 与 `[Markdown 源文件](<绝对路径/日期-slug.md>)`。必要时提供 article.html、图片文件夹；优先 clean 而非原格式器 preview。
