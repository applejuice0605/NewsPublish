# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- feat(notification): 支持飞书推送卡片自动折叠功能
  - 当单批次推送内容超过 1000 字符时，自动使用 `collapsible_panel` 组件折叠内容
  - 优化超长内容的阅读体验，默认显示摘要提示，点击展开查看完整内容

### Changed
- config(ai_analysis): 默认关闭 RSS 和独立展示区的 AI 分析，节省 Token 并精简报告内容
