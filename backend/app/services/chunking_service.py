"""知识切块服务 - 支持4种切块策略"""
import logging
import re
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.models import MvpKnowledgeItem, MvpKnowledgeChunk
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


# 分库到切块策略的映射
LIBRARY_CHUNK_STRATEGY = {
    "hot_content": ["post", "paragraph"],      # 爆款: 帖子级+段落级
    "industry_phrases": ["post", "paragraph"],  # 行业话术: 帖子级+段落级
    "platform_rules": ["rule"],                 # 平台规则: 规则级
    "audience_profile": ["post"],               # 人群画像: 帖子级
    "account_positioning": ["template"],        # 账号定位: 模板级
    "prompt_templates": ["template"],           # 提示词: 模板级
    "compliance_rules": ["rule"],               # 审核规则: 规则级
}


class ChunkingService:
    """知识切块服务"""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = get_embedding_service()

    async def process_and_store_chunks(
        self, knowledge_id: int, embedding_model: str = "volcano"
    ) -> Dict:
        # embedding_model参数已废弃，保留以兼容旧调用
        """对一条知识进行切块、向量化、入库
        Args:
            knowledge_id: 知识条目ID
            embedding_model: "volcano" 或 "local"
        Returns:
            {success, chunk_count, message}
        """
        # 获取知识条目
        item = self.db.query(MvpKnowledgeItem).filter(
            MvpKnowledgeItem.id == knowledge_id
        ).first()
        if not item:
            return {"success": False, "chunk_count": 0, "message": "知识条目不存在"}

        # 删除已有切块(重新切块)
        self.db.query(MvpKnowledgeChunk).filter(
            MvpKnowledgeChunk.knowledge_id == knowledge_id
        ).delete()

        # 根据library_type选择切块策略
        library_type = item.library_type or "industry_phrases"
        strategies = LIBRARY_CHUNK_STRATEGY.get(library_type, ["post"])

        chunks_data = []
        for strategy in strategies:
            if strategy == "post":
                chunks_data.extend(self._chunk_post_level(item))
            elif strategy == "paragraph":
                chunks_data.extend(self._chunk_paragraph_level(item))
            elif strategy == "rule":
                chunks_data.extend(self._chunk_rule_level(item))
            elif strategy == "template":
                chunks_data.extend(self._chunk_template_level(item))

        # 生成embedding并存储
        stored_count = 0
        for i, chunk_data in enumerate(chunks_data):
            try:
                # 生成embedding - 新版EmbeddingService只接受text参数
                embedding = await self.embedding_service.generate_embedding(
                    chunk_data["content"]
                )

                # 创建chunk记录 - embedding直接写入List[float]，无需json序列化
                chunk = MvpKnowledgeChunk(
                    knowledge_id=knowledge_id,
                    chunk_type=chunk_data["chunk_type"],
                    chunk_index=i,
                    content=chunk_data["content"],
                    metadata_json=chunk_data.get("metadata", {}),
                    embedding=embedding,  # 直接写入List[float]，pgvector Vector类型
                    token_count=len(chunk_data["content"]),  # 简易估算
                )
                self.db.add(chunk)
                stored_count += 1
            except Exception as e:
                logger.error(f"切块存储失败 knowledge_id={knowledge_id}, chunk={i}: {e}")

        self.db.commit()
        return {
            "success": True,
            "chunk_count": stored_count,
            "message": f"成功切块{stored_count}条"
        }

    def _chunk_post_level(self, item: MvpKnowledgeItem) -> List[Dict]:
        """帖子级切块: 完整内容+元数据作为一个chunk"""
        content = f"{item.title or ''}\n\n{item.content or ''}"
        metadata = {
            "type": "post",
            "title": item.title or "",
            "platform": item.platform or "",
            "audience": item.audience or "",
            "topic": getattr(item, 'topic', '') or "",
            "content_type": getattr(item, 'content_type', '') or "",
            "library_type": item.library_type or "",
            "is_hot": getattr(item, 'is_hot', False),
            "like_count": getattr(item, 'like_count', 0) or 0,
            "comment_count": getattr(item, 'comment_count', 0) or 0,
        }
        return [{"chunk_type": "post", "content": content.strip(), "metadata": metadata}]

    def _chunk_paragraph_level(self, item: MvpKnowledgeItem) -> List[Dict]:
        """段落级切块: 拆成标题/开头、中间论述、结尾CTA"""
        chunks = []
        content = item.content or ""
        title = item.title or ""

        # 按段落分割
        paragraphs = [p.strip() for p in re.split(r'\n{2,}|\r\n{2,}', content) if p.strip()]

        if not paragraphs:
            # 没有明确段落分割，按句子分
            sentences = re.split(r'[。！？\n]', content)
            sentences = [s.strip() for s in sentences if s.strip()]
            if len(sentences) <= 3:
                paragraphs = sentences
            else:
                # 三等分
                third = len(sentences) // 3
                paragraphs = [
                    '。'.join(sentences[:third]) + '。',
                    '。'.join(sentences[third:2*third]) + '。',
                    '。'.join(sentences[2*third:]) + '。',
                ]

        if len(paragraphs) >= 3:
            # 开头(标题+第一段)
            opening = f"{title}\n{paragraphs[0]}" if title else paragraphs[0]
            chunks.append({
                "chunk_type": "paragraph",
                "content": opening,
                "metadata": {"position": "opening", "title": title}
            })

            # 中间论述(中间段落合并)
            middle = "\n".join(paragraphs[1:-1])
            if middle.strip():
                chunks.append({
                    "chunk_type": "paragraph",
                    "content": middle,
                    "metadata": {"position": "body", "title": title}
                })

            # 结尾CTA
            chunks.append({
                "chunk_type": "paragraph",
                "content": paragraphs[-1],
                "metadata": {"position": "ending_cta", "title": title}
            })
        elif len(paragraphs) == 2:
            chunks.append({
                "chunk_type": "paragraph",
                "content": f"{title}\n{paragraphs[0]}" if title else paragraphs[0],
                "metadata": {"position": "opening", "title": title}
            })
            chunks.append({
                "chunk_type": "paragraph",
                "content": paragraphs[1],
                "metadata": {"position": "ending_cta", "title": title}
            })
        elif len(paragraphs) == 1:
            chunks.append({
                "chunk_type": "paragraph",
                "content": f"{title}\n{paragraphs[0]}" if title else paragraphs[0],
                "metadata": {"position": "full", "title": title}
            })

        return chunks

    def _chunk_rule_level(self, item: MvpKnowledgeItem) -> List[Dict]:
        """规则级切块: 每条规则独立存储"""
        chunks = []
        content = item.content or ""

        # 尝试按编号、换行、分号等分割规则
        rules = re.split(r'\n+|\d+[.、）)]\s*|；|;', content)
        rules = [r.strip() for r in rules if r.strip() and len(r.strip()) > 5]

        if not rules:
            # 无法分割，整体作为一条规则
            rules = [content.strip()]

        for i, rule in enumerate(rules):
            chunks.append({
                "chunk_type": "rule",
                "content": rule,
                "metadata": {
                    "rule_index": i,
                    "platform": item.platform or "",
                    "category": item.category or "",
                    "risk_level": getattr(item, 'risk_level', '') or "",
                    "library_type": item.library_type or "",
                }
            })

        return chunks

    def _chunk_template_level(self, item: MvpKnowledgeItem) -> List[Dict]:
        """模板级切块: 开头模板/CTA模板/语气模板等"""
        chunks = []
        content = item.content or ""
        category = item.category or ""

        # 根据category判断模板类型
        template_type = "general"
        if "语气" in category or "账号" in category:
            template_type = "tone"
        elif "CTA" in category or "转化" in category:
            template_type = "cta"
        elif "开头" in category or "钩子" in category:
            template_type = "opening"
        elif "提示词" in category or "prompt" in category.lower():
            template_type = "prompt"

        # 整体作为一个模板chunk
        chunks.append({
            "chunk_type": "template",
            "content": f"{item.title or ''}\n{content}".strip(),
            "metadata": {
                "template_type": template_type,
                "platform": item.platform or "",
                "style": item.style or "",
                "library_type": item.library_type or "",
            }
        })

        return chunks


def get_chunking_service(db: Session) -> ChunkingService:
    return ChunkingService(db)
