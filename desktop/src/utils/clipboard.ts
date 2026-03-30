/**
 * 复制文本到剪贴板
 * 兼容 HTTP 和 HTTPS 环境
 * 
 * 在 HTTPS 环境下使用现代 Clipboard API
 * 在 HTTP 环境下降级使用 document.execCommand('copy')
 */
export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    // 优先使用现代 Clipboard API（仅在安全上下文可用）
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    // HTTP 环境降级方案
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    textArea.style.top = '-9999px';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    
    textArea.focus();
    textArea.select();
    
    const success = document.execCommand('copy');
    document.body.removeChild(textArea);
    
    return success;
  } catch (err) {
    console.error('复制失败:', err);
    return false;
  }
};
