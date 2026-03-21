import { FormEvent, useState } from "react";
import { checkCompliance } from "../lib/api";

type RiskPoint = {
  type: string;
  text: string;
  reason: string;
  suggestion: string;
};

export function CompliancePage() {
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    risk_level: string;
    risk_score: number;
    risk_points: RiskPoint[];
    suggestions: string[];
    is_compliant: boolean;
  } | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await checkCompliance(content);
      setResult(data);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page grid">
      <h2>合规审核中心</h2>

      <section className="card">
        <h3>检测文本</h3>
        <form onSubmit={onSubmit} className="grid">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="输入文案，例如：这个方案包过秒批..."
            required
          />
          <button className="secondary" type="submit" disabled={loading}>
            {loading ? "检测中..." : "开始检测"}
          </button>
        </form>
      </section>

      {result && (
        <section className="card">
          <h3>检测结果</h3>
          <p>
            风险等级: <strong>{result.risk_level}</strong> | 评分: <strong>{result.risk_score}</strong>
          </p>
          <p className={result.is_compliant ? "success" : "error"}>
            {result.is_compliant ? "当前内容基础合规" : "检测到风险内容，请按建议修改"}
          </p>

          <h3 style={{ marginTop: 14 }}>风险点</h3>
          <ul>
            {result.risk_points.map((point, idx) => (
              <li key={idx}>
                [{point.type}] {point.text} - {point.reason} - 建议: {point.suggestion}
              </li>
            ))}
          </ul>

          <h3 style={{ marginTop: 14 }}>通用建议</h3>
          <ul>
            {result.suggestions.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
