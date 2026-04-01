import { useEffect, useState, useRef } from "react";
import { conversationApi } from "../../api/conversationApi";
import type { ConversationItem, MessageItem, SuggestResponse } from "../../types";
import { getErrorMessage } from "../../utils/errorHandler";

const platformLabels: Record<string, string> = {
  xiaohongshu: "小红书",
  douyin: "抖音",
  zhihu: "知乎",
};

const platformIcons: Record<string, string> = {
  xiaohongshu: "📕",
  douyin: "🎵",
  zhihu: "💙",
};

const conversationTypeLabels: Record<string, string> = {
  comment: "评论",
  private_message: "私信",
};

const statusLabels: Record<string, string> = {
  active: "进行中",
  closed: "已关闭",
  takeover: "人工接管",
};

const statusColors: Record<string, string> = {
  active: "#22c55e",
  closed: "#6b7280",
  takeover: "#f59e0b",
};

export function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [selectedConv, setSelectedConv] = useState<ConversationItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [msgLoading, setMsgLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 筛选条件
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [platformFilter, setPlatformFilter] = useState<string>("all");

  // AI 建议相关
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [suggestResult, setSuggestResult] = useState<SuggestResponse | null>(null);
  const [userMessageInput, setUserMessageInput] = useState("");

  // 发送回复相关
  const [replyContent, setReplyContent] = useState("");
  const [replyLoading, setReplyLoading] = useState(false);
  const [replyMessage, setReplyMessage] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 加载会话列表
  async function loadConversations() {
    setLoading(true);
    setError(null);
    try {
      const data = await conversationApi.list();
      setConversations(data || []);
    } catch (err: any) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  // 加载会话消息
  async function loadMessages(convId: number) {
    setMsgLoading(true);
    try {
      const data = await conversationApi.getMessages(convId);
      setMessages(data || []);
    } catch (err: any) {
      console.error("加载消息失败:", err);
      setMessages([]);
    } finally {
      setMsgLoading(false);
    }
  }

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (selectedConv) {
      loadMessages(selectedConv.id);
      // 清空 AI 建议
      setSuggestResult(null);
      setUserMessageInput("");
    }
  }, [selectedConv]);

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 筛选会话
  const filteredConversations = conversations.filter((conv) => {
    if (statusFilter !== "all" && conv.status !== statusFilter) return false;
    if (platformFilter !== "all" && conv.platform !== platformFilter) return false;
    return true;
  });

  // 获取 AI 建议
  async function handleGetSuggestion() {
    if (!userMessageInput.trim()) {
      setReplyMessage("请输入用户消息内容");
      return;
    }
    setSuggestLoading(true);
    setReplyMessage("");
    try {
      const result = await conversationApi.suggest({
        message: userMessageInput.trim(),
        platform: selectedConv?.platform,
      });
      setSuggestResult(result);
    } catch (err: any) {
      setReplyMessage(getErrorMessage(err));
    } finally {
      setSuggestLoading(false);
    }
  }

  // 选用建议回复
  function handleSelectSuggestion(suggestion: string) {
    setReplyContent(suggestion);
  }

  // 发送回复
  async function handleSendReply() {
    if (!selectedConv || !replyContent.trim()) return;
    setReplyLoading(true);
    setReplyMessage("");
    try {
      const newMsg = await conversationApi.reply(selectedConv.id, {
        content: replyContent.trim(),
        is_sent: true,
      });
      setMessages((prev) => [...prev, newMsg]);
      setReplyContent("");
      setReplyMessage("回复已发送");
      setTimeout(() => setReplyMessage(""), 2000);
    } catch (err: any) {
      setReplyMessage(getErrorMessage(err));
    } finally {
      setReplyLoading(false);
    }
  }

  // 人工接管会话
  async function handleTakeover() {
    if (!selectedConv) return;
    if (selectedConv.status === "takeover") return; // 已接管则跳过
    setReplyMessage("");
    try {
      await conversationApi.takeover(selectedConv.id);
      setReplyMessage(`会话 #${selectedConv.id} 已成功接管`);
      // 刷新会话列表以更新状态
      loadConversations();
      // 更新当前选中会话的状态
      setSelectedConv((prev) => prev ? { ...prev, status: "takeover" } : null);
    } catch (err: any) {
      setReplyMessage(`接管失败: ${getErrorMessage(err)}`);
    }
  }

  // 格式化时间
  function formatTime(dateStr: string | null) {
    if (!dateStr) return "-";
    const d = new Date(dateStr);
    return d.toLocaleString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="page" style={{ height: "calc(100vh - 60px)", display: "flex", flexDirection: "column" }}>
      <h2 style={{ margin: 0, padding: "16px 0" }}>会话管理</h2>

      <div style={{ flex: 1, display: "flex", gap: 16, overflow: "hidden" }}>
        {/* 左侧面板 - 会话列表 */}
        <div
          style={{
            width: "30%",
            minWidth: 280,
            background: "#fff",
            borderRadius: 8,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* 筛选条件 */}
          <div style={{ padding: 12, borderBottom: "1px solid #e5e7eb", display: "flex", gap: 8, flexWrap: "wrap" }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 4, border: "1px solid #d1d5db" }}
            >
              <option value="all">全部状态</option>
              <option value="active">进行中</option>
              <option value="closed">已关闭</option>
              <option value="takeover">人工接管</option>
            </select>
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value)}
              style={{ padding: "6px 10px", borderRadius: 4, border: "1px solid #d1d5db" }}
            >
              <option value="all">全部平台</option>
              <option value="xiaohongshu">小红书</option>
              <option value="douyin">抖音</option>
              <option value="zhihu">知乎</option>
            </select>
          </div>

          {/* 会话列表 */}
          <div style={{ flex: 1, overflow: "auto" }}>
            {loading ? (
              <div style={{ padding: 20, textAlign: "center", color: "#666" }}>加载中...</div>
            ) : error ? (
              <div style={{ padding: 20, textAlign: "center", color: "#ef4444" }}>{error}</div>
            ) : filteredConversations.length === 0 ? (
              <div style={{ padding: 20, textAlign: "center", color: "#999" }}>暂无会话</div>
            ) : (
              filteredConversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => setSelectedConv(conv)}
                  style={{
                    padding: "12px 16px",
                    borderBottom: "1px solid #f3f4f6",
                    cursor: "pointer",
                    background: selectedConv?.id === conv.id ? "#f0f9ff" : "transparent",
                    transition: "background 0.15s",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 18 }}>{platformIcons[conv.platform] || "📱"}</span>
                    <span style={{ fontWeight: 500 }}>
                      {conversationTypeLabels[conv.conversation_type] || conv.conversation_type}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        padding: "2px 6px",
                        borderRadius: 4,
                        background: statusColors[conv.status] || "#6b7280",
                        color: "#fff",
                      }}
                    >
                      {statusLabels[conv.status] || conv.status}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "#888" }}>
                    {platformLabels[conv.platform] || conv.platform} · ID: {conv.id}
                    {conv.ai_handled && " · AI处理"}
                  </div>
                  <div style={{ fontSize: 11, color: "#aaa", marginTop: 4 }}>
                    更新于 {formatTime(conv.updated_at)}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 右侧面板 - 聊天详情 */}
        <div
          style={{
            flex: 1,
            background: "#fff",
            borderRadius: 8,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {selectedConv ? (
            <>
              {/* 会话头部信息 */}
              <div
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid #e5e7eb",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span style={{ fontSize: 24 }}>{platformIcons[selectedConv.platform] || "📱"}</span>
                  <div>
                    <div style={{ fontWeight: 600 }}>
                      {conversationTypeLabels[selectedConv.conversation_type] || selectedConv.conversation_type}
                    </div>
                    <div style={{ fontSize: 12, color: "#666" }}>
                      {platformLabels[selectedConv.platform] || selectedConv.platform} · 
                      {selectedConv.ai_handled ? "AI处理中" : "待处理"}
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    className="ghost"
                    onClick={handleTakeover}
                    disabled={selectedConv.status === "takeover"}
                    style={{
                      padding: "6px 12px",
                      background: selectedConv.status === "takeover" ? "#fef3c7" : "transparent",
                      border: selectedConv.status === "takeover" ? "1px solid #f59e0b" : undefined,
                    }}
                  >
                    {selectedConv.status === "takeover" ? "已接管" : "人工接管"}
                  </button>
                </div>
              </div>

              {/* 消息列表 */}
              <div
                style={{
                  flex: 1,
                  overflow: "auto",
                  padding: 16,
                  display: "flex",
                  flexDirection: "column",
                  gap: 12,
                  background: "#f9fafb",
                }}
              >
                {msgLoading ? (
                  <div style={{ textAlign: "center", color: "#666", padding: 40 }}>加载消息中...</div>
                ) : messages.length === 0 ? (
                  <div style={{ textAlign: "center", color: "#999", padding: 40 }}>暂无消息记录</div>
                ) : (
                  messages.map((msg) => {
                    const isUser = msg.role === "user";
                    return (
                      <div
                        key={msg.id}
                        style={{
                          display: "flex",
                          justifyContent: isUser ? "flex-start" : "flex-end",
                        }}
                      >
                        <div
                          style={{
                            maxWidth: "70%",
                            padding: "10px 14px",
                            borderRadius: 12,
                            background: isUser ? "#fff" : "#dbeafe",
                            boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                          }}
                        >
                          <div style={{ fontSize: 12, color: "#666", marginBottom: 4, display: "flex", gap: 8 }}>
                            <span style={{ fontWeight: 500 }}>{isUser ? "用户" : "助手"}</span>
                            <span>{formatTime(msg.created_at)}</span>
                            {msg.intent && (
                              <span
                                style={{
                                  background: "#e0e7ff",
                                  color: "#4338ca",
                                  padding: "1px 6px",
                                  borderRadius: 4,
                                  fontSize: 11,
                                }}
                              >
                                {msg.intent}
                              </span>
                            )}
                          </div>
                          <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{msg.content}</div>
                          {msg.is_sent && (
                            <div style={{ fontSize: 10, color: "#22c55e", marginTop: 4 }}>已发送</div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* AI 建议区域 */}
              <div
                style={{
                  padding: 12,
                  borderTop: "1px solid #e5e7eb",
                  background: "#fefce8",
                }}
              >
                <div style={{ fontWeight: 500, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                  <span>💡</span> AI 回复建议
                </div>
                <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
                  <input
                    type="text"
                    placeholder="输入用户最新消息内容..."
                    value={userMessageInput}
                    onChange={(e) => setUserMessageInput(e.target.value)}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                    }}
                  />
                  <button
                    className="primary"
                    onClick={handleGetSuggestion}
                    disabled={suggestLoading}
                    style={{ padding: "8px 16px" }}
                  >
                    {suggestLoading ? "分析中..." : "获取建议"}
                  </button>
                </div>

                {suggestResult && (
                  <div>
                    {/* 意图识别结果 */}
                    <div
                      style={{
                        padding: 8,
                        background: "#fff",
                        borderRadius: 6,
                        marginBottom: 8,
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                      }}
                    >
                      <span style={{ fontWeight: 500 }}>意图: {suggestResult.intent}</span>
                      <span style={{ color: "#666" }}>置信度: {(suggestResult.confidence * 100).toFixed(1)}%</span>
                    </div>

                    {/* 人工接管警告 */}
                    {suggestResult.should_takeover && (
                      <div
                        style={{
                          padding: 10,
                          background: "#fef2f2",
                          border: "1px solid #fca5a5",
                          borderRadius: 6,
                          marginBottom: 8,
                          color: "#b91c1c",
                        }}
                      >
                        ⚠️ 建议人工接管: {suggestResult.takeover_reason || "复杂场景需要人工介入"}
                      </div>
                    )}

                    {/* 回复建议 */}
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      {suggestResult.suggestions.map((suggestion, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleSelectSuggestion(suggestion)}
                          style={{
                            padding: 10,
                            background: "#fff",
                            borderRadius: 6,
                            cursor: "pointer",
                            border: "1px solid #e5e7eb",
                            transition: "border-color 0.15s",
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#3b82f6")}
                          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#e5e7eb")}
                        >
                          <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>建议 {idx + 1}</div>
                          <div style={{ whiteSpace: "pre-wrap" }}>{suggestion}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 发送回复区域 */}
              <div style={{ padding: 12, borderTop: "1px solid #e5e7eb" }}>
                <div style={{ display: "flex", gap: 8 }}>
                  <textarea
                    placeholder="输入回复内容..."
                    value={replyContent}
                    onChange={(e) => setReplyContent(e.target.value)}
                    rows={2}
                    style={{
                      flex: 1,
                      padding: "8px 12px",
                      borderRadius: 6,
                      border: "1px solid #d1d5db",
                      resize: "none",
                    }}
                  />
                  <button
                    className="primary"
                    onClick={handleSendReply}
                    disabled={replyLoading || !replyContent.trim()}
                    style={{ padding: "8px 20px", alignSelf: "flex-end" }}
                  >
                    {replyLoading ? "发送中..." : "发送回复"}
                  </button>
                </div>
                {replyMessage && (
                  <div style={{ marginTop: 8, fontSize: 12, color: "#22c55e" }}>{replyMessage}</div>
                )}
              </div>
            </>
          ) : (
            <div
              style={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#999",
              }}
            >
              选择左侧会话查看详情
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ConversationsPage;
