import { FormEvent, useEffect, useState } from "react";
import { analyzeArkVision, listContent, rewriteContent, submitManualToInbox } from "../lib/api";
import { ContentAsset } from "../types";

export function AIPage() {
  const [contentList, setContentList] = useState<ContentAsset[]>([]);
  const [contentId, setContentId] = useState<number | "">("");
  const [targetPlatform, setTargetPlatform] = useState<"xiaohongshu" | "douyin" | "zhihu">("xiaohongshu");
  const [insightRefCount, setInsightRefCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState("");
  const [error, setError] = useState("");
  const [visionImageUrl, setVisionImageUrl] = useState(
    "https://ark-project.tos-cn-beijing.volces.com/doc_image/ark_demo_img_1.png"
  );
  const [visionText, setVisionText] = useState("你看见了什么？");
  const [visionModel, setVisionModel] = useState("doubao-seed-2-0-mini-260215");
  const [visionLoading, setVisionLoading] = useState(false);
  const [visionResult, setVisionResult] = useState("");
  const [visionError, setVisionError] = useState("");
  const [visionToRewriteLoading, setVisionToRewriteLoading] = useState(false);
  const [visionToRewriteMessage, setVisionToRewriteMessage] = useState("");

  useEffect(() => {
    async function fetchData() {
      const list = await listContent().catch(() => []);
      setContentList(list || []);
      if (list?.[0]?.id) setContentId(list[0].id);
    }
    fetchData();
  }, []);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!contentId) return;
    setLoading(true);
    setError("");
    setResult("");
    try {
      const data = await rewriteContent({
        content_id: Number(contentId),
        target_platform: targetPlatform,
      });
      setResult(data?.rewritten || "未返回内容");
      setInsightRefCount(data?.insight_reference_count ?? null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "改写失败，请检查模型服务是否可用");
    } finally {
      setLoading(false);
    }
  }

  async function onVisionSubmit(e: FormEvent) {
    e.preventDefault();
    if (!visionImageUrl.trim()) return;

    setVisionLoading(true);
    setVisionError("");
    setVisionResult("");
    try {
      const data = await analyzeArkVision({
        image_url: visionImageUrl.trim(),
        text: visionText.trim() || "你看见了什么？",
        model: visionModel.trim() || undefined
      });
      setVisionResult(data?.answer || "未返回内容");
    } catch (err: any) {
      setVisionError(err?.response?.data?.detail || "火山图片理解调用失败，请检查后端 ARK 配置");
    } finally {
      setVisionLoading(false);
    }
  }

  async function onVisionToRewrite() {
    if (!visionResult.trim()) {
      setVisionError("请先完成图片理解，再执行一键改写");
      return;
    }

    setVisionToRewriteLoading(true);
    setVisionToRewriteMessage("");
    setError("");
    setResult("");
    try {
      await submitManualToInbox({
        platform: "ark_vision",
        title: `图片理解_${new Date().toLocaleString()}`,
        content: visionResult.trim(),
        tags: ["火山图片理解"],
      });
      setVisionToRewriteMessage("已进入素材中心，可直接在素材列表中选择并改写");
    } catch (err: any) {
      setVisionError(err?.response?.data?.detail || err?.message || "提交失败");
    } finally {
      setVisionToRewriteLoading(false);
    }
  }

  return (
    <div className="page grid">
      <h2>AI 改写中心</h2>

      <section className="card">
        <h3>改写参数</h3>
        <form onSubmit={onSubmit} className="grid">
          <div className="form-row">
            <div>
              <label>选择素材</label>
              <select
                value={contentId}
                onChange={(e) => setContentId(Number(e.target.value))}
                required
              >
                {contentList.map((item) => (
                  <option key={item.id} value={item.id}>
                    #{item.id} {item.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label>目标平台</label>
              <select
                value={targetPlatform}
                onChange={(e) =>
                  setTargetPlatform(e.target.value as "xiaohongshu" | "douyin" | "zhihu")
                }
              >
                <option value="xiaohongshu">小红书</option>
                <option value="douyin">抖音</option>
                <option value="zhihu">知乎</option>
              </select>
            </div>

            <div>
              <label>参考模式</label>
              <input value="自动检索知识库" readOnly />
            </div>
          </div>

          <div>
            <button className="secondary" type="submit" disabled={loading || !contentId}>
              {loading ? "改写中..." : "开始改写"}
            </button>
          </div>

          {error && <div className="error">{error}</div>}
        </form>
      </section>

      <section className="card">
        <h3>改写结果</h3>
        {insightRefCount !== null && (
          <p style={{ fontSize: 13, color: insightRefCount > 0 ? "var(--brand-2)" : "#888", marginBottom: 8 }}>
            {insightRefCount > 0
              ? `✅ 已检索知识库，参考了 ${insightRefCount} 条素材文档`
              : `⚠️ 未检索到匹配参考，已按默认规则改写`}
          </p>
        )}
        <textarea value={result} readOnly placeholder="这里显示改写结果" />
      </section>

      <section className="card">
        <h3>火山引擎图片理解（Ark Responses）</h3>
        <form onSubmit={onVisionSubmit} className="grid">
          <div>
            <label>图片 URL</label>
            <input
              value={visionImageUrl}
              onChange={(e) => setVisionImageUrl(e.target.value)}
              placeholder="请输入可公网访问的图片地址"
              required
            />
          </div>

          <div className="form-row">
            <div>
              <label>问题</label>
              <input
                value={visionText}
                onChange={(e) => setVisionText(e.target.value)}
                placeholder="例如：你看见了什么？"
              />
            </div>
            <div>
              <label>模型</label>
              <input
                value={visionModel}
                onChange={(e) => setVisionModel(e.target.value)}
                placeholder="doubao-seed-2-0-mini-260215"
              />
            </div>
          </div>

          <div>
            <button className="secondary" type="submit" disabled={visionLoading || !visionImageUrl.trim()}>
              {visionLoading ? "识别中..." : "开始图片理解"}
            </button>
            <button
              className="ghost"
              type="button"
              disabled={visionToRewriteLoading || !visionResult.trim()}
              onClick={onVisionToRewrite}
              style={{ marginLeft: 10 }}
            >
              {visionToRewriteLoading ? "处理中..." : "一键入库并改写"}
            </button>
          </div>

          {visionError && <div className="error">{visionError}</div>}
          {visionToRewriteMessage && <div className="success">{visionToRewriteMessage}</div>}
          <textarea value={visionResult} readOnly placeholder="这里显示火山返回结果" />
        </form>
      </section>
    </div>
  );
}
