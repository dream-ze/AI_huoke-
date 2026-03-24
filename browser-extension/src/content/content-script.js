(function () {
  function textOrEmpty(value) {
    return (value || "").replace(/\s+/g, " ").trim();
  }

  function queryMeta(name) {
    var byName = document.querySelector('meta[name="' + name + '"]');
    if (byName && byName.content) return textOrEmpty(byName.content);

    var byProp = document.querySelector('meta[property="' + name + '"]');
    if (byProp && byProp.content) return textOrEmpty(byProp.content);

    return "";
  }

  function detectPlatform(hostname) {
    var host = (hostname || "").toLowerCase();
    if (host.indexOf("xiaohongshu") >= 0 || host.indexOf("xhslink") >= 0) {
      return "xiaohongshu";
    }
    if (host.indexOf("douyin") >= 0 || host.indexOf("iesdouyin") >= 0) {
      return "douyin";
    }
    if (host.indexOf("zhihu") >= 0) {
      return "zhihu";
    }
    if (host.indexOf("weixin") >= 0 || host.indexOf("wechat") >= 0) {
      return "wechat";
    }
    if (host.indexOf("xianyu") >= 0 || host.indexOf("goofish") >= 0) {
      return "xianyu";
    }
    return "other";
  }

  function extractTextBySelectors(selectors) {
    for (var i = 0; i < selectors.length; i += 1) {
      var node = document.querySelector(selectors[i]);
      if (node && node.textContent) {
        var text = textOrEmpty(node.textContent);
        if (text.length >= 12) return text;
      }
    }
    return "";
  }

  function collectParagraphText() {
    var nodes = document.querySelectorAll("article p, main p, .content p, p");
    var chunks = [];
    var maxLines = 80;

    for (var i = 0; i < nodes.length && chunks.length < maxLines; i += 1) {
      var line = textOrEmpty(nodes[i].textContent || "");
      if (line.length >= 8) {
        chunks.push(line);
      }
    }

    return textOrEmpty(chunks.join("\n"));
  }

  function collectComments() {
    var nodes = document.querySelectorAll("[class*='comment'], .comment, [data-e2e*='comment']");
    var comments = [];
    var seen = {};

    for (var i = 0; i < nodes.length && comments.length < 20; i += 1) {
      var content = textOrEmpty(nodes[i].textContent || "");
      if (!content || content.length < 4 || seen[content]) continue;
      seen[content] = true;
      comments.push({
        content: content,
        created_at: new Date().toISOString()
      });
    }

    return comments;
  }

  function normalizeUrl(inputUrl) {
    try {
      var parsed = new URL(inputUrl);
      parsed.hash = "";
      return parsed.toString();
    } catch (error) {
      return inputUrl || "";
    }
  }

  function collectPayload() {
    var url = normalizeUrl(window.location.href);
    var title =
      queryMeta("og:title") ||
      queryMeta("twitter:title") ||
      textOrEmpty(document.title);

    var content =
      queryMeta("description") ||
      queryMeta("og:description") ||
      extractTextBySelectors(["article", "main", ".post-content", ".rich-text"]) ||
      collectParagraphText();

    var author =
      queryMeta("author") ||
      queryMeta("article:author") ||
      extractTextBySelectors([".author", "[class*='author']", "[data-author]"]);

    var published = queryMeta("article:published_time") || "";
    var keywords = queryMeta("keywords");
    var tags = keywords
      ? keywords
          .split(/[,，]/)
          .map(function (item) {
            return item.trim();
          })
          .filter(Boolean)
          .slice(0, 10)
      : [];

    return {
      platform: detectPlatform(window.location.hostname),
      title: title || "未命名内容",
      content: content || "页面正文提取为空，请手动补充",
      author: author || null,
      publish_time: published || null,
      tags: tags,
      comments_json: collectComments(),
      url: url,
      heat_score: 0.0
    };
  }

  chrome.runtime.onMessage.addListener(function (message, _sender, sendResponse) {
    if (!message || message.type !== "PLUGIN_COLLECT_FROM_PAGE") {
      return false;
    }

    try {
      var payload = collectPayload();
      sendResponse({ ok: true, payload: payload });
    } catch (error) {
      sendResponse({
        ok: false,
        error: "采集失败：" + (error && error.message ? error.message : "未知错误")
      });
    }

    return true;
  });
})();
