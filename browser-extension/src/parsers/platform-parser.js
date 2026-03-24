function detectPlatformByHost(hostname) {
  var host = (hostname || "").toLowerCase();
  if (host.indexOf("xiaohongshu") >= 0 || host.indexOf("xhslink") >= 0) return "xiaohongshu";
  if (host.indexOf("douyin") >= 0 || host.indexOf("iesdouyin") >= 0) return "douyin";
  if (host.indexOf("zhihu") >= 0) return "zhihu";
  if (host.indexOf("weixin") >= 0 || host.indexOf("wechat") >= 0) return "wechat";
  if (host.indexOf("xianyu") >= 0 || host.indexOf("goofish") >= 0) return "xianyu";
  return "other";
}

if (typeof module !== "undefined") {
  module.exports = { detectPlatformByHost };
}
