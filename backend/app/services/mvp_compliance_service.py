"""MVP 合规审核服务 - 增强版（双引擎：规则+大模型语义检测）"""
import re
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models.models import MvpComplianceRule
from app.core.config import settings

logger = logging.getLogger(__name__)


class MvpComplianceService:
    def __init__(self, db: Session):
        self.db = db

    # 默认风险词（当数据库无规则时使用）
    DEFAULT_RISKY_KEYWORDS = {
        "必过": ("high", "建议替换为'通过率较高'"),
        "包过": ("high", "建议替换为'成功率较高'"),
        "秒批": ("high", "建议替换为'审批较快'"),
        "秒放款": ("high", "建议替换为'放款较快'"),
        "黑户可贷": ("high", "建议替换为'多种方案可选'"),
        "无视征信": ("high", "建议替换为'综合评估'"),
        "不看征信": ("high", "建议替换为'多维度评估'"),
        "100%通过": ("high", "建议移除绝对承诺"),
        "零利息": ("medium", "建议替换为'优惠利率'"),
        "免息": ("medium", "建议替换为'限时优惠'"),
        "低门槛": ("medium", "建议替换为'门槛灵活'"),
        "不上征信": ("medium", "建议说明具体以产品为准"),
        "随借随还": ("low", "建议说明还款灵活"),
    }

    def check(self, text: str, enable_llm: bool = True, model: str = "volcano") -> dict:
        """
        检查文案合规性（双引擎）
        
        第一层：基于规则的关键词/正则匹配
        第二层：大模型语义级风险检测（可选）
        
        Args:
            text: 待检查文本
            enable_llm: 是否启用大模型语义检测
            model: 模型选择 volcano/local
        """
        risk_points = []
        total_score = 0
        
        # 从数据库加载规则
        rules = self._load_rules()
        for rule in rules:
            keyword = rule.get("keyword", "")
            if keyword.lower() in text.lower():
                risk_level = rule.get("risk_level", "medium")
                suggestion = rule.get("suggestion", f"建议替换'{keyword}'为更合规的表达")
                risk_points.append({
                    "keyword": keyword,
                    "reason": f"包含{risk_level}级风险词: {keyword}",
                    "suggestion": suggestion
                })
                if risk_level == "high":
                    total_score += 30
                elif risk_level == "medium":
                    total_score += 15
                else:
                    total_score += 5
        
        # 正则检查：绝对承诺模式
        absolute_patterns = [
            (r"100%", "包含绝对承诺表达"),
            (r"保证.*通过", "包含保证承诺"),
            (r"一定.*批", "包含绝对承诺"),
            (r"无条件", "包含无条件承诺"),
            (r"(肯定|必然|绝对).*通过", "包含绝对化表达"),
        ]
        for pattern, reason in absolute_patterns:
            if re.search(pattern, text):
                risk_points.append({
                    "keyword": pattern,
                    "reason": reason,
                    "suggestion": "请移除绝对化表达"
                })
                total_score += 20
        
        # 生成修正版
        rewritten_text = self._auto_fix(text, risk_points)
        
        # 第二层：大模型语义检测（如果启用）
        llm_analysis = None
        llm_risk_points = []
        
        if enable_llm:
            try:
                # 同步调用异步方法
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    llm_result = loop.run_until_complete(
                        self._llm_semantic_check(text, model)
                    )
                    llm_analysis = llm_result.get("analysis", "")
                    llm_risk_points = llm_result.get("risk_points", [])
                    
                    # 合并LLM检测到的风险点
                    for rp in llm_risk_points:
                        rp["source"] = "llm"
                        risk_points.append(rp)
                        # LLM检测的风险点也计分
                        if rp.get("severity") == "high":
                            total_score += 25
                        elif rp.get("severity") == "medium":
                            total_score += 15
                        else:
                            total_score += 8
                finally:
                    loop.close()
            except Exception as e:
                logger.warning(f"LLM语义检测失败，仅使用规则匹配: {e}")
                llm_analysis = f"[大模型检测跳过: {str(e)[:50]}]"
        
        # 重新计算风险等级
        if total_score >= 50:
            risk_level = "high"
        elif total_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # 生成建议（去重）
        suggestions = list(set(rp.get("suggestion", "") for rp in risk_points if rp.get("suggestion")))
        
        # 如果LLM检测到了新风险，重新生成修正版
        if llm_risk_points:
            rewritten_text = self._auto_fix(text, risk_points)
        
        return {
            "risk_level": risk_level,
            "risk_score": min(total_score, 100),
            "risk_points": risk_points,
            "suggestions": suggestions,
            "rewritten_text": rewritten_text,
            "is_compliant": risk_level == "low",
            "llm_analysis": llm_analysis,
            "auto_fixed_text": rewritten_text  # 别名，保持兼容
        }

    def _load_rules(self) -> list:
        """从数据库加载规则，失败时使用默认规则"""
        try:
            db_rules = self.db.query(MvpComplianceRule).all()
            if db_rules:
                return [
                    {"keyword": r.keyword, "risk_level": r.risk_level, "suggestion": r.suggestion}
                    for r in db_rules
                ]
        except Exception:
            pass
        
        # 使用默认规则
        return [
            {"keyword": kw, "risk_level": level, "suggestion": sug}
            for kw, (level, sug) in self.DEFAULT_RISKY_KEYWORDS.items()
        ]

    def _auto_fix(self, text: str, risk_points: list) -> str:
        """自动修正风险词"""
        fixed = text
        replacements = {
            "必过": "通过率较高",
            "包过": "成功率较高",
            "秒批": "审批较快",
            "秒放款": "放款较快",
            "黑户可贷": "多种方案可选",
            "无视征信": "综合评估",
            "100%通过": "通过率较高",
            "不看征信": "多维度评估",
            "零利息": "优惠利率",
            "免息": "限时优惠",
            "低门槛": "门槛灵活",
            "不上征信": "具体以产品为准",
            "随借随还": "还款灵活"
        }
        for old, new in replacements.items():
            fixed = fixed.replace(old, new)
        return fixed

    def add_rule(self, keyword: str, risk_level: str = "medium", suggestion: str = None):
        """添加合规规则"""
        try:
            existing = self.db.query(MvpComplianceRule).filter(
                MvpComplianceRule.keyword == keyword
            ).first()
            if existing:
                existing.risk_level = risk_level
                existing.suggestion = suggestion
            else:
                rule = MvpComplianceRule(
                    rule_type="keyword",
                    keyword=keyword,
                    risk_level=risk_level,
                    suggestion=suggestion
                )
                self.db.add(rule)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"添加规则失败: {str(e)}")

    def list_rules(self):
        """列出所有规则"""
        try:
            return self.db.query(MvpComplianceRule).all()
        except Exception:
            return []

    def delete_rule(self, rule_id: int):
        """删除规则"""
        try:
            rule = self.db.query(MvpComplianceRule).filter(MvpComplianceRule.id == rule_id).first()
            if rule:
                self.db.delete(rule)
                self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise ValueError(f"删除规则失败: {str(e)}")

    def batch_check(self, texts: list) -> list:
        """批量合规检查"""
        return [self.check(t) for t in texts]

    async def _llm_semantic_check(self, text: str, model: str = "volcano") -> Dict[str, Any]:
        """
        大模型语义级风险检测
        
        检测维度：
        - 隐含风险：暗示性承诺、模糊表达
        - 绝对承诺：变相的100%保证
        - 夸大宣传：过度夸大效果
        - 合规建议：如何修正
        """
        try:
            from app.services.ai_service import AIService
            ai_svc = AIService(self.db)
            
            system_prompt = """你是金融合规审核专家。请从以下维度分析文案的合规风险：
1. 是否有隐含的绝对承诺（如变相的"必过""包下款"）
2. 是否有夸大宣传（过度夸大效果或收益）
3. 是否有模糊误导（让用户产生不切实际的期望）
4. 是否有违规引导（诱导用户做高风险决策）

请严格按JSON格式返回：
{
    "has_risk": true/false,
    "risk_points": [
        {
            "keyword": "问题表述",
            "reason": "风险原因",
            "suggestion": "修改建议",
            "severity": "high/medium/low"
        }
    ],
    "analysis": "整体分析总结",
    "suggested_rewrite": "建议修改后的文案（可选）"
}"""
            
            prompt = f"""请分析以下金融获客文案的合规风险：

---文案内容---
{text[:2000]}
---

请以JSON格式返回分析结果。"""
            
            use_cloud = model == "volcano"
            raw_response = await ai_svc.call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                use_cloud=use_cloud,
                scene="compliance_semantic_check"
            )
            
            # 解析LLM返回的JSON
            result = self._parse_llm_compliance_result(raw_response)
            return result
            
        except Exception as e:
            logger.warning(f"LLM语义检测异常: {e}")
            return {
                "has_risk": False,
                "risk_points": [],
                "analysis": f"检测失败: {str(e)[:100]}"
            }

    def _parse_llm_compliance_result(self, raw_response: str) -> Dict[str, Any]:
        """解析LLM返回的合规检测结果"""
        try:
            # 尝试提取JSON部分
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = raw_response[start:end]
                data = json.loads(json_str)
                
                # 标准化风险点格式
                risk_points = []
                for rp in data.get("risk_points", []):
                    risk_points.append({
                        "keyword": rp.get("keyword", ""),
                        "reason": rp.get("reason", ""),
                        "suggestion": rp.get("suggestion", ""),
                        "severity": rp.get("severity", "medium"),
                        "source": "llm"
                    })
                
                return {
                    "has_risk": data.get("has_risk", False),
                    "risk_points": risk_points,
                    "analysis": data.get("analysis", ""),
                    "suggested_rewrite": data.get("suggested_rewrite", "")
                }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"解析LLM合规结果失败: {e}")
        
        # 如果解析失败，返回空结果
        return {
            "has_risk": False,
            "risk_points": [],
            "analysis": raw_response[:500] if raw_response else ""
        }

    async def check_async(self, text: str, enable_llm: bool = True, model: str = "volcano") -> dict:
        """
        异步版合规检查（供异步上下文调用）
        """
        risk_points = []
        total_score = 0
        
        # 第一层：规则检查
        rules = self._load_rules()
        for rule in rules:
            keyword = rule.get("keyword", "")
            if keyword.lower() in text.lower():
                risk_level = rule.get("risk_level", "medium")
                suggestion = rule.get("suggestion", f"建议替换'{keyword}'为更合规的表达")
                risk_points.append({
                    "keyword": keyword,
                    "reason": f"包含{risk_level}级风险词: {keyword}",
                    "suggestion": suggestion,
                    "source": "rule"
                })
                if risk_level == "high":
                    total_score += 30
                elif risk_level == "medium":
                    total_score += 15
                else:
                    total_score += 5
        
        # 正则检查
        absolute_patterns = [
            (r"100%", "包含绝对承诺表达"),
            (r"保证.*通过", "包含保证承诺"),
            (r"一定.*批", "包含绝对承诺"),
            (r"无条件", "包含无条件承诺"),
            (r"(肯定|必然|绝对).*通过", "包含绝对化表达"),
        ]
        for pattern, reason in absolute_patterns:
            if re.search(pattern, text):
                risk_points.append({
                    "keyword": pattern,
                    "reason": reason,
                    "suggestion": "请移除绝对化表达",
                    "source": "rule"
                })
                total_score += 20
        
        rewritten_text = self._auto_fix(text, risk_points)
        
        # 第二层：LLM语义检测
        llm_analysis = None
        if enable_llm:
            try:
                llm_result = await self._llm_semantic_check(text, model)
                llm_analysis = llm_result.get("analysis", "")
                llm_risk_points = llm_result.get("risk_points", [])
                
                for rp in llm_risk_points:
                    rp["source"] = "llm"
                    risk_points.append(rp)
                    if rp.get("severity") == "high":
                        total_score += 25
                    elif rp.get("severity") == "medium":
                        total_score += 15
                    else:
                        total_score += 8
                        
                if llm_risk_points:
                    rewritten_text = self._auto_fix(text, risk_points)
            except Exception as e:
                logger.warning(f"异步LLM语义检测失败: {e}")
                llm_analysis = f"[大模型检测跳过: {str(e)[:50]}]"
        
        # 计算风险等级
        if total_score >= 50:
            risk_level = "high"
        elif total_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        suggestions = list(set(rp.get("suggestion", "") for rp in risk_points if rp.get("suggestion")))
        
        return {
            "risk_level": risk_level,
            "risk_score": min(total_score, 100),
            "risk_points": risk_points,
            "suggestions": suggestions,
            "rewritten_text": rewritten_text,
            "is_compliant": risk_level == "low",
            "llm_analysis": llm_analysis,
            "auto_fixed_text": rewritten_text
        }
