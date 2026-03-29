"""规则清洗服务 - 纯代码清洗，不使用AI模型"""
import re
import hashlib
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.models import MvpInboxItem


class CleaningService:
    def __init__(self, db: Session):
        self.db = db
    
    def clean_item(self, inbox_item_id: int) -> dict:
        """单条清洗，返回结果字典"""
        item = self.db.query(MvpInboxItem).filter(MvpInboxItem.id == inbox_item_id).first()
        if not item:
            return {"success": False, "error": "Item not found"}
        
        try:
            # 1. HTML 标签清理
            cleaned_content = self._remove_html(item.content or "")
            # 2. emoji 和噪声字符处理（保留常用emoji，去除乱码和特殊控制字符）
            cleaned_content = self._normalize_emoji(cleaned_content)
            # 3. 空白和换行标准化（多个空行→单个，多个空格→单个）
            cleaned_content = self._normalize_whitespace(cleaned_content)
            # 4. 长度截断（正文限5000字）
            cleaned_content = self._truncate(cleaned_content, 5000)
            # 5. 平台字段标准化
            if item.platform:
                item.platform = self._standardize_platform(item.platform)
            # 6. 标题清洗
            if item.title:
                item.title = self._remove_html(item.title)
                item.title = self._normalize_emoji(item.title)
                item.title = self._truncate(item.title, 200)
            # 7. 生成 content_preview（前200字）
            item.content_preview = self._generate_preview(cleaned_content, 200)
            # 8. 去重检测
            is_dup = self._check_duplicate(item.title or "", item.source_id or "", item.id)
            # 9. 更新字段
            item.content = cleaned_content
            item.clean_status = 'cleaned'
            item.cleaned_at = datetime.utcnow()
            if is_dup:
                item.duplicate_status = 'duplicate'
            
            self.db.commit()
            return {"success": True, "item_id": item.id, "is_duplicate": is_dup}
        except Exception as e:
            item.clean_status = 'failed'
            self.db.commit()
            return {"success": False, "error": str(e)}
    
    def batch_clean(self, item_ids: List[int]) -> dict:
        """批量清洗"""
        results = {"total": len(item_ids), "success": 0, "failed": 0, "details": []}
        for item_id in item_ids:
            result = self.clean_item(item_id)
            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
            results["details"].append(result)
        return results
    
    def _remove_html(self, text: str) -> str:
        """移除HTML标签"""
        # 移除script和style标签及内容
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # 将br和p标签转换为换行
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        # 移除所有其他HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 解码HTML实体
        import html
        text = html.unescape(text)
        return text
    
    def _normalize_emoji(self, text: str) -> str:
        """处理emoji和噪声字符：保留常用emoji，去除乱码和控制字符"""
        # 移除零宽字符和控制字符（保留换行和制表）
        text = re.sub(r'[\u200b\u200c\u200d\ufeff\u2028\u2029]', '', text)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """标准化空白字符"""
        # 多个空格→单个空格
        text = re.sub(r'[^\S\n]+', ' ', text)
        # 多个空行→最多两个换行
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _truncate(self, text: str, max_len: int) -> str:
        """长度截断"""
        if len(text) > max_len:
            return text[:max_len] + '...'
        return text
    
    def _standardize_platform(self, platform: str) -> str:
        """平台字段标准化"""
        platform_map = {
            '小红书': 'xiaohongshu', 'xhs': 'xiaohongshu', 'redbook': 'xiaohongshu',
            '抖音': 'douyin', 'tiktok': 'douyin',
            '知乎': 'zhihu',
            '微博': 'weibo', 'sina': 'weibo',
            '微信': 'wechat', 'weixin': 'wechat',
            '公众号': 'wechat_mp', 'mp': 'wechat_mp',
            '快手': 'kuaishou',
            'b站': 'bilibili', 'B站': 'bilibili',
        }
        normalized = platform.lower().strip()
        return platform_map.get(normalized, platform_map.get(platform, normalized))
    
    def _generate_preview(self, text: str, max_len: int = 200) -> str:
        """生成内容预览"""
        preview = text.replace('\n', ' ').strip()
        if len(preview) > max_len:
            return preview[:max_len] + '...'
        return preview
    
    def _check_duplicate(self, title: str, source_id: str, current_id: int) -> bool:
        """基于 title + source_id 的hash去重"""
        if not title and not source_id:
            return False
        dup_hash = hashlib.md5(f"{title}:{source_id}".encode()).hexdigest()
        existing = self.db.query(MvpInboxItem).filter(
            MvpInboxItem.id != current_id,
            MvpInboxItem.title == title,
            MvpInboxItem.source_id == source_id
        ).first()
        return existing is not None
