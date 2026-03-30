"""反馈闭环服务 - 收集用户反馈、更新知识库质量评分、生成学习建议"""
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_

from app.models.models import (
    MvpGenerationFeedback,
    MvpKnowledgeQualityScore,
    MvpKnowledgeItem
)


class FeedbackService:
    """反馈闭环服务"""
    
    FEEDBACK_TAGS_OPTIONS = [
        "太长", "太短", "不够专业", "太生硬", "不相关", 
        "数据错误", "风格不符", "缺少关键信息", "风险敏感词", "其他"
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_generation_id(self) -> str:
        """生成唯一生成ID"""
        return f"gen_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    async def submit_feedback(
        self,
        generation_id: str,
        query: str,
        generated_text: str,
        feedback_type: str,
        modified_text: Optional[str] = None,
        rating: Optional[int] = None,
        feedback_tags: Optional[List[str]] = None,
        knowledge_ids_used: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        提交生成结果反馈
        
        Args:
            generation_id: 生成任务ID
            query: 原始查询/请求参数
            generated_text: 生成的文本
            feedback_type: 反馈类型 (adopted/modified/rejected)
            modified_text: 用户修改后的文本
            rating: 1-5评分
            feedback_tags: 反馈标签列表
            knowledge_ids_used: 引用的知识库条目IDs
        """
        # 创建反馈记录
        feedback = MvpGenerationFeedback(
            generation_id=generation_id,
            query=query,
            generated_text=generated_text,
            feedback_type=feedback_type,
            modified_text=modified_text,
            rating=rating,
            feedback_tags=json.dumps(feedback_tags, ensure_ascii=False) if feedback_tags else None,
            knowledge_ids_used=json.dumps(knowledge_ids_used) if knowledge_ids_used else None
        )
        self.db.add(feedback)
        self.db.flush()
        
        # 更新关联知识条目的质量评分
        scores_updated = 0
        if knowledge_ids_used:
            scores_updated = await self._update_quality_scores_for_feedback(
                knowledge_ids_used, feedback_type
            )
        
        self.db.commit()
        
        return {
            "success": True,
            "feedback_id": feedback.id,
            "message": "反馈提交成功",
            "quality_scores_updated": scores_updated
        }
    
    async def _update_quality_scores_for_feedback(
        self, 
        knowledge_ids: List[int], 
        feedback_type: str
    ) -> int:
        """更新知识库条目质量评分"""
        updated_count = 0
        
        for kid in knowledge_ids:
            # 获取或创建质量评分记录
            score_record = self.db.query(MvpKnowledgeQualityScore).filter(
                MvpKnowledgeQualityScore.knowledge_id == kid
            ).first()
            
            if not score_record:
                score_record = MvpKnowledgeQualityScore(
                    knowledge_id=kid,
                    reference_count=0,
                    positive_feedback=0,
                    negative_feedback=0,
                    neutral_feedback=0,
                    quality_score=0.5,
                    weight_boost=1.0
                )
                self.db.add(score_record)
                self.db.flush()
            
            # 更新引用次数
            score_record.reference_count += 1
            score_record.last_referenced_at = datetime.now()
            
            # 根据反馈类型更新计数
            if feedback_type == "adopted":
                score_record.positive_feedback += 1
            elif feedback_type == "rejected":
                score_record.negative_feedback += 1
            else:  # modified
                score_record.neutral_feedback += 1
            
            # 重新计算质量分
            score_record.quality_score = self._calculate_quality_score(
                score_record.positive_feedback,
                score_record.negative_feedback,
                score_record.neutral_feedback,
                score_record.reference_count
            )
            
            # 更新权重加成
            score_record.weight_boost = self._calculate_weight_boost(score_record.quality_score)
            
            updated_count += 1
        
        return updated_count
    
    def _calculate_quality_score(
        self, 
        positive: int, 
        negative: int, 
        neutral: int, 
        reference: int
    ) -> float:
        """
        计算质量评分
        
        公式: quality_score = (positive + 0.5 * neutral) / (positive + neutral + negative + 1)
        结果限制在 0-1 之间
        """
        total = positive + neutral + negative
        if total == 0:
            return 0.5  # 默认中等评分
        
        # 平滑处理：加入先验值避免极端情况
        prior_positive = 1.0  # 先验正面反馈
        prior_total = 2.0     # 先验总数
        
        score = (positive + 0.5 * neutral + prior_positive) / (total + prior_total)
        
        # 限制在 0.1-0.95 之间，避免极端值
        return max(0.1, min(0.95, score))
    
    def _calculate_weight_boost(self, quality_score: float) -> float:
        """
        计算权重加成
        
        - quality_score > 0.8: weight_boost = 1.5
        - quality_score < 0.3: weight_boost = 0.5
        - 其他: 线性插值
        """
        if quality_score >= 0.8:
            return 1.5
        elif quality_score <= 0.3:
            return 0.5
        else:
            # 线性插值：0.3->0.5, 0.8->1.5
            return 0.5 + (quality_score - 0.3) * (1.0 / 0.5)
    
    async def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """获取反馈统计"""
        since = datetime.now() - timedelta(days=days)
        
        # 总反馈数
        total = self.db.query(func.count(MvpGenerationFeedback.id)).filter(
            MvpGenerationFeedback.created_at >= since
        ).scalar() or 0
        
        if total == 0:
            return {
                "total_feedback": 0,
                "adopted_count": 0,
                "modified_count": 0,
                "rejected_count": 0,
                "adoption_rate": 0.0,
                "modification_rate": 0.0,
                "rejection_rate": 0.0,
                "avg_rating": None,
                "recent_feedback_count": 0
            }
        
        # 各类型计数
        adopted = self.db.query(func.count(MvpGenerationFeedback.id)).filter(
            and_(
                MvpGenerationFeedback.created_at >= since,
                MvpGenerationFeedback.feedback_type == "adopted"
            )
        ).scalar() or 0
        
        modified = self.db.query(func.count(MvpGenerationFeedback.id)).filter(
            and_(
                MvpGenerationFeedback.created_at >= since,
                MvpGenerationFeedback.feedback_type == "modified"
            )
        ).scalar() or 0
        
        rejected = self.db.query(func.count(MvpGenerationFeedback.id)).filter(
            and_(
                MvpGenerationFeedback.created_at >= since,
                MvpGenerationFeedback.feedback_type == "rejected"
            )
        ).scalar() or 0
        
        # 平均评分
        avg_rating = self.db.query(func.avg(MvpGenerationFeedback.rating)).filter(
            and_(
                MvpGenerationFeedback.created_at >= since,
                MvpGenerationFeedback.rating.isnot(None)
            )
        ).scalar()
        
        return {
            "total_feedback": total,
            "adopted_count": adopted,
            "modified_count": modified,
            "rejected_count": rejected,
            "adoption_rate": round(adopted / total, 3) if total > 0 else 0,
            "modification_rate": round(modified / total, 3) if total > 0 else 0,
            "rejection_rate": round(rejected / total, 3) if total > 0 else 0,
            "avg_rating": round(float(avg_rating), 2) if avg_rating else None,
            "recent_feedback_count": total
        }
    
    async def get_quality_rankings(self, limit: int = 20, order: str = "desc") -> List[Dict[str, Any]]:
        """获取知识库质量排行榜"""
        query = self.db.query(
            MvpKnowledgeQualityScore,
            MvpKnowledgeItem
        ).join(
            MvpKnowledgeItem, 
            MvpKnowledgeQualityScore.knowledge_id == MvpKnowledgeItem.id
        )
        
        if order == "desc":
            query = query.order_by(desc(MvpKnowledgeQualityScore.quality_score))
        else:
            query = query.order_by(MvpKnowledgeQualityScore.quality_score)
        
        results = query.limit(limit).all()
        
        items = []
        for score, knowledge in results:
            items.append({
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "quality_score": round(score.quality_score, 3),
                "reference_count": score.reference_count,
                "positive_feedback": score.positive_feedback,
                "negative_feedback": score.negative_feedback,
                "weight_boost": round(score.weight_boost, 2),
                "last_referenced_at": str(score.last_referenced_at) if score.last_referenced_at else None
            })
        
        return items
    
    async def get_learning_suggestions(self) -> Dict[str, Any]:
        """
        获取持续学习建议
        
        基于质量评分和使用情况，生成优化建议
        """
        suggestions = []
        boost_candidates = 0
        downgrade_candidates = 0
        remove_candidates = 0
        
        # 1. 高质量条目建议提升权重
        high_quality = self.db.query(
            MvpKnowledgeQualityScore, MvpKnowledgeItem
        ).join(
            MvpKnowledgeItem,
            MvpKnowledgeQualityScore.knowledge_id == MvpKnowledgeItem.id
        ).filter(
            and_(
                MvpKnowledgeQualityScore.quality_score >= 0.8,
                MvpKnowledgeQualityScore.reference_count >= 3
            )
        ).limit(10).all()
        
        for score, knowledge in high_quality:
            if score.weight_boost < 1.5:
                suggestions.append({
                    "type": "boost",
                    "knowledge_id": knowledge.id,
                    "title": knowledge.title,
                    "current_score": round(score.quality_score, 3),
                    "suggestion": "建议提升检索权重至 1.5x",
                    "priority": "high",
                    "reason": f"质量评分 {score.quality_score:.2f}，被引用 {score.reference_count} 次，正面反馈 {score.positive_feedback} 次"
                })
                boost_candidates += 1
        
        # 2. 低质量条目建议降权
        low_quality = self.db.query(
            MvpKnowledgeQualityScore, MvpKnowledgeItem
        ).join(
            MvpKnowledgeItem,
            MvpKnowledgeQualityScore.knowledge_id == MvpKnowledgeItem.id
        ).filter(
            and_(
                MvpKnowledgeQualityScore.quality_score <= 0.3,
                MvpKnowledgeQualityScore.reference_count >= 2
            )
        ).limit(10).all()
        
        for score, knowledge in low_quality:
            suggestions.append({
                "type": "downgrade",
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "current_score": round(score.quality_score, 3),
                "suggestion": "建议降低检索权重至 0.5x",
                "priority": "medium",
                "reason": f"质量评分 {score.quality_score:.2f}，负面反馈 {score.negative_feedback} 次"
            })
            downgrade_candidates += 1
        
        # 3. 冷数据建议标记
        thirty_days_ago = datetime.now() - timedelta(days=30)
        cold_data = self.db.query(
            MvpKnowledgeQualityScore, MvpKnowledgeItem
        ).join(
            MvpKnowledgeItem,
            MvpKnowledgeQualityScore.knowledge_id == MvpKnowledgeItem.id
        ).filter(
            and_(
                MvpKnowledgeQualityScore.reference_count == 0,
                MvpKnowledgeQualityScore.last_referenced_at == None,
                MvpKnowledgeItem.created_at < thirty_days_ago
            )
        ).limit(10).all()
        
        for score, knowledge in cold_data:
            suggestions.append({
                "type": "remove",
                "knowledge_id": knowledge.id,
                "title": knowledge.title,
                "current_score": round(score.quality_score, 3),
                "suggestion": "建议标记为冷数据或移除",
                "priority": "low",
                "reason": "创建超过30天且从未被引用"
            })
            remove_candidates += 1
        
        # 4. 用户修改模式分析
        modified_feedbacks = self.db.query(MvpGenerationFeedback).filter(
            MvpGenerationFeedback.feedback_type == "modified"
        ).limit(50).all()
        
        # 分析反馈标签
        tag_counts: Dict[str, int] = {}
        for fb in modified_feedbacks:
            if fb.feedback_tags:
                tags = json.loads(fb.feedback_tags) if isinstance(fb.feedback_tags, str) else fb.feedback_tags
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        if tag_counts:
            top_issue = max(tag_counts.items(), key=lambda x: x[1])
            suggestions.append({
                "type": "adjust",
                "knowledge_id": 0,
                "title": "全局优化建议",
                "current_score": 0,
                "suggestion": f"用户最常修改的问题: \"{top_issue[0]}\"（出现 {top_issue[1]} 次），建议优化相关内容",
                "priority": "medium",
                "reason": "基于用户修改模式分析"
            })
        
        return {
            "suggestions": suggestions,
            "boost_candidates": boost_candidates,
            "downgrade_candidates": downgrade_candidates,
            "remove_candidates": remove_candidates
        }
    
    async def apply_weight_adjustment(self) -> Dict[str, Any]:
        """
        应用权重调整
        
        根据质量评分自动调整检索权重：
        - quality_score > 0.8: weight_boost = 1.5
        - quality_score < 0.3: weight_boost = 0.5
        - reference_count == 0 且创建超30天: 标记为冷数据
        """
        boosted_count = 0
        downgraded_count = 0
        cold_marked_count = 0
        details = []
        
        # 提升高质量条目权重
        high_quality = self.db.query(MvpKnowledgeQualityScore).filter(
            MvpKnowledgeQualityScore.quality_score >= 0.8
        ).all()
        
        for score in high_quality:
            if score.weight_boost != 1.5:
                old_boost = score.weight_boost
                score.weight_boost = 1.5
                boosted_count += 1
                details.append({
                    "knowledge_id": score.knowledge_id,
                    "action": "boost",
                    "old_value": round(old_boost, 2),
                    "new_value": 1.5
                })
        
        # 降低低质量条目权重
        low_quality = self.db.query(MvpKnowledgeQualityScore).filter(
            MvpKnowledgeQualityScore.quality_score <= 0.3
        ).all()
        
        for score in low_quality:
            if score.weight_boost != 0.5:
                old_boost = score.weight_boost
                score.weight_boost = 0.5
                downgraded_count += 1
                details.append({
                    "knowledge_id": score.knowledge_id,
                    "action": "downgrade",
                    "old_value": round(old_boost, 2),
                    "new_value": 0.5
                })
        
        # 标记冷数据（通过设置较低的权重）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        cold_data = self.db.query(MvpKnowledgeQualityScore).join(
            MvpKnowledgeItem,
            MvpKnowledgeQualityScore.knowledge_id == MvpKnowledgeItem.id
        ).filter(
            and_(
                MvpKnowledgeQualityScore.reference_count == 0,
                MvpKnowledgeQualityScore.last_referenced_at == None,
                MvpKnowledgeItem.created_at < thirty_days_ago
            )
        ).all()
        
        for score in cold_data:
            if score.weight_boost > 0.5:
                old_boost = score.weight_boost
                score.weight_boost = 0.3
                cold_marked_count += 1
                details.append({
                    "knowledge_id": score.knowledge_id,
                    "action": "cold_mark",
                    "old_value": round(old_boost, 2),
                    "new_value": 0.3
                })
        
        self.db.commit()
        
        message = f"权重调整完成: 提升 {boosted_count} 条, 降权 {downgraded_count} 条, 冷标记 {cold_marked_count} 条"
        
        return {
            "boosted_count": boosted_count,
            "downgraded_count": downgraded_count,
            "cold_marked_count": cold_marked_count,
            "message": message,
            "details": details[:50]  # 只返回前50条详情
        }
    
    def get_feedback_tags_options(self) -> List[str]:
        """获取可用的反馈标签选项"""
        return self.FEEDBACK_TAGS_OPTIONS
