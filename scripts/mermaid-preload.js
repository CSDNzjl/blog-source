/**
 * 仅对真正含 Mermaid 图的页面做 preload，与正文解析并行下载本地脚本。
 * 注意：不能匹配 mermaid-wrap / mermaid-src，主题脚本字符串里也有这些字样。
 */
'use strict'

hexo.extend.filter.register('after_render:html', (str) => {
  if (!str.includes('code class="highlight mermaid"') && !str.includes('class="mermaid-wrap"')) {
    return str
  }
  if (str.includes('rel="preload" href="/js/mermaid.min.js"')) {
    return str
  }
  return str.replace(
    '</head>',
    '<link rel="preload" href="/js/mermaid.min.js" as="script">\n</head>'
  )
})
