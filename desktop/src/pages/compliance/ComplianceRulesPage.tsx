import { useState, useEffect, useCallback } from "react";
import {
  listComplianceRules,
  createComplianceRule,
  updateComplianceRule,
  deleteComplianceRule,
  testComplianceRule,
} from "../../lib/api";

// 规则类型配置
const RULE_TYPE_OPTIONS = [
  { value: "keyword", label: "关键词", color: "#87CEEB" },
  { value: "regex", label: "正则表达式", color: "#DDA0DD" },
  { value: "semantic", label: "语义规则", color: "#98D8C8" },
];

// 风险等级配置
const RISK_LEVEL_OPTIONS = [
  { value: "low", label: "低风险", color: "#4caf50", bgColor: "#1b5e20" },
  { value: "medium", label: "中风险", color: "#ff9800", bgColor: "#e65100" },
  { value: "high", label: "高风险", color: "#f44336", bgColor: "#b71c1c" },
];

interface ComplianceRule {
  id: number;
  rule_type: string;
  keyword: string;
  pattern?: string;
  risk_level: string;
  description?: string;
  suggestion?: string;
  is_active?: boolean;
  created_at?: string;
}

interface TestResult {
  risk_level: string;
  risk_score: number;
  risk_points: Array<{
    keyword: string;
    reason: string;
    suggestion: string;
  }>;
  suggestions: string[];
  is_compliant: boolean;
}

export default function ComplianceRulesPage() {
  // 规则列表状态
  const [rules, setRules] = useState<ComplianceRule[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 筛选状态
  const [filterRuleType, setFilterRuleType] = useState("");
  const [filterRiskLevel, setFilterRiskLevel] = useState("");

  // 弹窗状态
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<ComplianceRule | null>(null);
  const [formData, setFormData] = useState({
    rule_type: "keyword",
    keyword: "",
    risk_level: "medium",
    pattern: "",
    description: "",
    suggestion: "",
  });

  // 测试工具状态
  const [testText, setTestText] = useState("");
  const [testLoading, setTestLoading] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  // 加载规则列表
  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = { page, size: pageSize };
      if (filterRuleType) params.rule_type = filterRuleType;
      if (filterRiskLevel) params.risk_level = filterRiskLevel;

      const res = await listComplianceRules(params);
      setRules(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("加载规则列表失败:", err);
      setRules([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [page, filterRuleType, filterRiskLevel]);

  // 初始加载
  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  // 打开新建弹窗
  const handleCreate = () => {
    setEditingRule(null);
    setFormData({
      rule_type: "keyword",
      keyword: "",
      risk_level: "medium",
      pattern: "",
      description: "",
      suggestion: "",
    });
    setModalOpen(true);
  };

  // 打开编辑弹窗
  const handleEdit = (rule: ComplianceRule) => {
    setEditingRule(rule);
    setFormData({
      rule_type: rule.rule_type,
      keyword: rule.keyword,
      risk_level: rule.risk_level,
      pattern: rule.pattern || "",
      description: rule.description || "",
      suggestion: rule.suggestion || "",
    });
    setModalOpen(true);
  };

  // 保存规则
  const handleSave = async () => {
    if (!formData.keyword.trim()) {
      alert("请输入关键词/规则内容");
      return;
    }

    try {
      if (editingRule) {
        await updateComplianceRule(editingRule.id, formData);
      } else {
        await createComplianceRule(formData);
      }
      setModalOpen(false);
      fetchRules();
    } catch (err: any) {
      alert(err.response?.data?.detail || "保存失败");
    }
  };

  // 删除规则
  const handleDelete = async (ruleId: number) => {
    if (!confirm("确定要删除这条规则吗？")) return;

    try {
      await deleteComplianceRule(ruleId);
      fetchRules();
    } catch (err: any) {
      alert(err.response?.data?.detail || "删除失败");
    }
  };

  // 测试规则
  const handleTest = async () => {
    if (!testText.trim()) {
      alert("请输入要检测的文本");
      return;
    }

    setTestLoading(true);
    try {
      const result = await testComplianceRule(testText);
      setTestResult(result);
    } catch (err) {
      console.error("测试失败:", err);
      alert("测试失败");
    } finally {
      setTestLoading(false);
    }
  };

  // 获取规则类型显示
  const getRuleTypeDisplay = (type: string) => {
    const option = RULE_TYPE_OPTIONS.find((o) => o.value === type);
    return option || { label: type, color: "#9B8B7A" };
  };

  // 获取风险等级显示
  const getRiskLevelDisplay = (level: string) => {
    const option = RISK_LEVEL_OPTIONS.find((o) => o.value === level);
    return option || { label: level, color: "#9B8B7A", bgColor: "#3A322C" };
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div style={styles.page}>
      {/* 页面标题 */}
      <div style={styles.header}>
        <div>
          <h2 style={styles.title}>合规规则管理</h2>
          <p style={styles.subtitle}>管理内容合规检测规则，支持关键词、正则、语义三种类型</p>
        </div>
        <button onClick={handleCreate} style={styles.createButton}>
          + 新建规则
        </button>
      </div>

      {/* 筛选栏 */}
      <div style={styles.filterBar}>
        <div style={styles.filterGroup}>
          <select
            value={filterRuleType}
            onChange={(e) => {
              setFilterRuleType(e.target.value);
              setPage(1);
            }}
            style={styles.select}
          >
            <option value="">全部类型</option>
            {RULE_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <select
            value={filterRiskLevel}
            onChange={(e) => {
              setFilterRiskLevel(e.target.value);
              setPage(1);
            }}
            style={styles.select}
          >
            <option value="">全部风险等级</option>
            {RISK_LEVEL_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div style={styles.totalBadge}>共 {total} 条规则</div>
      </div>

      {/* 规则列表 */}
      <div style={styles.tableContainer}>
        {loading ? (
          <div style={styles.loadingState}>加载中...</div>
        ) : rules.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyIcon}>🛡️</div>
            <div style={styles.emptyTitle}>暂无规则</div>
            <div style={styles.emptyDesc}>点击"新建规则"添加第一条合规规则</div>
          </div>
        ) : (
          <>
            <table style={styles.table}>
              <thead>
                <tr style={styles.tableHeader}>
                  <th style={styles.thType}>类型</th>
                  <th style={styles.thKeyword}>关键词/规则</th>
                  <th style={styles.thRisk}>风险等级</th>
                  <th style={styles.thDesc}>描述</th>
                  <th style={styles.thAction}>操作</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => {
                  const typeDisplay = getRuleTypeDisplay(rule.rule_type);
                  const riskDisplay = getRiskLevelDisplay(rule.risk_level);
                  return (
                    <tr key={rule.id} style={styles.tableRow}>
                      <td style={styles.tdType}>
                        <span
                          style={{
                            ...styles.typeTag,
                            background: typeDisplay.color + "30",
                            color: typeDisplay.color,
                          }}
                        >
                          {typeDisplay.label}
                        </span>
                      </td>
                      <td style={styles.tdKeyword}>
                        <div style={styles.keywordText}>{rule.keyword}</div>
                        {rule.pattern && (
                          <div style={styles.patternText}>正则: {rule.pattern}</div>
                        )}
                      </td>
                      <td style={styles.tdRisk}>
                        <span
                          style={{
                            ...styles.riskTag,
                            background: riskDisplay.bgColor + "40",
                            color: riskDisplay.color,
                          }}
                        >
                          {riskDisplay.label}
                        </span>
                      </td>
                      <td style={styles.tdDesc}>
                        {rule.description || "-"}
                        {rule.suggestion && (
                          <div style={styles.suggestionText}>建议: {rule.suggestion}</div>
                        )}
                      </td>
                      <td style={styles.tdAction}>
                        <button
                          onClick={() => handleEdit(rule)}
                          style={styles.editButton}
                        >
                          编辑
                        </button>
                        <button
                          onClick={() => handleDelete(rule.id)}
                          style={styles.deleteButton}
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* 分页 */}
            {totalPages > 1 && (
              <div style={styles.pagination}>
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  style={{
                    ...styles.pageButton,
                    opacity: page === 1 ? 0.5 : 1,
                    cursor: page === 1 ? "not-allowed" : "pointer",
                  }}
                >
                  上一页
                </button>
                <span style={styles.pageInfo}>
                  第 {page} / {totalPages} 页 (共 {total} 条)
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  style={{
                    ...styles.pageButton,
                    opacity: page === totalPages ? 0.5 : 1,
                    cursor: page === totalPages ? "not-allowed" : "pointer",
                  }}
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* 规则测试工具 */}
      <div style={styles.testSection}>
        <h3 style={styles.testTitle}>🧪 规则测试工具</h3>
        <p style={styles.testSubtitle}>输入文案内容，检测是否触发合规规则</p>
        <textarea
          value={testText}
          onChange={(e) => setTestText(e.target.value)}
          placeholder="请输入要检测的文案内容..."
          style={styles.testInput}
          rows={4}
        />
        <button
          onClick={handleTest}
          disabled={testLoading}
          style={styles.testButton}
        >
          {testLoading ? "检测中..." : "检测合规性"}
        </button>

        {/* 测试结果 */}
        {testResult && (
          <div style={styles.testResult}>
            <div style={styles.resultHeader}>
              <span style={styles.resultLabel}>检测结果:</span>
              <span
                style={{
                  ...styles.resultLevel,
                  color: getRiskLevelDisplay(testResult.risk_level).color,
                }}
              >
                {getRiskLevelDisplay(testResult.risk_level).label}
              </span>
              <span style={styles.resultScore}>
                风险分: {testResult.risk_score}/100
              </span>
            </div>

            {testResult.risk_points.length > 0 ? (
              <div style={styles.riskPoints}>
                <div style={styles.riskPointsTitle}>检测到的风险点:</div>
                {testResult.risk_points.map((point, idx) => (
                  <div key={idx} style={styles.riskPoint}>
                    <div style={styles.riskPointKeyword}>⚠️ {point.keyword}</div>
                    <div style={styles.riskPointReason}>{point.reason}</div>
                    {point.suggestion && (
                      <div style={styles.riskPointSuggestion}>
                        💡 建议: {point.suggestion}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={styles.compliantMessage}>✅ 未检测到风险，内容合规</div>
            )}

            {testResult.suggestions.length > 0 && (
              <div style={styles.suggestions}>
                <div style={styles.suggestionsTitle}>优化建议:</div>
                <ul style={styles.suggestionsList}>
                  {testResult.suggestions.map((s, idx) => (
                    <li key={idx} style={styles.suggestionItem}>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 新建/编辑弹窗 */}
      {modalOpen && (
        <div style={styles.modalOverlay}>
          <div style={styles.modal}>
            <h3 style={styles.modalTitle}>
              {editingRule ? "编辑规则" : "新建规则"}
            </h3>

            <div style={styles.formGroup}>
              <label style={styles.label}>规则类型</label>
              <select
                value={formData.rule_type}
                onChange={(e) =>
                  setFormData({ ...formData, rule_type: e.target.value })
                }
                style={styles.formSelect}
              >
                {RULE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>
                {formData.rule_type === "regex" ? "正则表达式" : "关键词"}
              </label>
              <input
                type="text"
                value={formData.keyword}
                onChange={(e) =>
                  setFormData({ ...formData, keyword: e.target.value })
                }
                placeholder={
                  formData.rule_type === "regex"
                    ? "输入正则表达式，如: \\d+%通过"
                    : "输入关键词，如: 必过"
                }
                style={styles.formInput}
              />
            </div>

            {formData.rule_type === "regex" && (
              <div style={styles.formGroup}>
                <label style={styles.label}>匹配模式 (可选)</label>
                <input
                  type="text"
                  value={formData.pattern}
                  onChange={(e) =>
                    setFormData({ ...formData, pattern: e.target.value })
                  }
                  placeholder="额外的匹配模式"
                  style={styles.formInput}
                />
              </div>
            )}

            <div style={styles.formGroup}>
              <label style={styles.label}>风险等级</label>
              <select
                value={formData.risk_level}
                onChange={(e) =>
                  setFormData({ ...formData, risk_level: e.target.value })
                }
                style={styles.formSelect}
              >
                {RISK_LEVEL_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>描述 (可选)</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="规则的简要描述"
                style={styles.formInput}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>修改建议 (可选)</label>
              <input
                type="text"
                value={formData.suggestion}
                onChange={(e) =>
                  setFormData({ ...formData, suggestion: e.target.value })
                }
                placeholder="触发规则时给出的修改建议"
                style={styles.formInput}
              />
            </div>

            <div style={styles.modalActions}>
              <button onClick={() => setModalOpen(false)} style={styles.cancelButton}>
                取消
              </button>
              <button onClick={handleSave} style={styles.saveButton}>
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    padding: "24px",
    minHeight: "calc(100vh - 48px)",
    background: "#2D2520",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "24px",
  },
  title: {
    fontSize: "24px",
    fontWeight: 700,
    color: "#E8DDD3",
    margin: "0 0 8px 0",
  },
  subtitle: {
    fontSize: "14px",
    color: "#9B8B7A",
    margin: 0,
  },
  createButton: {
    padding: "10px 20px",
    borderRadius: "8px",
    border: "none",
    background: "#A0522D",
    color: "#FFF",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  filterBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: "16px",
    marginBottom: "24px",
    padding: "16px",
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
  },
  filterGroup: {
    display: "flex",
    gap: "12px",
    flexWrap: "wrap",
  },
  select: {
    padding: "8px 12px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#2D2520",
    color: "#E8DDD3",
    fontSize: "14px",
    minWidth: "140px",
  },
  totalBadge: {
    background: "#3A322C",
    color: "#D4C5B2",
    padding: "8px 16px",
    borderRadius: "20px",
    fontSize: "14px",
    fontWeight: 500,
  },
  tableContainer: {
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
    overflow: "hidden",
    marginBottom: "24px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "14px",
  },
  tableHeader: {
    background: "#3A322C",
  },
  tableRow: {
    borderBottom: "1px solid #4A3F35",
    transition: "background 0.15s ease",
  },
  thType: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
    width: "100px",
  },
  thKeyword: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
    width: "30%",
  },
  thRisk: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
    width: "100px",
  },
  thDesc: {
    padding: "12px 16px",
    textAlign: "left",
    color: "#BFA98E",
    fontWeight: 600,
  },
  thAction: {
    padding: "12px 16px",
    textAlign: "center",
    color: "#BFA98E",
    fontWeight: 600,
    width: "150px",
  },
  tdType: {
    padding: "12px 16px",
  },
  typeTag: {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "4px",
    fontSize: "12px",
    fontWeight: 500,
  },
  tdKeyword: {
    padding: "12px 16px",
  },
  keywordText: {
    color: "#E8DDD3",
    fontWeight: 500,
    fontSize: "14px",
  },
  patternText: {
    color: "#9B8B7A",
    fontSize: "12px",
    marginTop: "4px",
  },
  tdRisk: {
    padding: "12px 16px",
  },
  riskTag: {
    display: "inline-block",
    padding: "4px 10px",
    borderRadius: "4px",
    fontSize: "12px",
    fontWeight: 500,
  },
  tdDesc: {
    padding: "12px 16px",
    color: "#9B8B7A",
    fontSize: "13px",
  },
  suggestionText: {
    color: "#87CEEB",
    fontSize: "12px",
    marginTop: "4px",
  },
  tdAction: {
    padding: "12px 16px",
    textAlign: "center",
  },
  editButton: {
    padding: "6px 12px",
    borderRadius: "4px",
    border: "none",
    background: "#3A322C",
    color: "#D4C5B2",
    fontSize: "12px",
    cursor: "pointer",
    marginRight: "8px",
  },
  deleteButton: {
    padding: "6px 12px",
    borderRadius: "4px",
    border: "none",
    background: "#5c2a2a",
    color: "#ff9999",
    fontSize: "12px",
    cursor: "pointer",
  },
  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "16px",
    padding: "16px",
    borderTop: "1px solid #4A3F35",
  },
  pageButton: {
    padding: "8px 16px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#3A322C",
    color: "#E8DDD3",
    cursor: "pointer",
    fontSize: "14px",
  },
  pageInfo: {
    color: "#9B8B7A",
    fontSize: "14px",
  },
  loadingState: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "60px",
    color: "#9B8B7A",
    fontSize: "14px",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "60px",
    textAlign: "center",
  },
  emptyIcon: {
    fontSize: "64px",
    marginBottom: "16px",
  },
  emptyTitle: {
    fontSize: "18px",
    fontWeight: 600,
    color: "#E8DDD3",
    marginBottom: "8px",
  },
  emptyDesc: {
    fontSize: "14px",
    color: "#9B8B7A",
  },
  testSection: {
    background: "#1E1A16",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
    padding: "24px",
  },
  testTitle: {
    fontSize: "18px",
    fontWeight: 600,
    color: "#E8DDD3",
    margin: "0 0 8px 0",
  },
  testSubtitle: {
    fontSize: "14px",
    color: "#9B8B7A",
    margin: "0 0 16px 0",
  },
  testInput: {
    width: "100%",
    padding: "12px",
    borderRadius: "8px",
    border: "1px solid #4A3F35",
    background: "#2D2520",
    color: "#E8DDD3",
    fontSize: "14px",
    resize: "vertical",
    marginBottom: "12px",
    boxSizing: "border-box",
  },
  testButton: {
    padding: "10px 24px",
    borderRadius: "8px",
    border: "none",
    background: "#8B7355",
    color: "#FFF",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
  testResult: {
    marginTop: "20px",
    padding: "16px",
    background: "#2D2520",
    borderRadius: "8px",
    border: "1px solid #4A3F35",
  },
  resultHeader: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
    marginBottom: "16px",
    paddingBottom: "12px",
    borderBottom: "1px solid #4A3F35",
  },
  resultLabel: {
    color: "#9B8B7A",
    fontSize: "14px",
  },
  resultLevel: {
    fontSize: "16px",
    fontWeight: 700,
  },
  resultScore: {
    color: "#9B8B7A",
    fontSize: "14px",
    marginLeft: "auto",
  },
  riskPoints: {
    marginBottom: "16px",
  },
  riskPointsTitle: {
    color: "#BFA98E",
    fontSize: "14px",
    fontWeight: 600,
    marginBottom: "12px",
  },
  riskPoint: {
    background: "#3A322C",
    padding: "12px",
    borderRadius: "6px",
    marginBottom: "8px",
  },
  riskPointKeyword: {
    color: "#E8DDD3",
    fontWeight: 600,
    fontSize: "14px",
    marginBottom: "4px",
  },
  riskPointReason: {
    color: "#9B8B7A",
    fontSize: "13px",
    marginBottom: "4px",
  },
  riskPointSuggestion: {
    color: "#87CEEB",
    fontSize: "12px",
  },
  compliantMessage: {
    color: "#4caf50",
    fontSize: "14px",
    padding: "12px",
    background: "#1b5e2040",
    borderRadius: "6px",
  },
  suggestions: {
    marginTop: "16px",
  },
  suggestionsTitle: {
    color: "#BFA98E",
    fontSize: "14px",
    fontWeight: 600,
    marginBottom: "8px",
  },
  suggestionsList: {
    margin: 0,
    paddingLeft: "20px",
    color: "#D4C5B2",
  },
  suggestionItem: {
    marginBottom: "4px",
    fontSize: "13px",
  },
  modalOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: "rgba(0, 0, 0, 0.7)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  modal: {
    background: "#2D2520",
    borderRadius: "12px",
    border: "1px solid #4A3F35",
    padding: "24px",
    width: "90%",
    maxWidth: "500px",
    maxHeight: "90vh",
    overflow: "auto",
  },
  modalTitle: {
    fontSize: "18px",
    fontWeight: 600,
    color: "#E8DDD3",
    margin: "0 0 20px 0",
  },
  formGroup: {
    marginBottom: "16px",
  },
  label: {
    display: "block",
    color: "#BFA98E",
    fontSize: "14px",
    marginBottom: "6px",
  },
  formSelect: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#1E1A16",
    color: "#E8DDD3",
    fontSize: "14px",
    boxSizing: "border-box",
  },
  formInput: {
    width: "100%",
    padding: "10px 12px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#1E1A16",
    color: "#E8DDD3",
    fontSize: "14px",
    boxSizing: "border-box",
  },
  modalActions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "12px",
    marginTop: "24px",
  },
  cancelButton: {
    padding: "10px 20px",
    borderRadius: "6px",
    border: "1px solid #4A3F35",
    background: "#3A322C",
    color: "#D4C5B2",
    fontSize: "14px",
    cursor: "pointer",
  },
  saveButton: {
    padding: "10px 20px",
    borderRadius: "6px",
    border: "none",
    background: "#A0522D",
    color: "#FFF",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
  },
};
