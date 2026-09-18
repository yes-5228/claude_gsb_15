# 公厕保洁巡查记录系统

面向城市公厕管养单位的巡查记录、问题整改与应急处置闭环管理系统，覆盖 **公厕台账 → 保洁巡查 → 问题上报 → 整改跟踪 → 应急处置** 五条业务主线。后端为 FastAPI + SQLAlchemy，前端为 React + Vite，前后端均按模块拆分，可单独开发、单独部署。

## 功能模块

| 模块 | 页面/入口 | 主要能力 |
| --- | --- | --- |
| 总览看板 | `/` | 核心指标卡（含应急处置/响应超时/响应及时率）、巡查与问题趋势、整改状态/分类/严重程度分布、应急事件类型分布、区域运行情况、重点关注公厕、最新问题、巡查与应急事件 |
| 公厕台账 | `/restrooms`、`/restrooms/:id` | 台账增删改查、区域与状态筛选、公厕详情（档案 + 历史巡查 + 历史问题 + 应急事件）、关联数据删除保护 |
| 保洁巡查 | `/inspections` | 8 项检查项打分、自动折算百分制得分与等级、班次/日期/结论筛选、巡查详情、一键转问题上报 |
| 问题上报 | `/issues`、`/issues/:id` | 问题上报（可关联巡查记录）、分类/程度/期限、整改流程流转、整改轨迹时间线、超期预警、追加跟进记录 |
| 应急处置 | `/emergencies`、`/emergencies/:id` | 停水停电/设施爆裂/污损外溢等事件登记（发现时间、影响范围）、按事件类型约定响应时限并自动计算响应耗时、超时预警、处置措施登记、恢复情况与影响补充、处置轨迹时间线 |

其他页面不会互相混杂：台账、巡查、问题、应急各自独立成页，详情页再做跨模块的关联展示。

## 技术栈

- 后端：FastAPI 0.115、SQLAlchemy 2.0、Pydantic v2、Uvicorn；数据库默认 SQLite，容器中可切换 PostgreSQL 16
- 前端：React 18、React Router 6、Vite 6；不使用 UI 组件库，样式集中在 `src/styles/global.css`
- 部署：Docker Compose 编排 PostgreSQL + 后端 + Nginx 前端（Nginx 同时反代 `/api`）

## 目录结构

```
.
├── backend
│   ├── app
│   │   ├── api/v1/endpoints      # 路由层：restrooms / inspections / issues / emergencies / stats / meta
│   │   ├── core                 # 配置、数据库、业务常量、领域异常
│   │   ├── models               # ORM 模型：公厕、巡查、问题、整改流水、应急事件、处置流水
│   │   ├── schemas              # Pydantic 出入参模型
│   │   ├── services             # 业务规则层：台账、巡查、问题整改、应急处置、评分、统计
│   │   ├── seed.py              # 演示数据生成
│   │   └── main.py              # 应用入口（含异常处理、CORS、健康检查）
│   ├── tests                    # pytest 接口测试
│   ├── Dockerfile
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── api                  # 按资源拆分的接口封装 + 统一 fetch 客户端
│   │   ├── components           # 通用组件：表格、分页、弹窗、标签、图表、时间线等
│   │   ├── hooks                # useAsync / useListQuery / useDictionaries
│   │   ├── pages                # dashboard / restrooms / inspections / issues / emergencies 五个模块
│   │   ├── utils                # 时间格式化、评分换算、响应耗时格式化
│   │   └── styles/global.css
│   ├── nginx.conf
│   └── Dockerfile
└── docker-compose.yml
```

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
docker compose up -d --build
```

启动后：

- 前端界面：http://localhost:8080
- 后端接口文档：http://localhost:8000/docs （也可通过 http://localhost:8080/docs 访问）
- 健康检查：http://localhost:8000/health

三个服务均带健康检查，`backend` 等待 `db` 健康后启动，`frontend` 等待 `backend` 健康后启动。首次启动会自动建表并写入演示数据。

停止与清理：

```bash
docker compose down        # 停止容器
docker compose down -v     # 同时删除数据库卷（下次启动重新生成演示数据）
```

### 方式二：本地开发

后端（默认使用 SQLite，数据库文件为 `backend/data/app.db`）：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev                        # http://localhost:5173，/api 自动代理到 127.0.0.1:8000
```

若后端不在默认端口，可指定代理目标：

```bash
set VITE_PROXY_TARGET=http://127.0.0.1:8020   # macOS/Linux: export VITE_PROXY_TARGET=...
npm run dev
```

## 环境变量

后端（均可用环境变量覆盖，见 `backend/app/core/config.py`）：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/app.db` | 数据库连接串；容器中为 `postgresql+psycopg://restroom:restroom_pass@db:5432/restroom` |
| `SEED_ON_STARTUP` | `true` | 启动时若库为空则写入演示数据 |
| `CORS_ORIGINS` | `*` | 允许跨域来源，逗号分隔 |
| `SQL_ECHO` | `false` | 是否打印 SQL |

前端：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `VITE_API_BASE` | `/api/v1` | 接口前缀，构建时注入 |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:8000` | 仅开发模式下 Vite 代理目标 |

## 接口一览

所有接口前缀为 `/api/v1`，完整文档见 `/docs`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/restrooms` | 台账分页查询（keyword/district/status/grade/排序/分页） |
| POST | `/restrooms` | 新增公厕，编号留空自动生成 `WC-0001` |
| GET | `/restrooms/{id}` | 详情，含巡查次数、均分、未闭环问题数、处置中应急事件数 |
| PATCH | `/restrooms/{id}` | 局部更新 |
| DELETE | `/restrooms/{id}?force=` | 删除；有巡查、问题或应急事件记录时返回 409，`force=true` 才级联删除 |
| GET | `/restrooms/meta/districts` | 区域列表（筛选下拉用） |
| GET | `/inspections` | 巡查记录查询（restroom_id/district/inspector/shift/result/日期区间/关键字） |
| POST | `/inspections` | 新增巡查，服务端按检查项自动算分、定级、判定结论 |
| GET/PATCH/DELETE | `/inspections/{id}` | 详情 / 更新 / 删除 |
| GET | `/issues` | 问题查询（status/category/severity/district/overdue/open_only/日期区间/关键字） |
| POST | `/issues` | 上报问题，自动生成编号 `WT-YYYYMMDD-001` 并写入首条整改流水 |
| GET/PATCH/DELETE | `/issues/{id}` | 详情（含完整整改轨迹）/ 更新 / 删除 |
| GET | `/issues/{id}/transitions` | 当前状态可执行的流转动作 |
| POST | `/issues/{id}/transitions` | 推进整改状态（越级流转返回 400） |
| POST | `/issues/{id}/records` | 追加跟进记录（不改变状态） |
| GET | `/emergencies` | 应急事件查询（event_type/status/district/overdue/open_only/recovered/日期区间/关键字） |
| POST | `/emergencies` | 登记应急事件，自动生成编号 `YJ-YYYYMMDD-001` 并写入首条处置流水 |
| GET/PATCH/DELETE | `/emergencies/{id}` | 详情（含完整处置轨迹与响应耗时）/ 补正登记（仅待处置）/ 删除 |
| POST | `/emergencies/{id}/handle` | 开始处置：登记处置人、处置措施与到场时间，事件转入「处置中」 |
| POST | `/emergencies/{id}/recover` | 恢复确认：补充恢复情况与造成的影响，事件转入「已恢复」 |
| GET | `/emergencies/{id}/transitions` | 当前状态可执行的流转动作 |
| POST | `/emergencies/{id}/transitions` | 推进处置状态（作废/终止/归档关闭，越级流转返回 400） |
| POST | `/emergencies/{id}/records` | 追加处置跟进记录（不改变状态） |
| GET | `/stats/overview` | 核心指标（含应急事件总数、处置中、响应超时、响应及时率） |
| GET | `/stats/dashboard` | 看板聚合数据（趋势、分布、区域、排行、最新记录、应急类型与最新事件） |
| GET | `/meta/dictionaries` | 枚举字典（状态、分类、程度、检查项、流转规则、应急类型与响应时限） |
| GET | `/meta/restroom-options` | 公厕下拉选项 |
| GET | `/health` | 健康检查 |

## 业务规则

- **巡查评分**：8 个检查项各 0-10 分，得分 = 总得分 / 满分 × 100；≥90 优秀、≥80 良好、≥70 合格，其余不合格。任一检查项低于 6 分或等级为不合格时，巡查结论自动置为「发现问题」。
- **问题编号**：`WT-` + 上报日期 + 当日三位流水号。
- **整改闭环**：`待整改 → 整改中 → 待验收 → 已完成 → 已关闭`；`待验证` 阶段可被驳回退回 `整改中`，`待整改/整改中` 可直接作废关闭。每次流转都会写入一条整改流水（动作、原状态、新状态、操作人、说明），详情页以时间线呈现。
- **超期预警**：整改期限早于当前时间且状态仍处于未闭环（待整改/整改中/待验收）时，列表与详情页显示「已超期」，看板统计超期数量。
- **应急事件编号**：`YJ-` + 登记日期 + 当日三位流水号。
- **应急响应时限**：按事件类型约定到场处置时限——停水 30 分钟、停电 30 分钟、设施爆裂 15 分钟、污损外溢 15 分钟、其他 30 分钟。
- **响应耗时计算**：响应耗时 = 开始处置时间 − 发现时间（分钟）。已到场时按实际耗时与时限比较判定是否超时；仍处于「待处置」且经过时间已超过时限时，按未到场超时预警。事件持续时长 = 恢复时间 − 发现时间（未恢复则计至当前）。
- **应急处置闭环**：`待处置 → 处置中 → 已恢复 → 已关闭`；`待处置` 可作废关闭、`处置中` 可终止关闭。开始处置登记处置人与处置措施，恢复时补充恢复情况与造成的影响。每次流转写入一条处置流水（动作、原状态、新状态、操作人、说明），详情页以时间线呈现；事件进入处置后登记信息不可再修改。
- **删除保护**：删除公厕时若已存在巡查、问题或应急事件记录，接口返回 409 并提示数量，需要显式 `force=true` 才会级联删除；前端会二次确认。

## 演示数据

`SEED_ON_STARTUP=true`（默认）且数据库为空时，会自动写入：10 座公厕（4 个区域、三类等级、含维修/停用状态）、近 14 天约 90 条巡查记录、13 条不同整改阶段的问题及其完整整改轨迹、10 起覆盖全部类型与各处置阶段（待处置/处置中/已恢复/已关闭，含响应及时与响应超时）的应急事件。数据由固定随机种子生成，结果可复现；如需重置，删除 `backend/data/app.db`（或 `docker compose down -v`）后重启即可。

## 测试与验证

```bash
cd backend && pytest -q          # 接口测试（覆盖台账 CRUD、删除保护、评分、流程流转、应急处置、统计）
cd frontend && npm run build     # 生产构建
```

本项目完成时已实际运行验证：

- 后端 `pytest`：10 个用例全部通过（含 4 个应急处置用例，覆盖登记、响应时限与耗时、超时预警、处置/恢复/关闭流转、补正保护、筛选与删除保护）；`/health`、台账/巡查/问题/应急/统计/字典接口均返回预期数据。
- 前端 `npm run build`：构建成功（76 个模块）。
- 后端端到端冒烟（uvicorn + 种子数据）：字典返回应急类型与时限；应急列表分页、计算字段（响应时限/响应耗时/是否超时）、超时/处置中/类型筛选正确；完整链路 登记 → 开始处置（响应 20 分钟 > 15 分钟时限，正确标记超时）→ 恢复（持续 90 分钟）→ 归档关闭（4 条流水）验证通过；越级恢复与处置后补正均返回 400；看板应急指标（总数、处置中、超时数、响应及时率 70.0%）、类型分布、最新事件与公厕详情应急统计、删除保护提示均符合预期。

## 常见问题

- **端口被占用**：若 8000/8080 已被占用，可用覆盖文件改端口，例如 `docker compose -f docker-compose.yml -f override.yml up -d`，其中 `override.yml` 写 `services: { backend: { ports: ["8010:8000"] } }`。
- **想看 SQLite 而不是 PostgreSQL**：把 `backend` 服务的 `DATABASE_URL` 改为 `sqlite:///./data/app.db` 即可，无需 `db` 服务。
- **接口 422**：后端把参数校验错误统一转成中文可读文案，前端会直接弹出提示，例如「参数校验失败 - name: String should have at least 1 character」。
- **越级流转报错**：属于预期行为，接口会返回当前状态允许流转的目标状态列表，前端也只会展示合法动作。
