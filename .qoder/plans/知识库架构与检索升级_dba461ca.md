# 知识库架构升级与混合检索闭环

## 现状概述

- 知识库为单表 `mvp_knowledge_items`，检索基于关键词/字段匹配
- embedding 字段已预留但未启用，无 pgvector 依赖
- 合规审核有独立页面，AI工作台无口吻选择
- 无独立知识库管理页面
- 前端构建 chunk 较大(670KB)

## Task 1: 数据库Schema升级 — 知识分库 + 切块表 + pgvector

**目标**: 实现4层知识架构和多维切块存储

**后端文件**:
- `backend/app/models/models.py` — 新增/修改模型
- `backend/alembic/versions/` — 新建迁移文件
- `backend/requirements.txt` — 添加 pgvector 依赖

**具体变更**:

1. 添加依赖: `pgvector>=0.2.4` 到 requirements.txt

2. 修改 `mvp_knowledge_items` 表，新增字段:
   - `library_type`: String(50) — 所属分库(hot_content/industry_phrases/platform_rules/audience_profile/account_positioning/prompt_templates/compliance_rules)
   - `layer`: String(30) — 所属层级(raw/structured/rule/generation)
   - `source_url`: String(500) — 原始链接
   - `author`: String(200) — 作者
   - `like_count`/`comment_count`/`collect_count`: Integer — 互动数据
   - `emotion_intensity`: String(20) — 情绪强度
   - `conversion_goal`: String(50) — 转化目标
   - `is_hot`: Boolean — 是否爆款

3. 新建 `mvp_knowledge_chunks` 表:
   - `id`: Integer PK
   - `knowledge_id`: Integer FK → mvp_knowledge_items
   - `chunk_type`: String(30) — post/paragraph/rule/template
   - `chunk_index`: Integer — 切块序号
   - `content`: Text — 切块内容
   - `metadata_json`: JSON — 元数据(标题/段落位置/规则类型等)
   - `embedding`: Vector(1024) — pgvector 向量字段
   - `token_count`: Integer — token数
   - `created_at`: DateTime

4. Alembic 迁移: 启用 pgvector 扩展，创建 chunks 表，为 embedding 建 ivfflat 索引

## Task 2: Embedding服务 + 切块服务

**目标**: 实现内容切块和向量化能力

**新建文件**:
- `backend/app/services/embedding_service.py` — 向量化服务
- `backend/app/services/chunking_service.py` — 切块服务

**embedding_service.py**:
- 支持两种模式:
  - `volcano`: 调用火山方舟 Embedding API (text-embedding-v2)
  - `local`: 调用 Ollama embedding 端点 (`/api/embeddings`)
- 方法: `async generate_embedding(text: str, model: str = "volcano") -> List[float]`
- 方法: `async generate_embeddings_batch(texts: List[str]) -> List[List[float]]`
- 向量维度: 1024 (与pgvector索引匹配)

**chunking_service.py**:
- 4种切块策略:

  a) `chunk_post_level(knowledge_item)` — 帖子级: 完整内容+元数据作为一个chunk
  
  b) `chunk_paragraph_level(knowledge_item)` — 段落级: 拆成标题/开头、中间论述、结尾CTA三段
  
  c) `chunk_rule_level(rule_text, rule_type)` — 规则级: 单条规则作为独立chunk
  
  d) `chunk_template_level(template_text, template_type)` — 模板级: 开头模板/CTA模板/语气模板

- 方法: `async process_and_store_chunks(knowledge_id, db)` — 根据library_type自动选择切块策略，生成embedding，写入chunks表

## Task 3: 混合检索服务

**目标**: 实现 关键词检索 + 向量检索 + 元数据过滤 + rerank

**修改文件**:
- `backend/app/services/mvp_knowledge_service.py` — 升级 search_for_generation

**新建文件**:
- `backend/app/services/hybrid_search_service.py`

**hybrid_search_service.py**:

```
async search(query_params) -> List[ChunkResult]:
    1. 元数据过滤: 按 platform/topic/audience/library_type 预筛选
    2. 关键词召回 Top20: 对 chunk content 做 ilike/tsvector 全文检索
    3. 向量召回 Top20: query embedding <-> chunk embedding 余弦相似度
    4. 合并去重 Top30: 按 chunk_id 去重，union 两路结果
    5. Rerank Top5~8: 调用 LLM 对候选做相关性打分排序
    6. 返回排序后的 chunks + 原始 knowledge_item 信息
```

**升级 search_for_generation**:
- 按用户选择条件分别调用 hybrid_search:
  - 爆款内容库: library_type=hot_content, platform+audience+topic 过滤
  - 人群洞察库: library_type=audience_profile, audience 过滤
  - 平台规则库: library_type=platform_rules, platform 过滤
  - 审核规则库: library_type=compliance_rules
  - 账号语气库: library_type=account_positioning, platform+account_type 过滤
  - CTA模板库: library_type=prompt_templates, goal 过滤
- 每类库分别召回，最终组装成结构化上下文

## Task 4: 入库Pipeline升级 — 切块+向量化+分库

**目标**: 采集内容自动完成切块、向量化、分库入库

**修改文件**:
- `backend/app/services/mvp_knowledge_service.py` — auto_ingest_from_raw 升级
- `backend/app/collector/services/pipeline.py` — auto_ingest_to_mvp_knowledge 升级

**入库流程升级为**:
```
采集内容
→ 清洗正文(已有)
→ 去重(已有，content_hash)
→ 标签提取(已有，关键词规则)
→ 结构化抽取(已有，增强: 可选LLM抽取)
→ 推断 library_type + layer(新增)
→ 生成摘要(已有)
→ 写入 mvp_knowledge_items(已有)
→ 切chunk(新增: 调用 chunking_service)
→ 生成embedding(新增: 调用 embedding_service)
→ 写入 mvp_knowledge_chunks(新增)
```

**分库规则** (library_type 推断):
- category=爆款/案例 → hot_content
- category=人群洞察 → audience_profile
- category=平台规则 → platform_rules
- category=风险提示 → compliance_rules
- category=语气模板 → account_positioning
- category=CTA模板 → prompt_templates
- 其他 → industry_phrases (默认)

**API端点**:
- 修改 `POST /api/mvp/raw-contents/auto-pipeline` — 增加切块+向量化步骤
- 新增 `POST /api/mvp/knowledge/reindex` — 对已有知识重新切块+向量化

## Task 5: 前端 — 知识库页面 + 合规移入AI工作台 + 口吻选择

**目标**: 新增知识库管理页面，移除独立合规页面，AI工作台增加口吻选择

**修改文件**:
- `desktop/src/App.tsx` — 路由调整
- `desktop/src/components/AppLayout.tsx` — 导航调整
- `desktop/src/pages/ai-workbench/MvpWorkbenchPage.tsx` — 合规嵌入+口吻选择
- `desktop/src/lib/api.ts` — 新增知识库API
- `desktop/src/types.ts` — 类型更新

**新建文件**:
- `desktop/src/pages/knowledge/KnowledgePage.tsx` — 知识库管理页面

**5a. 知识库页面 (KnowledgePage.tsx)**:
- 顶部: 7个分库Tab切换(爆款内容/行业话术/平台规则/人群画像/账号定位/提示词/审核规则)
- 筛选栏: platform/topic/audience/content_type/keyword搜索
- 列表展示: 标题/平台/分库类型/层级/风险等级/使用次数/创建时间
- 内容预览: 点击展开查看内容+结构化字段+切块信息
- 统计概览: 各分库数量、总条目数、今日新增

**5b. 合规审核移入AI工作台**:
- 移除导航中的"合规审核"菜单项
- 移除 /compliance 路由
- AI工作台新增"合规检测"区域(位于生成结果下方):
  - 文本输入框: 可粘贴任意文案进行检测
  - 检测按钮: 调用 /api/mvp/compliance/check
  - 结果展示: 风险等级/风险点/建议/自动修正版

**5c. AI工作台新增口吻选择**:
- 新增 TONE_OPTIONS 选项组(位于"内容目标"下方):
  - `professional`: 专业严谨
  - `friendly`: 亲切友好
  - `humorous`: 幽默风趣
  - `empathetic`: 共情走心
  - `urgent`: 紧迫感
- 请求参数增加 `tone` 字段
- 后端 FullPipelineRequest 增加 `tone: Optional[str]`
- 生成时将 tone 纳入 prompt 编排

**5d. 导航调整**:
- 内容生产: AI中枢 / 采集中心 / AI工作台(含合规)
- 知识管理: 知识库(新增)
- 内容管理: 收件箱 / 素材库
- 业务管理: 线索管理 / 客户管理
- 管理层: 老板看板

**5e. 收件箱确认**: 已是预览模式，确认无详情弹窗/无人工审核按钮

**5f. 素材库确认**: 已有"转入改写"按钮，确认功能正常

## Task 6: 后端API端点补全

**修改文件**:
- `backend/app/api/endpoints/mvp_routes.py`
- `backend/app/schemas/mvp_schemas.py`
- `backend/app/schemas/generate_schema.py`

**新增端点**:
- `GET /api/mvp/knowledge/libraries` — 获取各分库统计
- `GET /api/mvp/knowledge/chunks/{knowledge_id}` — 获取某条知识的切块列表
- `POST /api/mvp/knowledge/reindex` — 重建索引(重新切块+向量化)
- `POST /api/mvp/compliance/check` 保留(AI工作台内调用)

**修改端点**:
- `GET /api/mvp/knowledge` — 增加 library_type 过滤参数
- `POST /api/mvp/generate/full-pipeline` — 增加 tone 参数

**Schema更新**:
- FullPipelineRequest 增加 `tone: Optional[str] = None`
- 新增 KnowledgeLibraryStats schema
- 新增 ChunkResponse schema

## Task 7: 前端代码分割优化

**修改文件**:
- `desktop/vite.config.ts` — 配置 manualChunks

**分割策略**:
- vendor chunk: react/react-dom
- ui chunk: UI组件库
- pages chunk: 按路由懒加载 (React.lazy + Suspense)

**修改 App.tsx**: 所有页面组件改为 `React.lazy(() => import(...))` 动态导入

## Task 8: 验证与集成测试

- 后端: 模块导入验证、API端点可达性
- 前端: TypeScript编译零错误、生产构建成功、chunk大小检查
- 知识库: 分库入库→切块→向量化→混合检索 端到端验证

## 依赖关系

```
Task 1 (Schema) 
  → Task 2 (Embedding+切块服务)
    → Task 3 (混合检索)
    → Task 4 (入库Pipeline)
  → Task 6 (API端点)

Task 5 (前端) 依赖 Task 6 (API)
Task 7 (代码分割) 独立可并行

Task 8 (验证) 依赖 Task 1~7 全部完成
```

## 技术决策

1. **向量存储**: pgvector (PostgreSQL原生扩展，无需额外服务)
2. **Embedding模型**: 优先火山方舟 text-embedding API，fallback Ollama nomic-embed-text
3. **向量维度**: 1024 (兼容主流模型)
4. **Rerank**: 使用LLM做轻量rerank (火山/Ollama)，不引入额外rerank模型服务
5. **切块粒度**: 按 library_type 自动选择策略
6. **前端懒加载**: React.lazy + Suspense，Vite manualChunks
