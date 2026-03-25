from app.collectors.xiaohongshu_collector import XiaohongshuCollector
# from app.collectors.douyin_collector import DouyinCollector
# from app.collectors.zhihu_collector import ZhihuCollector
# from app.collectors.xianyu_collector import XianyuCollector


class CollectorFactory:
    @staticmethod
    def get_collector(platform: str):
        if platform == "xiaohongshu":
            return XiaohongshuCollector()
        # elif platform == "douyin":
        #     return DouyinCollector()
        # elif platform == "zhihu":
        #     return ZhihuCollector()
        # elif platform == "xianyu":
        #     return XianyuCollector()
        raise ValueError(f"不支持的平台: {platform}")
