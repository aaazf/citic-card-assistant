# 基础阶段架构决策

## ADR-001：聊天流使用 POST + SSE

`POST /api/v1/chat` 保持为唯一聊天入口。Phase 3 响应 JSON；Phase 5 在 `Accept: text/event-stream` 下返回 SSE 流。前端使用 `fetch()` 读取流，不使用仅支持 GET 的原生 `EventSource`。

## ADR-002：Chunk 归 Chroma 管理

Chroma 保存 Chunk 正文、Embedding 和检索元数据。SQLite 只保存 `Document` 及 `chunk_count`。`app/models/chunk.py` 是向量记录的数据契约，不是 SQLAlchemy 表。

## ADR-003：引用随消息持久化

第一版在 `Message.citations` JSON 字段中保存引用。引用至少包含 document_id、filename、page、chunk_id、score。只有后续出现跨消息引用查询需求时才拆分为独立关联表。

## ADR-004：文档处理使用进程内任务

Phase 2 使用轻量进程内后台处理并持久化 Document 状态。第一版不引入 Celery、Redis 或消息队列。

## ADR-005：阶段顺序

Phase 1 只提供最近会话页面壳；Phase 7 实现持久化与恢复。Phase 3 使用最简向量检索链路但保留 Router 接口；Phase 4 接入 Knowledge、Hybrid、General 路由。

## ADR-006：Embedding 模型切换

Phase 2 使用单个固定 Chroma collection。不同模型产生不同向量维度时，切换配置前需要重新导入文档；自动重建索引不在第一版范围。
