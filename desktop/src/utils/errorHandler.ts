/**
 * 统一错误消息处理
 * 将各种错误类型转换为用户友好的中文消息
 */

export function getErrorMessage(err: any): string {
    // HTTP 状态码映射
    if (err?.response?.status) {
        switch (err.response.status) {
            case 400:
                return "请求参数有误，请检查后重试";
            case 401:
                return "登录已过期，请重新登录";
            case 403:
                return "权限不足，无法执行此操作";
            case 404:
                return "请求的资源不存在";
            case 422:
                return "请求参数有误，请检查后重试";
            case 429:
                return "请求过于频繁，请稍后重试";
            case 500:
                return "服务器内部错误，请稍后重试";
            case 502:
                return "服务暂时不可用，请稍后重试";
            case 503:
                return "服务维护中，请稍后重试";
            case 504:
                return "请求超时，请稍后重试";
        }
    }
    
    // 网络错误
    if (err?.code === "ERR_NETWORK" || err?.message?.includes("Network Error")) {
        return "网络连接失败，请检查网络设置";
    }
    
    // 超时
    if (err?.code === "ECONNABORTED" || err?.message?.includes("timeout")) {
        return "请求超时，请稍后重试";
    }
    
    // 后端返回的错误消息（脱敏处理，限制长度避免暴露敏感信息）
    if (err?.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === "string" && detail.length < 100) {
            return detail;
        }
    }
    
    // 标准错误消息
    if (err?.message && typeof err.message === "string") {
        // 避免显示技术性错误信息
        const msg = err.message;
        if (msg.includes("fetch") || msg.includes("Network")) {
            return "网络连接失败，请检查网络设置";
        }
        // 如果消息较短且看起来像用户友好的消息，直接返回
        if (msg.length < 100 && !msg.includes("Error:") && !msg.includes("at ")) {
            return msg;
        }
    }
    
    return "操作失败，请稍后重试";
}

/**
 * 判断是否为网络错误
 */
export function isNetworkError(err: any): boolean {
    return (
        err?.code === "ERR_NETWORK" ||
        err?.message?.includes("Network Error") ||
        err?.message?.includes("fetch")
    );
}

/**
 * 判断是否为认证错误
 */
export function isAuthError(err: any): boolean {
    return err?.response?.status === 401;
}

/**
 * 判断是否为权限错误
 */
export function isPermissionError(err: any): boolean {
    return err?.response?.status === 403;
}

/**
 * 判断是否为资源不存在错误
 */
export function isNotFoundError(err: any): boolean {
    return err?.response?.status === 404;
}

/**
 * 判断是否为服务器错误
 */
export function isServerError(err: any): boolean {
    const status = err?.response?.status;
    return status >= 500 && status < 600;
}
