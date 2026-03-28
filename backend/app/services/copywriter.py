from __future__ import annotations

from app.schemas import CopyGenerateRequest, CopyVariant, TagResult


def _hashtags(tags: list[str]) -> list[str]:
    result: list[str] = []
    for tag in tags:
        if not tag:
            continue
        t = tag.strip().replace("#", "")
        if t and t not in result:
            result.append(f"#{t}")
    return result[:6]


def _shorten(text: str, max_len: int = 160) -> str:
    text = text.strip().replace("\n", " ")
    return text[:max_len]


def generate_xiaohongshu_copies(req: CopyGenerateRequest, tags: TagResult) -> list[CopyVariant]:
    source = _shorten(req.content_text, 180)
    topic = req.topic_tag or tags.topic_tag
    crowd = req.crowd_tag or tags.crowd_tag

    variant1 = CopyVariant(
        variant_name="爆款版",
        title=f"{topic}真的别乱做，我是怎么一步步避坑的",
        content=(
            f'最近看到很多人在聊\u201c{req.title}\u201d，其实这种事我之前也踩过坑。\n\n'
            f"尤其是像【{crowd}】这种情况，很多人第一反应就是急着做决定，"
            f"但越着急越容易被带偏。\n\n"
            f"我后来才发现，先把自己的情况拆清楚，比到处乱问更重要。\n"
            f"比如这类问题里，最容易忽略的就是还款方式、实际成本、征信影响这几个点。\n\n"
            f"素材里提到的点是：{source}...\n\n"
            f"如果你也在碰到类似问题，真的建议先把自己的情况理一遍，"
            f"别一上来就被别人节奏带走。"
        ),
        hashtags=_hashtags([req.keyword or "", topic, crowd, req.platform]),
    )

    variant2 = CopyVariant(
        variant_name="引流版",
        title=f"{topic}这件事，我劝你先别急着做决定",
        content=(
            f'很多人表面看是在问\u201c{req.title}\u201d，'
            f"其实真正卡住的是：不知道自己适合哪种方案。\n\n"
            f"像【{crowd}】这类情况，处理顺序很关键，顺序错了，后面会更麻烦。\n\n"
            f"我把这类内容反复看了很多，发现大家最容易踩的就是：\n"
            f"1. 只看表面利率\n"
            f"2. 忽略隐藏成本\n"
            f"3. 没提前判断自己条件\n\n"
            f"原素材核心是：{source}...\n\n"
            f"有同样情况的，先别乱操作，先把自己的问题点搞清楚。"
        ),
        hashtags=_hashtags([req.keyword or "", topic, "避坑", req.platform]),
    )

    variant3 = CopyVariant(
        variant_name="安全版",
        title=f"关于{topic}，分享几个容易被忽略的点",
        content=(
            f'今天整理了一下关于\u201c{req.title}\u201d这类内容。\n\n'
            f"发现很多讨论其实都集中在几个问题上：\n"
            f"- 真实成本怎么看\n"
            f"- 还款节奏怎么判断\n"
            f"- 不同人群适不适合当前方案\n\n"
            f"像这篇素材里提到：{source}...\n\n"
            f"如果你最近也在关注【{topic}】相关内容，建议多对比、多判断，"
            f"先把信息看完整，再做决定。"
        ),
        hashtags=_hashtags([topic, crowd, "经验分享", req.platform]),
    )

    return [variant1, variant2, variant3]


def generate_douyin_copies(req: CopyGenerateRequest, tags: TagResult) -> list[CopyVariant]:
    source = _shorten(req.content_text, 120)
    topic = req.topic_tag or tags.topic_tag
    crowd = req.crowd_tag or tags.crowd_tag

    variant1 = CopyVariant(
        variant_name="口播版1",
        title=f"{topic}别瞎弄",
        content=(
            f"{req.title}，很多人一上来就做错了。"
            f"尤其是{crowd}，最怕的不是没办法，而是顺序搞错。"
            f"这条素材里最关键的一点其实是：{source}。"
            f"先把自己的情况看明白，再决定下一步。"
        ),
        hashtags=_hashtags([topic, crowd, req.platform]),
    )

    variant2 = CopyVariant(
        variant_name="口播版2",
        title=f"{topic}一定要先看这个",
        content=(
            f"很多人问{topic}怎么处理，"
            f"其实不是不会做，是不知道先做哪一步。"
            f"这篇内容里讲到：{source}。"
            f"真遇到这种情况，先别急。"
        ),
        hashtags=_hashtags([topic, "避坑", req.platform]),
    )

    variant3 = CopyVariant(
        variant_name="口播版3",
        title=f"{topic}经验分享",
        content=(
            f"今天聊一下{topic}。"
            f"很多人容易忽略真实成本和后续影响。"
            f"素材核心内容是：{source}。"
            f"这种事一定先判断，再行动。"
        ),
        hashtags=_hashtags([topic, "经验", req.platform]),
    )

    return [variant1, variant2, variant3]


def generate_copies(req: CopyGenerateRequest, tags: TagResult) -> list[CopyVariant]:
    if req.platform == "douyin":
        return generate_douyin_copies(req, tags)
    return generate_xiaohongshu_copies(req, tags)
