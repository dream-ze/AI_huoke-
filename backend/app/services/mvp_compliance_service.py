"""MVP 合规审核服务 - 增强版（四层检测体系）

四层检测体系：
- 第一层：硬规则拦截（助贷专用敏感词）
- 第二层：语义风险识别（暗示性违规表达）
- 第三层：平台规则映射（平台特定规则）
- 第四层：自动降风险改写建议

红黄绿灯分级：
- 红灯 (red): 命中硬规则或高风险语义 → 禁止发
- 黄灯 (yellow): 中等风险表达或平台规则 → 建议改
- 绿灯 (green): 无风险或低风险 → 可发
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.models.models import MvpComplianceRule
from app.services.platform_rule_service import PlatformRuleService, check_text_against_rules
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MvpComplianceService:
    def __init__(self, db: Session):
        self.db = db

    # ============================================================
    # 第一层：硬规则 - 助贷专用敏感词（当数据库无规则时使用）
    # ============================================================

    # 承诺下款类 - 高风险
    LOAN_PROMISE_KEYWORDS = {
        "包下款": ("high", "帮您匹配适合的产品方案"),
        "保证通过": ("high", "协助提升通过率"),
        "100%放款": ("high", "为您匹配合适产品"),
        "必下": ("high", "为您推荐合适方案"),
        "秒批": ("high", "审批流程便捷"),
        "秒到": ("high", "放款时效较快"),
        "必过": ("high", "通过率较高"),
        "包过": ("high", "成功率较高"),
        "秒放款": ("high", "放款较快"),
        "黑户可贷": ("high", "多种方案可选"),
        "100%通过": ("high", "通过率较高"),
    }

    # 包装资料类 - 高风险
    LOAN_PACKAGING_KEYWORDS = {
        "包装银行流水": ("high", "提供真实资质证明"),
        "做假资料": ("high", "准备合规材料"),
        "代开证明": ("high", "自行办理相关证明"),
        "包装资料": ("high", "完善资质材料"),
        "虚假流水": ("high", "提供真实银行流水"),
    }

    # 征信类 - 高风险
    LOAN_CREDIT_KEYWORDS = {
        "无视征信": ("high", "多种产品方案可选"),
        "征信洗白": ("high", "改善信用记录"),
        "征信修复": ("high", "规范征信管理"),
        "消除逾期": ("high", "按时还款改善记录"),
        "不看征信": ("high", "多维度评估"),
        "洗白征信": ("high", "合规维护信用"),
    }

    # 利率误导类 - 中高风险
    LOAN_INTEREST_KEYWORDS = {
        "零利息": ("high", "利率优惠"),
        "免息贷款": ("high", "限时优惠活动"),
        "无手续费": ("medium", "低手续费方案"),
        "全网最低": ("high", "具有竞争力利率"),
        "免息": ("medium", "限时优惠"),
    }

    # 诱导夸大类 - 中高风险
    LOAN_INDUCE_KEYWORDS = {
        "内部渠道": ("high", "正规产品渠道"),
        "特殊通道": ("high", "标准审批流程"),
        "限时放款": ("medium", "高效审批放款"),
        "有关系": ("high", "专业服务团队"),
        "有渠道": ("high", "合作机构资源"),
        "内部门路": ("high", "正规渠道申请"),
    }

    # 合并所有助贷专用敏感词
    LOAN_SPECIFIC_KEYWORDS = {}
    LOAN_SPECIFIC_KEYWORDS.update(LOAN_PROMISE_KEYWORDS)
    LOAN_SPECIFIC_KEYWORDS.update(LOAN_PACKAGING_KEYWORDS)
    LOAN_SPECIFIC_KEYWORDS.update(LOAN_CREDIT_KEYWORDS)
    LOAN_SPECIFIC_KEYWORDS.update(LOAN_INTEREST_KEYWORDS)
    LOAN_SPECIFIC_KEYWORDS.update(LOAN_INDUCE_KEYWORDS)

    # ============================================================
    # 第二层：语义风险 - 暗示性违规表达
    # ============================================================

    # 暗示性违规表达模式（关键词组合 + 风险原因）
    SEMANTIC_RISK_PATTERNS = [
        # 暗示包装类
        (r"帮你搞定", "暗示非正规操作", "high", "协助您完成申请流程"),
        (r"帮你办", "暗示非正规操作", "medium", "协助您办理"),
        (r"帮你弄", "暗示非正规操作", "medium", "协助您处理"),
        # 暗示无视风控类
        (r"不看.*征信", "暗示规避风控", "high", "综合评估信用状况"),
        (r"不查.*征信", "暗示规避风控", "high", "多维度信用评估"),
        (r"不管.*征信", "暗示规避风控", "high", "全面评估资质"),
        # 暗示快速放款类
        (r"快速到账", "暗示过度承诺时效", "medium", "高效审批流程"),
        (r"极速放款", "暗示过度承诺时效", "medium", "便捷审批服务"),
        (r"当天.*下款", "暗示过度承诺时效", "medium", "较快审批时效"),
        # 暗示内部关系类
        (r"有关系.*[通下放]", "暗示非正规渠道", "high", "专业服务支持"),
        (r"有渠道.*贷款", "暗示非正规渠道", "high", "正规产品渠道"),
        (r"内部.*关系", "暗示非正规渠道", "high", "专业团队服务"),
        # 暗示承诺类
        (r"没问题.*下款", "暗示承诺下款", "high", "为您匹配合适方案"),
        (r"肯定.*能.*贷", "暗示承诺下款", "high", "协助提升成功率"),
        (r"稳.*下款", "暗示承诺下款", "high", "为您匹配稳健方案"),
    ]

    # 默认风险词（当数据库无规则时使用）- 保留原有规则
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

    def check(self, text: str, enable_llm: bool = True, model: str = "volcano", platform: Optional[str] = None) -> dict:
        """
        检查文案合规性（四层检测体系）

        第一层：基于规则的关键词/正则匹配（通用规则）
        第二层：大模型语义级风险检测（可选）
        第三层：平台专属规则检测（当指定platform时）
        第四层：自动改写修正

        Args:
            text: 待检查文本
            enable_llm: 是否启用大模型语义检测
            model: 模型选择 volcano/local
            platform: 平台名称 (xiaohongshu/douyin/zhihu/weixin)，None时不进行平台规则检测
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
                risk_points.append(
                    {"keyword": keyword, "reason": f"包含{risk_level}级风险词: {keyword}", "suggestion": suggestion}
                )
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
                risk_points.append({"keyword": pattern, "reason": reason, "suggestion": "请移除绝对化表达"})
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
                    llm_result = loop.run_until_complete(self._llm_semantic_check(text, model))
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

        # 第三层：平台专属规则检测（当指定platform时）
        platform_risk_points = []
        if platform:
            try:
                platform_risk_points = self._check_platform_rules(text, platform)
                for rp in platform_risk_points:
                    rp["source"] = "platform_rule"
                    risk_points.append(rp)
                    # 平台规则风险计分
                    if rp.get("risk_level") == "high":
                        total_score += 25
                    elif rp.get("risk_level") == "medium":
                        total_score += 12
                    else:
                        total_score += 5
            except Exception as e:
                logger.warning(f"平台规则检测失败: {e}")

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
            rewritten_text = self._auto_fix(text, risk_points, platform)

        # 计算交通灯等级
        traffic_light = self._calculate_traffic_light(total_score, risk_points)

        return {
            "risk_level": risk_level,
            "risk_score": min(total_score, 100),
            "risk_points": risk_points,
            "suggestions": suggestions,
            "rewritten_text": rewritten_text,
            "is_compliant": risk_level == "low",
            "llm_analysis": llm_analysis,
            "auto_fixed_text": rewritten_text,  # 别名，保持兼容
            "traffic_light": traffic_light,  # 新增字段
        }

    def _load_rules(self) -> list:
        """从数据库加载规则，失败时使用默认规则"""
        try:
            db_rules = self.db.query(MvpComplianceRule).all()
            if db_rules:
                return [
                    {"keyword": r.keyword, "risk_level": r.risk_level, "suggestion": r.suggestion} for r in db_rules
                ]
        except Exception:
            pass

        # 使用默认规则
        return [
            {"keyword": kw, "risk_level": level, "suggestion": sug}
            for kw, (level, sug) in self.DEFAULT_RISKY_KEYWORDS.items()
        ]

    def _auto_fix(self, text: str, risk_points: list, platform: Optional[str] = None) -> str:
        """自动修正风险词（增强版：优先使用数据库模板）"""
        fixed = text

        # 第一步：尝试从数据库加载改写模板
        try:
            from app.services.platform_rule_service import PlatformRuleService

            platform_svc = PlatformRuleService(self.db)
            templates = platform_svc.get_rewrite_templates(platform=platform)

            for tmpl in templates:
                trigger = tmpl.get("trigger_pattern", "")
                alternative = tmpl.get("safe_alternative", "")
                if trigger and alternative:
                    # 尝试正则替换
                    try:
                        fixed = re.sub(trigger, alternative, fixed, flags=re.IGNORECASE)
                    except re.error:
                        # 如果不是有效正则，做普通字符串替换
                        fixed = fixed.replace(trigger, alternative)
        except Exception as e:
            logger.warning(f"加载改写模板失败，使用默认替换: {e}")

        # 第二步：硬编码替换作为兜底
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
            "随借随还": "还款灵活",
        }
        for old, new in replacements.items():
            fixed = fixed.replace(old, new)
        return fixed

    def add_rule(self, keyword: str, risk_level: str = "medium", suggestion: str = None):
        """添加合规规则"""
        try:
            existing = self.db.query(MvpComplianceRule).filter(MvpComplianceRule.keyword == keyword).first()
            if existing:
                existing.risk_level = risk_level
                existing.suggestion = suggestion
            else:
                rule = MvpComplianceRule(
                    rule_type="keyword", keyword=keyword, risk_level=risk_level, suggestion=suggestion
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

    def _check_platform_rules(self, text: str, platform: str) -> List[Dict[str, Any]]:
        """
        检查平台专属规则

        Args:
            text: 待检查文本
            platform: 平台名称

        Returns:
            匹配的风险点列表
        """
        try:
            platform_svc = PlatformRuleService(self.db)
            rules = platform_svc.get_rules_by_platform(platform)
            return check_text_against_rules(text, rules)
        except Exception as e:
            logger.warning(f"平台规则检查异常: {e}")
            return []

    def _calculate_traffic_light(self, total_score: int, risk_points: List[Dict]) -> str:
        """
        计算交通灯等级

        规则：
        - green: score < 25 且无高风险
        - yellow: 25 <= score < 50 或有中等风险
        - red: score >= 50 或有高风险

        Args:
            total_score: 总风险分
            risk_points: 风险点列表

        Returns:
            "green" / "yellow" / "red"
        """
        # 检查是否有高风险
        has_high_risk = any(rp.get("risk_level") == "high" or rp.get("severity") == "high" for rp in risk_points)
        has_medium_risk = any(rp.get("risk_level") == "medium" or rp.get("severity") == "medium" for rp in risk_points)

        # 红灯：分数>=50 或存在高风险
        if total_score >= 50 or has_high_risk:
            return "red"

        # 黄灯：分数>=25 或存在中等风险
        if total_score >= 25 or has_medium_risk:
            return "yellow"

        # 绿灯：分数<25 且无中等及以上风险
        return "green"

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
                prompt=prompt, system_prompt=system_prompt, use_cloud=use_cloud, scene="compliance_semantic_check"
            )

            # 解析LLM返回的JSON
            result = self._parse_llm_compliance_result(raw_response)
            return result

        except Exception as e:
            logger.warning(f"LLM语义检测异常: {e}")
            return {"has_risk": False, "risk_points": [], "analysis": f"检测失败: {str(e)[:100]}"}

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
                    risk_points.append(
                        {
                            "keyword": rp.get("keyword", ""),
                            "reason": rp.get("reason", ""),
                            "suggestion": rp.get("suggestion", ""),
                            "severity": rp.get("severity", "medium"),
                            "source": "llm",
                        }
                    )

                return {
                    "has_risk": data.get("has_risk", False),
                    "risk_points": risk_points,
                    "analysis": data.get("analysis", ""),
                    "suggested_rewrite": data.get("suggested_rewrite", ""),
                }
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"解析LLM合规结果失败: {e}")

        # 如果解析失败，返回空结果
        return {"has_risk": False, "risk_points": [], "analysis": raw_response[:500] if raw_response else ""}

    def four_layer_check(self, text: str, platform: Optional[str] = None) -> Dict[str, Any]:
        """
        四层合规检测 - 返回详细的分层检测结果

        Args:
            text: 待检查文本
            platform: 平台名称 (xiaohongshu/douyin/zhihu/weixin)，可选

        Returns:
            {
                "traffic_light": "green" | "yellow" | "red",
                "overall_risk_score": float,
                "layer_results": {
                    "layer1_hard_rules": {...},
                    "layer2_semantic_risks": {...},
                    "layer3_platform_rules": {...},
                    "layer4_rewrite_suggestions": {...}
                },
                "rewrite_suggestions": [...],
                "final_text": str,  # 自动修正后的文本
            }
        """
        layer_results = {
            "layer1_hard_rules": {"hits": [], "has_high_risk": False},
            "layer2_semantic_risks": {"hits": [], "has_high_risk": False},
            "layer3_platform_rules": {"hits": [], "has_high_risk": False},
            "layer4_rewrite_suggestions": {"suggestions": []},
        }

        total_score = 0
        all_risk_points = []
        rewrite_suggestions = []

        # ============ 第一层：硬规则拦截 ============
        layer1_result = self._check_layer1_hard_rules(text)
        layer_results["layer1_hard_rules"] = layer1_result
        if layer1_result["hits"]:
            for hit in layer1_result["hits"]:
                all_risk_points.append({**hit, "layer": "layer1", "source": "hard_rule"})
                if hit.get("risk_level") == "high":
                    total_score += 35
                elif hit.get("risk_level") == "medium":
                    total_score += 20
                else:
                    total_score += 10
                rewrite_suggestions.append(
                    {
                        "original": hit.get("keyword", ""),
                        "suggestion": hit.get("safe_alternative", hit.get("suggestion", "")),
                        "layer": "layer1",
                    }
                )

        # ============ 第二层：语义风险识别 ============
        layer2_result = self._check_layer2_semantic_risks(text)
        layer_results["layer2_semantic_risks"] = layer2_result
        if layer2_result["hits"]:
            for hit in layer2_result["hits"]:
                all_risk_points.append({**hit, "layer": "layer2", "source": "semantic"})
                if hit.get("risk_level") == "high":
                    total_score += 30
                elif hit.get("risk_level") == "medium":
                    total_score += 15
                else:
                    total_score += 8
                rewrite_suggestions.append(
                    {
                        "original": hit.get("keyword", ""),
                        "suggestion": hit.get("safe_alternative", ""),
                        "layer": "layer2",
                    }
                )

        # ============ 第三层：平台规则映射 ============
        if platform:
            layer3_result = self._check_layer3_platform_rules(text, platform)
            layer_results["layer3_platform_rules"] = layer3_result
            if layer3_result["hits"]:
                for hit in layer3_result["hits"]:
                    all_risk_points.append({**hit, "layer": "layer3", "source": "platform_rule"})
                    if hit.get("risk_level") == "high":
                        total_score += 25
                    elif hit.get("risk_level") == "medium":
                        total_score += 12
                    else:
                        total_score += 5
                    rewrite_suggestions.append(
                        {
                            "original": hit.get("keyword", ""),
                            "suggestion": hit.get("suggestion", ""),
                            "layer": "layer3",
                        }
                    )

        # ============ 第四层：自动改写建议 ============
        final_text = self._auto_fix_four_layer(text, rewrite_suggestions)
        layer4_result = self._generate_layer4_suggestions(all_risk_points, final_text)
        layer_results["layer4_rewrite_suggestions"] = layer4_result

        # ============ 计算红黄绿灯 ============
        traffic_light = self._calculate_traffic_light_v2(total_score, layer_results)

        return {
            "traffic_light": traffic_light,
            "overall_risk_score": min(total_score, 100),
            "layer_results": layer_results,
            "rewrite_suggestions": rewrite_suggestions,
            "final_text": final_text,
            "risk_points": all_risk_points,
            "is_compliant": traffic_light == "green",
        }

    def _check_layer1_hard_rules(self, text: str) -> Dict[str, Any]:
        """第一层：硬规则拦截 - 检查助贷专用敏感词"""
        hits = []
        has_high_risk = False
        text_lower = text.lower()

        # 1. 检查助贷专用敏感词
        for keyword, (risk_level, safe_alt) in self.LOAN_SPECIFIC_KEYWORDS.items():
            if keyword.lower() in text_lower:
                # 查找关键词位置
                start = text_lower.find(keyword.lower())
                hits.append(
                    {
                        "keyword": keyword,
                        "risk_level": risk_level,
                        "reason": f"命中{risk_level}级风险词: {keyword}",
                        "suggestion": f"建议替换为: {safe_alt}",
                        "safe_alternative": safe_alt,
                        "position": {"start": start, "end": start + len(keyword)},
                        "category": self._get_keyword_category(keyword),
                    }
                )
                if risk_level == "high":
                    has_high_risk = True

        # 2. 检查数据库中的规则
        db_rules = self._load_rules()
        for rule in db_rules:
            keyword = rule.get("keyword", "")
            if keyword and keyword.lower() in text_lower:
                # 检查是否已在助贷敏感词中命中（去重）
                if not any(h.get("keyword", "").lower() == keyword.lower() for h in hits):
                    risk_level = rule.get("risk_level", "medium")
                    start = text_lower.find(keyword.lower())
                    hits.append(
                        {
                            "keyword": keyword,
                            "risk_level": risk_level,
                            "reason": f"命中{risk_level}级风险词: {keyword}",
                            "suggestion": rule.get("suggestion", f"建议替换'{keyword}'为更合规的表达"),
                            "safe_alternative": rule.get("suggestion", ""),
                            "position": {"start": start, "end": start + len(keyword)},
                            "category": "通用规则",
                        }
                    )
                    if risk_level == "high":
                        has_high_risk = True

        # 3. 检查绝对承诺正则
        absolute_patterns = [
            (r"100%", "包含绝对承诺表达"),
            (r"保证.*通过", "包含保证承诺"),
            (r"一定.*批", "包含绝对承诺"),
            (r"无条件", "包含无条件承诺"),
            (r"(肯定|必然|绝对).*通过", "包含绝对化表达"),
        ]
        for pattern, reason in absolute_patterns:
            match = re.search(pattern, text)
            if match:
                matched_text = match.group()
                # 去重检查
                if not any(h.get("keyword") == matched_text for h in hits):
                    hits.append(
                        {
                            "keyword": matched_text,
                            "risk_level": "high",
                            "reason": reason,
                            "suggestion": "请移除绝对化表达",
                            "safe_alternative": "提供合理预期",
                            "position": {"start": match.start(), "end": match.end()},
                            "category": "绝对承诺",
                        }
                    )
                    has_high_risk = True

        return {"hits": hits, "has_high_risk": has_high_risk, "hit_count": len(hits)}

    def _check_layer2_semantic_risks(self, text: str) -> Dict[str, Any]:
        """第二层：语义风险识别 - 检查暗示性违规表达"""
        hits = []
        has_high_risk = False

        for pattern, reason, risk_level, safe_alt in self.SEMANTIC_RISK_PATTERNS:
            match = re.search(pattern, text)
            if match:
                matched_text = match.group()
                hits.append(
                    {
                        "keyword": matched_text,
                        "risk_level": risk_level,
                        "reason": reason,
                        "suggestion": f"建议替换为: {safe_alt}",
                        "safe_alternative": safe_alt,
                        "position": {"start": match.start(), "end": match.end()},
                        "category": "语义风险",
                    }
                )
                if risk_level == "high":
                    has_high_risk = True

        return {"hits": hits, "has_high_risk": has_high_risk, "hit_count": len(hits)}

    def _check_layer3_platform_rules(self, text: str, platform: str) -> Dict[str, Any]:
        """第三层：平台规则映射"""
        hits = []
        has_high_risk = False

        try:
            platform_svc = PlatformRuleService(self.db)
            rules = platform_svc.get_rules_by_platform(platform)
            matched = check_text_against_rules(text, rules)

            for m in matched:
                risk_level = m.get("risk_level", "medium")
                hits.append(
                    {
                        "keyword": m.get("keyword", ""),
                        "risk_level": risk_level,
                        "reason": f"平台规则命中: {m.get('rule_category', '未分类')}",
                        "suggestion": m.get("suggestion", ""),
                        "safe_alternative": m.get("suggestion", ""),
                        "rule_category": m.get("rule_category", ""),
                        "category": f"{platform}平台规则",
                    }
                )
                if risk_level == "high":
                    has_high_risk = True
        except Exception as e:
            logger.warning(f"平台规则检测失败: {e}")

        return {"hits": hits, "has_high_risk": has_high_risk, "hit_count": len(hits), "platform": platform}

    def _generate_layer4_suggestions(self, risk_points: List[Dict], final_text: str) -> Dict[str, Any]:
        """第四层：生成改写建议"""
        suggestions = []

        for rp in risk_points:
            suggestions.append(
                {
                    "original": rp.get("keyword", ""),
                    "suggestion": rp.get("safe_alternative", rp.get("suggestion", "")),
                    "layer": rp.get("layer", ""),
                    "risk_level": rp.get("risk_level", "medium"),
                }
            )

        return {
            "suggestions": suggestions,
            "rewritten_text": final_text,
            "suggestion_count": len(suggestions),
        }

    def _auto_fix_four_layer(self, text: str, rewrite_suggestions: List[Dict]) -> str:
        """基于四层检测结果自动修正文本"""
        fixed = text

        # 按位置倒序替换，避免位置偏移
        sorted_suggestions = sorted(rewrite_suggestions, key=lambda x: len(x.get("original", "")), reverse=True)

        for sug in sorted_suggestions:
            original = sug.get("original", "")
            suggestion = sug.get("suggestion", "")
            if original and suggestion and original != suggestion:
                # 提取建议中的实际替换词
                if "建议替换为:" in suggestion or "建议替换为" in suggestion:
                    # 从建议中提取替换词
                    parts = suggestion.split(":")
                    if len(parts) > 1:
                        actual_replacement = parts[-1].strip()
                    else:
                        actual_replacement = suggestion
                else:
                    actual_replacement = suggestion
                fixed = fixed.replace(original, actual_replacement)

        return fixed

    def _get_keyword_category(self, keyword: str) -> str:
        """获取关键词所属分类"""
        if keyword in self.LOAN_PROMISE_KEYWORDS:
            return "承诺下款类"
        elif keyword in self.LOAN_PACKAGING_KEYWORDS:
            return "包装资料类"
        elif keyword in self.LOAN_CREDIT_KEYWORDS:
            return "征信类"
        elif keyword in self.LOAN_INTEREST_KEYWORDS:
            return "利率误导类"
        elif keyword in self.LOAN_INDUCE_KEYWORDS:
            return "诱导夸大类"
        return "其他"

    def _calculate_traffic_light_v2(self, total_score: float, layer_results: Dict) -> str:
        """
        计算交通灯等级（增强版）

        分级逻辑：
        - 红灯: 命中第一层硬规则高风险 或 命中第二层高风险语义
        - 黄灯: 命中第一层中等风险 或 第二层中等风险 或 第三层平台规则
        - 绿灯: 无风险或仅有低风险
        """
        # 第一层高风险 → 红灯
        if layer_results.get("layer1_hard_rules", {}).get("has_high_risk"):
            return "red"

        # 第二层高风险 → 红灯
        if layer_results.get("layer2_semantic_risks", {}).get("has_high_risk"):
            return "red"

        # 第三层高风险 → 黄灯（平台规则风险相对可控）
        if layer_results.get("layer3_platform_rules", {}).get("has_high_risk"):
            return "yellow"

        # 分数>=50 → 红灯
        if total_score >= 50:
            return "red"

        # 分数>=25 或 有任何命中 → 黄灯
        if total_score >= 25:
            return "yellow"

        # 检查是否有任何风险命中
        has_any_hit = (
            layer_results.get("layer1_hard_rules", {}).get("hit_count", 0) > 0
            or layer_results.get("layer2_semantic_risks", {}).get("hit_count", 0) > 0
            or layer_results.get("layer3_platform_rules", {}).get("hit_count", 0) > 0
        )

        if has_any_hit:
            return "yellow"

        # 无风险 → 绿灯
        return "green"

    async def check_async(
        self, text: str, enable_llm: bool = True, model: str = "volcano", platform: Optional[str] = None
    ) -> dict:
        """
        异步版合规检查（供异步上下文调用）- 四层检测体系
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
                risk_points.append(
                    {
                        "keyword": keyword,
                        "reason": f"包含{risk_level}级风险词: {keyword}",
                        "suggestion": suggestion,
                        "source": "rule",
                    }
                )
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
                risk_points.append(
                    {"keyword": pattern, "reason": reason, "suggestion": "请移除绝对化表达", "source": "rule"}
                )
                total_score += 20

        rewritten_text = self._auto_fix(text, risk_points, platform)

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
                    rewritten_text = self._auto_fix(text, risk_points, platform)
            except Exception as e:
                logger.warning(f"异步LLM语义检测失败: {e}")
                llm_analysis = f"[大模型检测跳过: {str(e)[:50]}]"

        # 第三层：平台专属规则检测
        if platform:
            try:
                platform_risk_points = self._check_platform_rules(text, platform)
                for rp in platform_risk_points:
                    rp["source"] = "platform_rule"
                    risk_points.append(rp)
                    if rp.get("risk_level") == "high":
                        total_score += 25
                    elif rp.get("risk_level") == "medium":
                        total_score += 12
                    else:
                        total_score += 5
            except Exception as e:
                logger.warning(f"异步平台规则检测失败: {e}")

        # 计算风险等级
        if total_score >= 50:
            risk_level = "high"
        elif total_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        suggestions = list(set(rp.get("suggestion", "") for rp in risk_points if rp.get("suggestion")))

        # 计算交通灯等级
        traffic_light = self._calculate_traffic_light(total_score, risk_points)

        return {
            "risk_level": risk_level,
            "risk_score": min(total_score, 100),
            "risk_points": risk_points,
            "suggestions": suggestions,
            "rewritten_text": rewritten_text,
            "is_compliant": risk_level == "low",
            "llm_analysis": llm_analysis,
            "auto_fixed_text": rewritten_text,
            "traffic_light": traffic_light,
        }
