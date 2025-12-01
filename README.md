# NewsPublish / TrendRadar

一个用于聚合多平台热点并推送到飞书/钉钉/企业微信等渠道的自动化工具，支持本地运行与 GitHub Actions 定时任务。

## 快速开始
- 安装依赖：`python -m pip install -r TrendRadar/requirements.txt`
- 本地运行：`python TrendRadar/main.py`
- 生成的报告在 `TrendRadar/output/` 与 `output/` 目录（已在 `.gitignore` 忽略）

## 配置说明
- 主配置文件：`TrendRadar/config/config.yaml`
- 关键项：
  - `report.mode`: 选择推送模式，`current` / `daily` / `incremental`
  - `notification.push_window`: 推送时间窗口（北京时间），不在窗口将跳过推送
  - `feishu_message_type`: 飞书消息类型，支持 `card`（交互卡片）、`post`、`text`
  - 展示上限：`feishu_top_n_per_group`（当前榜单）、`feishu_top_n_incremental`（新增）、`feishu_top_n_daily`（当日汇总）
  - 链接显示阈值：`feishu_current_link_threshold`（current 模式总展示条数大于此值才显示“打开完整报告”）

## 环境变量优先（不在仓库存放真实链接）
- 程序已优先读取环境变量以避免在仓库中暴露真实 webhook：
  - `FEISHU_WEBHOOK_URL`
  - `DINGTALK_WEBHOOK_URL`
  - `WEWORK_WEBHOOK_URL`
- 本地临时验证（PowerShell）：
  - 设置：`$env:FEISHU_WEBHOOK_URL="<你的飞书Webhook>"`
  - 关闭时间窗口便于测试：`$env:PUSH_WINDOW_ENABLED="false"`
  - 运行：`python TrendRadar/main.py`
- 本地永久设置（当前用户）：
  - `[Environment]::SetEnvironmentVariable("FEISHU_WEBHOOK_URL","<你的飞书Webhook>","User")`

## GitHub Actions 定时
- 工作流文件：`.github/workflows/schedule.yml`
- 定时表达式使用 UTC；当前设置为每天北京时间 10:30（UTC 02:30）：`cron: "30 2 * * *"`
- 通过仓库 Secrets 注入 webhook：
  - `FEISHU_WEBHOOK_URL`（可选：`DINGTALK_WEBHOOK_URL`、`WEWORK_WEBHOOK_URL`）
- 手动触发：在 Actions 页面选择工作流并点击 `Run workflow`
- 并发与重复：建议开启 `notification.push_window.once_per_day: true`，避免时间窗口内多次推送；如需并发控制可在工作流添加 `concurrency`。

## 频率词规则
- 文件：`TrendRadar/config/frequency_words.txt`
- 语法：
  - 普通词：每行一个词；匹配任意包含该词的标题
  - 必须词：行首 `+`，同一组内所有必须词都需命中
  - 过滤词：行首 `!`，命中即排除该标题
- 匹配逻辑：
  - 中文采用“包含匹配”
  - 英文采用“单词边界匹配”例如 `\bai\b`，避免误命中子串（如 `ananhaid` 不再命中 `AI`）
  - 松散模式：`report.match_loose_mode` 为 `true` 时会做规范化去除空格/标点以提升召回

## 常见问题
- 提示“通知功能已启用但未配置任何通知渠道”：未注入任何 webhook。请通过环境变量或 Secrets 配置 `FEISHU_WEBHOOK_URL` 等。
- “不在推送时间窗口，跳过推送”：请调整 `notification.push_window.time_range` 或临时设置 `PUSH_WINDOW_ENABLED=false`。
- 飞书按钮“不显示”：current 模式下总展示条数不超过 `feishu_current_link_threshold`（默认 20）。超过才显示“打开完整报告”。
- GitHub 定时未触发：定时使用 UTC 时间并有抖动；确认工作流在默认分支且 Actions 已启用，可先手动 `Run workflow` 验证。

## 版本与安全
- 不在仓库中保存真实 webhook；一律通过环境变量或 Secrets 注入。
- 若误提交过真实链接，建议在对应平台重置或更换 webhook。
