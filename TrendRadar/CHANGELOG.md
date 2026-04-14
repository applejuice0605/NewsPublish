# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- feat(notification): 支持飞书推送卡片自动折叠功能
  - 当单批次推送内容超过 1000 字符时，自动使用 `collapsible_panel` 组件折叠内容
  - 优化超长内容的阅读体验，默认显示摘要提示，点击展开查看完整内容

### Changed
- config(ai_analysis): 默认关闭 RSS 和独立展示区的 AI 分析，节省 Token 并精简报告内容

### Fixed
- ci(actions): GitHub Actions 安装依赖失败（找不到满足 `litellm>=1.57.0,<2.0.0` 的发行版）
  - 将运行环境 Python 版本从 3.10 提升至 3.11，以匹配上游 litellm 的 `Requires-Python` 要求
  - 保持 `TrendRadar/requirements.txt` 约束不变，避免破坏既有 API 行为
- schedule(timeline): 修复晚间汇总（晚报）因 GitHub Actions 延迟导致无法触发的问题
  - 延长 `evening_summary` 推送窗口至 23:59
  - 同步调整 `deep_quiet` 开始时间至 00:00，避免时间段冲突
- fix(notification): 修复飞书推送卡片“展开全文”功能失效及语法错误
  - 恢复 `collapsible_panel` 折叠面板逻辑，支持超长内容自动折叠
  - 修复 `is_flow_webhook = false` 导致的 Python 语法错误
  - 统一并优化飞书卡片 1.0 与 2.0 格式的标题显示
- feat(rss): 新增微信 RSS 订阅源
  - 开启全局 RSS 抓取功能
  - 添加 `WeChat RSS` 订阅配置
  - 开启推送通知中的 RSS 区域显示
