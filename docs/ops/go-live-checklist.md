# aipaneladmin 上线检查表（Go-Live Checklist）

> 配套文档：[grayscale-monitoring-checklist.md](grayscale-monitoring-checklist.md)（监控配置清单）
> 溯源：T15 节点 5 测试总结——部署硬约束 H-1~H-3、灰度策略、遗留跟踪项

---

## 一、部署前硬约束核查（不满足不得进入灰度）

| # | 检查项 | 通过标准 | 核查方式 | 状态 |
|---|---|---|---|---|
| 1 | H-1 单 worker | `UVICORN_WORKERS=1` 且启动日志 `Worker 数量: 1`；preflight 无 H-1 告警 | `docker compose up` 后查 app 日志 | ☐ |
| 2 | H-2 Redis 启用 | 挂载的 `config.conf` 中 `redis.enabled=true`、`host=redis`；preflight Redis 可达无告警 | app 日志 `Redis连接成功` | ☐ |
| 3 | H-2 进程内降级消除 | 启动日志**无**「Redis已禁用或模块未安装」「将使用数据库直接查询」字样 | app 日志检索 | ☐ |
| 4 | H-3 网关超时 | nginx `proxy_buffering off` + `proxy_read_timeout ≥ 30s` 生效 | `nginx -T` 输出核查 | ☐ |
| 5 | H-3 SSE 实测 | HITL 长暂停用例（timeout_minutes=5）经 nginx 访问，60s 不断连且收到 `: ping` 心跳帧 | 复跑 tests/_t15_diag_hitl2.py 改 BASE 指向网关 | ☐ |
| 6 | 严格自检 | `DEPLOY_ENV=docker` 下故意置 `redis.enabled=false` 启动 → 进程 exit 2 拒绝启动（验证后恢复） | 预演一次 | ☐ |
| 7 | 敏感配置 | `deploy/app/config.conf`、`.env` 未提交仓库；`.gitignore` 已覆盖 | `git status` + `git check-ignore` | ☐ |

## 二、监控接入核查

| # | 检查项 | 通过标准 | 状态 |
|---|---|---|---|
| 8 | Prometheus 抓取 | `up{job="aipanel"} == 1`；`quota_reject_total`/`concurrent_runs`/`force_finalize_total`/`node_settle_failure_total` 可查 | ☐ |
| 9 | 告警规则加载 | `deploy/prometheus/alert_rules.yml` 5 条规则在 Prometheus UI Rules 页可见且无语法错误 | ☐ |
| 10 | Alertmanager 通道 | 触发一次测试告警（如临时改阈值）确认送达通知通道 | ☐ |
| 11 | 巡检脚本调度 | J-1~J-4 crontab 已配置（5min/02:00/09:00/03:00），手动各跑一次确认退出码与 `reports/ops/` 落盘 | ☐ |
| 12 | 审计日报基线 | `audit_report.py` 首日运行留存基线占比（供环比） | ☐ |

## 三、灰度晋级核对（每阶段晋级前逐项确认）

| # | 检查项 | 通过标准 | 阶段 1→2 | 阶段 2→3 |
|---|---|---|---|---|
| 13 | P0/P1 告警 | 阶段内零触发 | ☐ | ☐ |
| 14 | 僵尸巡检 | J-1 每日零异常 | ☐ | ☐ |
| 15 | 配额对账 | J-2 每日差异 = 0 | ☐ | ☐ |
| 16 | 审计占比 | M-5 占比无环比突增（>20pp） | ☐ | ☐ |
| 17 | 42901 拒绝率 | M-3 无异常抬升 | ☐ | ☐ |
| 18 | HITL 人工抽测 | 暂停/恢复/超时 approve/断开自愈 四路径手工验证通过 | ☐ | ☐ |

## 四、回退预案

| 触发条件 | 动作 |
|---|---|
| 任一 P0 告警且 30min 未定位 | 回退上一灰度阶段（缩量/下架），缺陷回流测试智能体复测通道 |
| M-1 僵尸实例出现 | 人工 DB 直改终态 + 重启清槽 → 回流 BUG-T15-012/014 联合排查 |
| M-4 保底触发 | 保留现场日志（`_force_finalize` WARNING 上下文）→ 回流 BUG-T15-014 复测矩阵 `_t15_bug014_v2_hitl.py` |

回退操作（docker-compose 形态）：
```bash
cd deploy/app
docker compose down          # 停当前版本
# 切回上一镜像 tag 后：
docker compose up -d
```

## 五、遗留跟踪项（不阻塞上线，按触发条件启动）

| 编号 | 事项 | 触发条件 | 责任侧 |
|---|---|---|---|
| G2 | 画布 UI 交互补测（AC-01~06） | 浏览器桥恢复后 1 个工作日内 | 测试侧 |
| G3 | AI 效果面专项（AC-16~19） | 真实模型环境备妥后 | 测试侧+上游 |
| O-02/O-03 | 上游口径书面确认 | 上线前 | 产品/上游 |
| R-2 | 复测脚本输出落盘规范 | 下一测试任务启动前 | 测试侧 |
