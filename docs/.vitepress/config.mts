import { defineConfig } from 'vitepress'

const base = process.env.DOCS_BASE || '/'

export default defineConfig({
  lang: 'zh-CN',
  title: 'PaperSeek',
  description: 'LLM based Literature Search Agent',
  base,
  cleanUrls: true,
  lastUpdated: true,
  markdown: {
    lineNumbers: true
  },
  head: [
    ['link', { rel: 'icon', href: '/paperseek-mark.png' }],
    ['meta', { name: 'theme-color', content: '#0f172a' }],
    ['meta', { property: 'og:title', content: 'PaperSeek Docs' }],
    ['meta', { property: 'og:description', content: 'Natural language literature search with PaperSeek.' }]
  ],
  themeConfig: {
    siteTitle: 'PaperSeek Docs',
    logo: '/paperseek-mark.png',
    search: {
      provider: 'local'
    },
    nav: [
      { text: '首页', link: '/' },
      { text: '开源版手册', link: '/user-manual' },
      { text: '在线版手册', link: '/online-demo' },
      { text: '部署', link: '/deployment' },
      { text: 'GitHub', link: 'https://github.com/MingfengHong/paperseek' }
    ],
    sidebar: [
      {
        text: '开始',
        items: [
          { text: '文档站首页', link: '/' },
          { text: '开源版完整用户手册', link: '/user-manual' },
          { text: '在线体验版用户手册', link: '/online-demo' }
        ]
      },
      {
        text: '使用与部署',
        items: [
          { text: '部署指南', link: '/deployment' }
        ]
      },
      {
        text: '社区维护',
        items: [
          { text: '文档站维护说明', link: '/site-maintenance' }
        ]
      }
    ],
    socialLinks: [
      { icon: 'github', link: 'https://github.com/MingfengHong/paperseek' }
    ],
    footer: {
      message: 'Released under the Apache-2.0 License.',
      copyright: 'Copyright © 2026 MingfengHong'
    },
    editLink: {
      pattern: 'https://github.com/MingfengHong/paperseek/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页'
    },
    lastUpdated: {
      text: '最后更新'
    },
    docFooter: {
      prev: '上一页',
      next: '下一页'
    },
    outline: {
      label: '本页目录',
      level: [2, 3]
    },
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    darkModeSwitchLabel: '外观',
    lightModeSwitchTitle: '切换到浅色模式',
    darkModeSwitchTitle: '切换到深色模式'
  }
})
