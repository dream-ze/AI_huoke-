const PluginApiClient = {
  defaults: {
    requestTimeoutMs: 12000,
    maxRetries: 2
  },

  normalizeBaseUrl(url) {
    return (url || "http://127.0.0.1:8000").trim().replace(/\/$/, "");
  },

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
};
