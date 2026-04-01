from app.collector.parsers.douyin import DouyinCollector
from app.collector.parsers.xiaohongshu import XiaohongshuCollector
from app.collector.parsers.zhihu import ZhihuCollector

# from app.collector.parsers.xianyu import XianyuCollector


class CollectorFactory:
    @staticmethod
    def get_collector(platform: str):
        if platform == "xiaohongshu":
            return XiaohongshuCollector()
        elif platform == "douyin":
            return DouyinCollector()
        elif platform == "zhihu":
            return ZhihuCollector()
        # elif platform == "xianyu":
        #     return XianyuCollector()
        raise ValueError(f"不支持的平台: {platform}")
