"""MVP 爆款仿写服务"""
import json
import os
import asyncio
import logging
from sqlalchemy.orm import Session
from app.models.models import MvpMaterialItem

logger = logging.getLogger(__name__)


class MvpRewriteService:
    def __init__(self, db: Session):
        self.db = db
        self._prompts_dir = os.path.join(os.path.dirname(__file__), "..", "ai", "prompts")

    def rewrite_hot(self, material_id: int):
        """爆款仿写：分析结构+生成3个仿写版本"""
        try:
            material = self.db.query(MvpMaterialItem).filter(MvpMaterialItem.id == material_id).first()
            if not material:
                raise ValueError("素材不存在")
            
            text = f"{material.title}\n\n{material.content}"
            
            # 尝试调用LLM
            result = self._call_llm_rewrite(text)
            
            # 更新使用次数
            material.use_count += 1
            self.db.commit()
            
            return result
        except ValueError:
            raise
        except Exception as e:
            logger.exception("爆款仿写失败")
            self.db.rollback()
            raise ValueError(f"仿写失败: {str(e)}")

    def _call_llm_rewrite(self, text: str) -> dict:
        """调用LLM进行仿写，失败时使用Mock"""
        try:
            prompt_file = os.path.join(self._prompts_dir, "mvp_hot_rewrite_v1.txt")
            with open(prompt_file, "r", encoding="utf-8") as f:
                template = f.read()
            prompt = template.replace("{original_text}", text[:1500])
            
            from app.services.ai_service import AIService
            ai_svc = AIService(self.db)
            # 使用asyncio运行异步方法
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                raw = loop.run_until_complete(
                    ai_svc.call_llm(
                        prompt=prompt,
                        system_prompt="你是爆款内容仿写专家。请分析爆款结构并生成仿写版本，返回JSON格式。",
                        use_cloud=True
                    )
                )
                return self._parse_rewrite(raw)
            finally:
                loop.close()
        except Exception as e:
            logger.warning(f"LLM仿写调用失败，使用Mock: {e}")
            # 提取标题和内容
            lines = text.split("\n")
            title = lines[0] if lines else "示例标题"
            content = "\n".join(lines[1:]) if len(lines) > 1 else "示例内容"
            return self._mock_rewrite(title, content)

    def _parse_rewrite(self, raw_text):
        """解析仿写结果"""
        try:
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(raw_text[start:end])
        except Exception:
            pass
        return self._mock_rewrite("示例标题", "示例内容")

    def _mock_rewrite(self, title, content):
        """Mock仿写结果"""
        preview = content[:100] if content else ""
        return {
            "structure_analysis": {
                "hook": title[:30] if title else "引人注目的开头",
                "pain_point": "目标人群的核心痛点描述",
                "scenario": "具体的使用场景",
                "solution": "提供的解决方案",
                "cta": "引导行动的结尾"
            },
            "versions": [
                {
                    "title": f"[仿写v1] {title}",
                    "text": f"你有没有遇到过这样的情况？{preview}\n\n其实解决方法很简单，关键是找对方向。今天就来分享几个实用技巧...",
                    "version": "v1",
                    "style_label": "仿写版本1"
                },
                {
                    "title": f"[仿写v2] {title}",
                    "text": f"很多人都在问这个问题！{preview}\n\n作为过来人，我总结了3个核心要点，每一个都很重要...",
                    "version": "v2",
                    "style_label": "仿写版本2"
                },
                {
                    "title": f"[仿写v3] {title}",
                    "text": f"今天不藏着了，直接说！{preview}\n\n别再走弯路了，看完这篇你就全明白了。建议收藏慢慢看...",
                    "version": "v3",
                    "style_label": "仿写版本3"
                },
            ]
        }

    def analyze_structure(self, text: str) -> dict:
        """分析内容结构（不生成仿写）"""
        try:
            # 简单的结构分析
            lines = text.split("\n")
            title = lines[0].strip() if lines else ""
            content = "\n".join(lines[1:]).strip() if len(lines) > 1 else text
            
            # 识别钩子类型
            hook_type = "问题开头"
            if any(c.isdigit() for c in title[:10]):
                hook_type = "数字开头"
            elif "？" in title or "吗" in title:
                hook_type = "疑问开头"
            elif any(kw in title for kw in ["真实", "亲身", "我的"]):
                hook_type = "故事开头"
            
            # 识别CTA类型
            cta_type = "无明显引导"
            if any(kw in content[-100:] for kw in ["评论", "留言", "讨论"]):
                cta_type = "评论引导"
            elif any(kw in content[-100:] for kw in ["私信", "联系"]):
                cta_type = "私信引导"
            elif any(kw in content[-100:] for kw in ["关注", "粉丝"]):
                cta_type = "关注引导"
            elif any(kw in content[-100:] for kw in ["收藏", "保存"]):
                cta_type = "收藏引导"
            
            return {
                "title": title,
                "hook_type": hook_type,
                "cta_type": cta_type,
                "paragraph_count": len([p for p in content.split("\n") if p.strip()]),
                "char_count": len(content),
                "has_emoji": any(ord(c) > 127 and ord(c) < 65536 for c in content)
            }
        except Exception as e:
            return {"error": str(e)}

    def batch_rewrite(self, material_ids: list) -> dict:
        """批量仿写"""
        results = {"success": [], "failed": []}
        for mid in material_ids:
            try:
                result = self.rewrite_hot(mid)
                results["success"].append({"material_id": mid, "result": result})
            except Exception as e:
                results["failed"].append({"material_id": mid, "error": str(e)})
        return results
