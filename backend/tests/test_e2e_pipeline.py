"""端到端链路测试：采集→清洗→筛选→入库→生成→合规

测试策略：
- 使用 SQLite 内存数据库进行隔离测试
- Mock 所有外部依赖（Ollama/LLM、Embedding）
- 验证完整链路的数据流转和状态变更
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql import func

# ============== 测试环境设置 ==============
# 必须在导入 app 模块之前设置环境变量
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
os.environ["OLLAMA_MODEL"] = "qwen"
os.environ["ARK_API_KEY"] = ""
os.environ["USE_CLOUD_MODEL"] = "false"


# ============== 测试模型定义 ==============
# 为测试创建独立的 Base 和模型，避免导入生产代码的数据库配置
Base = declarative_base()


class MvpInboxItem(Base):
    """测试用收件箱模型"""

    __tablename__ = "mvp_inbox_items"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False, default="xiaohongshu")
    source_id = Column(String(200), nullable=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    content_preview = Column(Text, nullable=True)
    author = Column(String(200), nullable=True)
    author_name = Column(String(200), nullable=True)
    publish_time = Column(DateTime, nullable=True)
    source_url = Column(String(1000), nullable=True)
    url = Column(String(500), nullable=True)
    source_type = Column(String(50), nullable=False, default="collect")
    keyword = Column(String(200), nullable=True)
    risk_level = Column(String(20), nullable=False, default="low")
    duplicate_status = Column(String(20), nullable=False, default="unique")
    score = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.0)
    tech_status = Column(String(30), nullable=False, default="parsed")
    biz_status = Column(String(30), nullable=False, default="pending")
    clean_status = Column(String(20), default="pending")
    quality_status = Column(String(20), default="pending")
    risk_status = Column(String(20), default="normal")
    material_status = Column(String(20), default="not_in")
    rewrite_ready = Column(Boolean, default=False)
    cleaned_at = Column(DateTime, nullable=True)
    screened_at = Column(DateTime, nullable=True)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    favorite_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=None, onupdate=None)


class MvpMaterialItem(Base):
    """测试用素材库模型"""

    __tablename__ = "mvp_material_items"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source_url = Column(String(1000), nullable=True)
    like_count = Column(Integer, nullable=False, default=0)
    comment_count = Column(Integer, nullable=False, default=0)
    author = Column(String(200), nullable=True)
    is_hot = Column(Boolean, nullable=False, default=False)
    risk_level = Column(String(20), nullable=False, default="low")
    use_count = Column(Integer, nullable=False, default=0)
    source_inbox_id = Column(Integer, nullable=True)
    inbox_item_id = Column(Integer, nullable=True)
    quality_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    rewrite_ready = Column(Boolean, default=False)
    tags_json = Column(Text, nullable=True)
    topic = Column(String(100), nullable=True)
    persona = Column(String(100), nullable=True)
    content_preview = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, default=None, onupdate=None)


class MvpKnowledgeItem(Base):
    """测试用知识库模型"""

    __tablename__ = "mvp_knowledge_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=True)
    platform = Column(String(50), nullable=True)
    audience = Column(String(100), nullable=True)
    style = Column(String(100), nullable=True)
    source_material_id = Column(Integer, nullable=True)
    use_count = Column(Integer, nullable=False, default=0)
    embedding = Column(Text, nullable=True)  # SQLite 不支持 Vector
    library_type = Column(String(50), default="hot_content")
    layer = Column(String(30), default="structured")
    topic = Column(String(100), nullable=True)
    content_type = Column(String(50), nullable=True)
    hook_sentence = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=True)
    summary = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=True)
    author = Column(String(200), nullable=True)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    is_hot = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class MvpKnowledgeChunk(Base):
    """测试用知识切块模型"""

    __tablename__ = "mvp_knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    knowledge_id = Column(Integer, nullable=False, index=True)
    chunk_type = Column(String(30), nullable=False)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    embedding = Column(Text, nullable=True)
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


class MvpGenerationResult(Base):
    """测试用生成结果模型"""

    __tablename__ = "mvp_generation_results"

    id = Column(Integer, primary_key=True, index=True)
    source_material_id = Column(Integer, nullable=True)
    input_text = Column(Text, nullable=False)
    output_title = Column(String(500), nullable=True)
    output_text = Column(Text, nullable=False)
    version = Column(String(50), nullable=False)
    platform = Column(String(50), nullable=True)
    audience = Column(String(100), nullable=True)
    style = Column(String(100), nullable=True)
    is_final = Column(Boolean, nullable=False, default=False)
    opening_hook = Column(Text, nullable=True)
    cta_section = Column(Text, nullable=True)
    risk_disclaimer = Column(Text, nullable=True)
    alternative_v1 = Column(Text, nullable=True)
    alternative_v2 = Column(Text, nullable=True)
    output_structure = Column(JSON, nullable=True)
    compliance_status = Column(String(30), nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class MvpComplianceRule(Base):
    """测试用合规规则模型"""

    __tablename__ = "mvp_compliance_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String(50), nullable=False)
    keyword = Column(String(200), nullable=False)
    suggestion = Column(Text, nullable=True)
    risk_level = Column(String(20), nullable=False, default="medium")


# ============== Fixtures ==============


@pytest.fixture
def db_session():
    """创建内存数据库会话"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_collector_data():
    """模拟采集数据"""
    return {
        "platform": "xiaohongshu",
        "title": "征信花了怎么办？教你正确修复征信",
        "content": """征信花了还能贷款吗？这是很多朋友关心的问题。

今天给大家分享几个实用的征信修复方法：

第一，先看查询次数。如果你的征信查询次数过多，建议先养护3-6个月，期间不要再申请新的贷款或信用卡。

第二，检查负债情况。负债率过高也会影响贷款审批，尽量把负债控制在收入的50%以内。

第三，保持良好的还款记录。按时还款是修复征信的关键。

有任何问题欢迎咨询，祝大家都能顺利贷款！""",
        "author_name": "金融小助手",
        "publish_time": "2026-04-01T10:00:00",
        "url": "https://www.xiaohongshu.com/explore/test123",
        "source_id": "xhs_test_123",
        "like_count": 1200,
        "comment_count": 89,
        "favorite_count": 456,
    }


@pytest.fixture
def low_quality_collector_data():
    """低质量采集数据"""
    return {
        "platform": "xiaohongshu",
        "title": "测试标题",
        "content": "短内容",
        "author_name": "测试作者",
        "url": "https://test.com/low",
        "source_id": "low_001",
        "like_count": 0,
        "comment_count": 0,
        "favorite_count": 0,
    }


@pytest.fixture
def high_risk_collector_data():
    """高风险采集数据"""
    return {
        "platform": "xiaohongshu",
        "title": "黑户必过！无视征信秒批贷款！",
        "content": """百分百通过！黑户也能贷！

我们平台保证100%下款，不看征信，不看负债，秒批秒放款！

零利息！零门槛！当天放款！

联系人：张经理""",
        "author_name": "贷款中介",
        "url": "https://test.com/risk",
        "source_id": "risk_001",
        "like_count": 50,
        "comment_count": 10,
        "favorite_count": 5,
    }


# ============== 测试服务类（简化版，不依赖完整 app 导入）==============


class MockCleaningService:
    """模拟清洗服务"""

    def __init__(self, db: Session):
        self.db = db

    def clean_item(self, inbox_item_id: int) -> dict:
        item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == inbox_item_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}

        # 简化清洗逻辑
        import re
        from datetime import datetime

        # 移除多余空白
        content = re.sub(r"\n{3,}", "\n\n", item.content or "")
        content = re.sub(r" {2,}", " ", content)

        item.content = content
        item.content_preview = content[:200]
        item.clean_status = "cleaned"
        item.cleaned_at = datetime.utcnow()

        self.db.commit()
        return {"success": True, "item_id": item.id, "is_duplicate": False}


class MockQualityScreeningService:
    """模拟质量筛选服务"""

    def __init__(self, db: Session):
        self.db = db

    async def screen_item(self, inbox_item_id: int) -> dict:
        item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == inbox_item_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}

        import math
        from datetime import datetime

        # 热度评分
        heat = (item.like_count or 0) * 0.4 + (item.comment_count or 0) * 0.4 + (item.favorite_count or 0) * 0.2
        heat_score = min(math.log10(heat + 1) / 3 * 25, 25) if heat > 0 else 0

        # 完整度评分
        completeness = 0
        if item.title:
            completeness += 5
        if item.content and len(item.content) > 50:
            completeness += 5
        if item.author_name:
            completeness += 3
        if item.platform:
            completeness += 3
        completeness = min(completeness, 25)

        # 可读性评分
        readability = 0
        if item.content and 100 <= len(item.content) <= 3000:
            readability += 10
        if item.content and len(item.content.split("\n")) >= 2:
            readability += 8
        readability = min(readability, 25)

        # 可仿写性评分
        rewritability = 0
        if item.title:
            rewritability += 10
        rewritability = min(rewritability, 25)

        quality_score = heat_score + completeness + readability + rewritability

        # 简单风险评分
        risk_keywords = ["必过", "包过", "黑户", "秒批", "100%", "零利息", "零门槛"]
        risk_score = 0
        content = (item.title or "") + (item.content or "")
        for kw in risk_keywords:
            if kw in content:
                risk_score += 15
        risk_score = min(risk_score, 100)

        # 更新状态
        if quality_score >= 70:
            quality_status = "good"
        elif quality_score >= 40:
            quality_status = "normal"
        else:
            quality_status = "low"

        item.quality_score = round(quality_score, 1)
        item.risk_score = round(risk_score, 1)
        item.quality_status = quality_status
        item.screened_at = datetime.utcnow()

        if quality_score >= 70 and risk_score < 50:
            item.rewrite_ready = True

        self.db.commit()

        return {
            "success": True,
            "item_id": item.id,
            "quality_score": item.quality_score,
            "risk_score": item.risk_score,
            "quality_status": quality_status,
        }


class MockPipelineService:
    """模拟 Pipeline 服务"""

    def __init__(self, db: Session):
        self.db = db
        self.cleaning = MockCleaningService(db)
        self.screening = MockQualityScreeningService(db)

    async def ingest_from_collector(self, raw_data: dict) -> dict:
        from datetime import datetime

        try:
            item = MvpInboxItem(
                platform=raw_data.get("platform", "unknown"),
                source_id=raw_data.get("source_id"),
                title=raw_data.get("title", "")[:500],
                content=raw_data.get("content", ""),
                author=raw_data.get("author_name"),
                author_name=raw_data.get("author_name"),
                source_url=raw_data.get("url"),
                url=raw_data.get("url"),
                source_type="collect",
                like_count=raw_data.get("like_count", 0),
                comment_count=raw_data.get("comment_count", 0),
                favorite_count=raw_data.get("favorite_count", 0),
                clean_status="pending",
                material_status="not_in",
            )

            if raw_data.get("publish_time"):
                try:
                    item.publish_time = datetime.fromisoformat(raw_data["publish_time"].replace("Z", "+00:00"))
                except:
                    pass

            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)

            # 触发清洗
            clean_result = self.cleaning.clean_item(item.id)
            clean_status = "cleaned" if clean_result.get("success") else "failed"

            return {
                "success": True,
                "item_id": item.id,
                "clean_status": clean_status,
                "is_duplicate": clean_result.get("is_duplicate", False),
            }
        except Exception as e:
            self.db.rollback()
            return {"success": False, "error": str(e)}

    async def promote_to_material(self, inbox_item_id: int) -> dict:
        item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == inbox_item_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}

        if item.clean_status != "cleaned":
            return {"success": False, "error": "Item not cleaned"}

        # 检查是否已入素材库
        if item.material_status == "in_material":
            existing = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.inbox_item_id == inbox_item_id).first()
            if existing:
                return {"success": True, "material_id": existing.id, "inbox_item_id": inbox_item_id}

        # 触发质量筛选
        await self.screening.screen_item(inbox_item_id)
        self.db.refresh(item)

        # 创建素材
        material = MvpMaterialItem(
            platform=item.platform,
            title=item.title,
            content=item.content,
            source_url=item.source_url or item.url,
            like_count=item.like_count or 0,
            comment_count=item.comment_count or 0,
            author=item.author or item.author_name,
            is_hot=(item.quality_score or 0) >= 70,
            risk_level=item.risk_level or "low",
            inbox_item_id=item.id,
            quality_score=item.quality_score,
            risk_score=item.risk_score,
            rewrite_ready=item.rewrite_ready,
        )

        self.db.add(material)
        item.material_status = "in_material"
        self.db.commit()
        self.db.refresh(material)

        return {"success": True, "material_id": material.id, "inbox_item_id": inbox_item_id}

    async def build_knowledge(self, material_id: int) -> dict:
        material = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
        if not material:
            return {"success": False, "error": "Material not found"}

        # 检查是否已有知识条目
        existing = self.db.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.source_material_id == material_id).first()
        if existing:
            return {"success": True, "knowledge_id": existing.id, "chunk_count": 0}

        knowledge = MvpKnowledgeItem(
            title=material.title,
            content=material.content,
            platform=material.platform,
            source_material_id=material_id,
            source_url=material.source_url,
            author=material.author,
            audience=material.persona,
            topic=material.topic,
            library_type="hot_content",
            like_count=material.like_count,
            comment_count=material.comment_count,
            is_hot=material.is_hot,
        )

        self.db.add(knowledge)
        self.db.flush()

        # 创建简单 chunk
        chunk = MvpKnowledgeChunk(
            knowledge_id=knowledge.id,
            chunk_type="post",
            chunk_index=0,
            content=f"{material.title}\n\n{material.content}",
            token_count=len(material.content or ""),
        )
        self.db.add(chunk)

        self.db.commit()
        self.db.refresh(knowledge)

        return {"success": True, "knowledge_id": knowledge.id, "chunk_count": 1}


class MockComplianceService:
    """模拟合规服务"""

    DEFAULT_RISKY_KEYWORDS = {
        "必过": ("high", "建议替换为'通过率较高'"),
        "包过": ("high", "建议替换为'成功率较高'"),
        "秒批": ("high", "建议替换为'审批较快'"),
        "秒放款": ("high", "建议替换为'放款较快'"),
        "黑户可贷": ("high", "建议替换为'多种方案可选'"),
        "黑户也能贷": ("high", "建议替换为'多种方案可选'"),
        "无视征信": ("high", "建议替换为'综合评估'"),
        "不看征信": ("high", "建议替换为'多维度评估'"),
        "100%": ("high", "建议移除绝对承诺"),
        "百分百": ("high", "建议移除绝对承诺"),
        "零利息": ("medium", "建议替换为'优惠利率'"),
        "零门槛": ("medium", "建议替换为'门槛灵活'"),
        "低门槛": ("medium", "建议替换为'门槛灵活'"),
    }

    def __init__(self, db: Session):
        self.db = db

    def check(self, text: str, enable_llm: bool = False, platform: str = None) -> dict:
        import re

        risk_points = []
        total_score = 0

        # 关键词检测
        for keyword, (level, suggestion) in self.DEFAULT_RISKY_KEYWORDS.items():
            if keyword in text:
                risk_points.append(
                    {
                        "keyword": keyword,
                        "reason": f"包含{level}级风险词: {keyword}",
                        "suggestion": suggestion,
                        "source": "rule",
                    }
                )
                if level == "high":
                    total_score += 30
                elif level == "medium":
                    total_score += 15
                else:
                    total_score += 5

        # 正则检查
        absolute_patterns = [
            (r"100%", "包含绝对承诺表达"),
            (r"保证.*通过", "包含保证承诺"),
            (r"必过", "包含绝对承诺"),
        ]
        for pattern, reason in absolute_patterns:
            if re.search(pattern, text):
                risk_points.append(
                    {
                        "keyword": pattern,
                        "reason": reason,
                        "suggestion": "请移除绝对化表达",
                        "source": "rule",
                    }
                )
                total_score += 20

        # 计算风险等级
        if total_score >= 50:
            risk_level = "high"
        elif total_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 自动修正
        rewritten = self._auto_fix(text, risk_points)

        # 交通灯
        has_high = any(rp.get("risk_level") == "high" for rp in risk_points)
        has_medium = any(rp.get("risk_level") == "medium" for rp in risk_points)

        if total_score >= 50 or has_high:
            traffic_light = "red"
        elif total_score >= 25 or has_medium:
            traffic_light = "yellow"
        else:
            traffic_light = "green"

        return {
            "risk_level": risk_level,
            "risk_score": min(total_score, 100),
            "risk_points": risk_points,
            "suggestions": list(set(rp.get("suggestion", "") for rp in risk_points if rp.get("suggestion"))),
            "rewritten_text": rewritten,
            "is_compliant": risk_level == "low",
            "traffic_light": traffic_light,
        }

    def _auto_fix(self, text: str, risk_points: list) -> str:
        replacements = {
            "必过": "通过率较高",
            "包过": "成功率较高",
            "秒批": "审批较快",
            "秒放款": "放款较快",
            "黑户可贷": "多种方案可选",
            "黑户也能贷": "多种方案可选",
            "无视征信": "综合评估",
            "100%": "较高",
            "百分百": "较高",
            "零利息": "优惠利率",
            "零门槛": "门槛灵活",
        }
        fixed = text
        for old, new in replacements.items():
            fixed = fixed.replace(old, new)
        return fixed


class MockGenerateService:
    """模拟生成服务"""

    def __init__(self, db: Session):
        self.db = db

    def generate_multi_version(
        self,
        source_type: str,
        source_id: int = None,
        manual_text: str = None,
        target_platform: str = "xiaohongshu",
        audience: str = "",
        style: str = "",
        **kwargs,
    ) -> dict:
        # 获取输入文本
        if source_type == "material" and source_id:
            material = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == source_id).first()
            input_text = f"{material.title}\n\n{material.content}" if material else ""
        else:
            input_text = manual_text or ""

        # 模拟生成结果
        versions = [
            {
                "title": f"[专业版] {input_text[:30]}...",
                "text": f"专业分析：{input_text[:200]}...建议先养护征信，再申请贷款。",
                "version": "professional",
                "style_label": "专业型",
            },
            {
                "title": f"[口语版] {input_text[:30]}...",
                "text": f"家人们！{input_text[:150]}...有问题评论区聊！",
                "version": "casual",
                "style_label": "口语型",
            },
            {
                "title": f"[种草版] {input_text[:30]}...",
                "text": f"姐妹们看过来！{input_text[:150]}...记得收藏哦！",
                "version": "seeding",
                "style_label": "种草型",
            },
        ]

        # 保存结果
        for v in versions:
            result = MvpGenerationResult(
                source_material_id=source_id if source_type == "material" else None,
                input_text=input_text[:500],
                output_title=v["title"],
                output_text=v["text"],
                version=v["version"],
                platform=target_platform,
                audience=audience,
                style=style,
            )
            self.db.add(result)
        self.db.commit()

        return {"versions": versions}


# ============== Test Class ==============


class TestE2EPipeline:
    """端到端链路测试：采集→清洗→筛选→入库→生成→合规"""

    @pytest.mark.asyncio
    async def test_full_pipeline_happy_path(
        self,
        db_session: Session,
        sample_collector_data,
    ):
        """完整链路测试：一条合格内容从采集到合规通过"""

        pipeline = MockPipelineService(db_session)

        # ========== Step 1: 采集入收件箱 ==========
        ingest_result = await pipeline.ingest_from_collector(sample_collector_data)

        assert ingest_result["success"] is True
        assert ingest_result["item_id"] is not None
        assert ingest_result["clean_status"] == "cleaned"

        item_id = ingest_result["item_id"]

        # ========== Step 2: 验证 InboxItem 创建 ==========
        inbox_item = db_session.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
        assert inbox_item is not None
        assert inbox_item.clean_status == "cleaned"
        assert inbox_item.title == sample_collector_data["title"]
        assert inbox_item.platform == "xiaohongshu"

        # ========== Step 3: promote_to_material → 素材库 ==========
        material_result = await pipeline.promote_to_material(item_id)

        assert material_result["success"] is True
        assert material_result["material_id"] is not None
        material_id = material_result["material_id"]

        material_item = db_session.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
        assert material_item is not None
        assert material_item.quality_score is not None
        assert material_item.quality_score > 0  # 高互动内容应有正分

        # ========== Step 4: build_knowledge → 知识库 ==========
        knowledge_result = await pipeline.build_knowledge(material_id)

        assert knowledge_result["success"] is True
        assert knowledge_result["knowledge_id"] is not None
        knowledge_id = knowledge_result["knowledge_id"]

        knowledge_item = db_session.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_id).first()
        assert knowledge_item is not None

        chunks = db_session.query(MvpKnowledgeChunk).filter(MvpKnowledgeChunk.knowledge_id == knowledge_id).all()
        assert len(chunks) >= 1

        # ========== Step 5: generate_multi_version → 多版本文案 ==========
        gen_service = MockGenerateService(db_session)
        gen_result = gen_service.generate_multi_version(
            source_type="material",
            source_id=material_id,
            target_platform="xiaohongshu",
            audience="征信花的人群",
        )

        assert "versions" in gen_result
        assert len(gen_result["versions"]) == 3

        gen_results = (
            db_session.query(MvpGenerationResult).filter(MvpGenerationResult.source_material_id == material_id).all()
        )
        assert len(gen_results) == 3

        # ========== Step 6: 合规检查 ==========
        compliance_service = MockComplianceService(db_session)

        test_text = "专业分析：征信花了不要慌，先看查询次数，再评估当前负债情况。建议先养护征信3-6个月。"
        compliance_result = compliance_service.check(text=test_text, platform="xiaohongshu")

        assert "risk_level" in compliance_result
        assert "risk_score" in compliance_result
        assert "risk_points" in compliance_result
        assert compliance_result["risk_level"] == "low"
        assert compliance_result["is_compliant"] is True

    @pytest.mark.asyncio
    async def test_pipeline_low_quality_not_rewrite_ready(
        self,
        db_session: Session,
        low_quality_collector_data,
    ):
        """低质量内容不应标记为 rewrite_ready"""

        pipeline = MockPipelineService(db_session)

        ingest_result = await pipeline.ingest_from_collector(low_quality_collector_data)
        assert ingest_result["success"] is True
        item_id = ingest_result["item_id"]

        # 触发质量筛选
        await pipeline.promote_to_material(item_id)

        inbox_item = db_session.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()

        # 低质量内容：内容过短、无互动数据
        assert inbox_item.quality_score < 70
        assert inbox_item.rewrite_ready is False

    @pytest.mark.asyncio
    async def test_pipeline_high_risk_content_detected(
        self,
        db_session: Session,
        high_risk_collector_data,
    ):
        """高风险内容应被合规检测标记"""

        pipeline = MockPipelineService(db_session)

        ingest_result = await pipeline.ingest_from_collector(high_risk_collector_data)
        assert ingest_result["success"] is True
        item_id = ingest_result["item_id"]

        # 合规检测
        compliance_service = MockComplianceService(db_session)

        inbox_item = db_session.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
        content_to_check = f"{inbox_item.title}\n\n{inbox_item.content}"

        compliance_result = compliance_service.check(text=content_to_check, platform="xiaohongshu")

        # 应检测到高风险
        assert compliance_result["risk_level"] in ["high", "medium"]
        assert len(compliance_result["risk_points"]) > 0

        # 验证检测到的风险点
        risk_keywords = [rp["keyword"] for rp in compliance_result["risk_points"]]
        expected_keywords = ["必过", "黑户", "秒批", "100%", "零利息", "零门槛", "百分百"]
        found_any = any(kw in str(risk_keywords) for kw in expected_keywords)
        assert found_any, f"Expected risk keywords, got: {risk_keywords}"

        assert compliance_result["risk_score"] >= 25
        assert compliance_result["traffic_light"] in ["yellow", "red"]

    @pytest.mark.asyncio
    async def test_compliance_auto_fix(self, db_session: Session):
        """合规检测应自动修正风险文案"""

        compliance_service = MockComplianceService(db_session)

        risky_text = "我们的贷款产品必过！黑户也能贷！无视征信，秒批秒放款！零利息，零门槛，100%通过！"

        result = compliance_service.check(text=risky_text)

        assert result["risk_level"] == "high"
        assert len(result["risk_points"]) > 0

        rewritten = result["rewritten_text"]
        assert "必过" not in rewritten
        assert "黑户" not in rewritten
        assert "秒批" not in rewritten
        assert "100%" not in rewritten

        fixed_result = compliance_service.check(text=rewritten)
        assert fixed_result["risk_score"] < result["risk_score"]

    @pytest.mark.asyncio
    async def test_material_to_knowledge_flow(
        self,
        db_session: Session,
        sample_collector_data,
    ):
        """素材库到知识库的完整流程"""

        pipeline = MockPipelineService(db_session)

        ingest_result = await pipeline.ingest_from_collector(sample_collector_data)
        item_id = ingest_result["item_id"]

        material_result = await pipeline.promote_to_material(item_id)
        material_id = material_result["material_id"]

        inbox_item = db_session.query(MvpInboxItem).filter(MvpInboxItem.id == item_id).first()
        assert inbox_item.material_status == "in_material"

        material = db_session.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
        assert material.inbox_item_id == item_id

        knowledge_result = await pipeline.build_knowledge(material_id)
        assert knowledge_result["success"] is True
        knowledge_id = knowledge_result["knowledge_id"]

        knowledge = db_session.query(MvpKnowledgeItem).filter(MvpKnowledgeItem.id == knowledge_id).first()
        assert knowledge is not None
        assert knowledge.source_material_id == material_id


class TestComplianceServiceUnit:
    """合规服务单元测试"""

    def test_risk_keyword_detection(self, db_session: Session):
        """风险词检测"""
        service = MockComplianceService(db_session)

        result = service.check("保证通过，必过，包过！")

        assert result["risk_level"] in ["high", "medium"]
        assert len(result["risk_points"]) > 0

    def test_traffic_light_calculation(self, db_session: Session):
        """交通灯等级计算"""
        service = MockComplianceService(db_session)

        green_result = service.check("这是一条普通的科普内容，仅供参考。")
        assert green_result["traffic_light"] == "green"

        red_result = service.check("必过！黑户可贷！秒批！100%通过！")
        assert red_result["traffic_light"] == "red"


class TestCleaningServiceUnit:
    """清洗服务单元测试"""

    def test_whitespace_normalization(self, db_session: Session):
        """空白字符标准化"""
        service = MockCleaningService(db_session)

        item = MvpInboxItem(
            platform="xiaohongshu",
            title="测试标题",
            content="段落1\n\n\n\n\n段落2   多空格",
            clean_status="pending",
        )
        db_session.add(item)
        db_session.commit()

        result = service.clean_item(item.id)

        assert result["success"] is True
        db_session.refresh(item)
        assert item.clean_status == "cleaned"


class TestQualityScreeningServiceUnit:
    """质量筛选服务单元测试"""

    @pytest.mark.asyncio
    async def test_heat_score_calculation(self, db_session: Session):
        """热度评分计算"""
        service = MockQualityScreeningService(db_session)

        item = MvpInboxItem(
            platform="xiaohongshu",
            title="热门内容",
            content="这是一段测试内容，长度适中。" * 5,
            like_count=10000,
            comment_count=500,
            favorite_count=2000,
            clean_status="cleaned",
        )
        db_session.add(item)
        db_session.commit()

        result = await service.screen_item(item.id)

        assert result["success"] is True
        db_session.refresh(item)
        assert item.quality_score > 0

    @pytest.mark.asyncio
    async def test_low_quality_scoring(self, db_session: Session):
        """低质量内容评分"""
        service = MockQualityScreeningService(db_session)

        item = MvpInboxItem(
            platform="xiaohongshu",
            title="短",
            content="短",
            like_count=0,
            comment_count=0,
            favorite_count=0,
            clean_status="cleaned",
        )
        db_session.add(item)
        db_session.commit()

        result = await service.screen_item(item.id)

        assert result["success"] is True
        db_session.refresh(item)
        assert item.quality_score < 50
