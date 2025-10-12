export interface ErrorInfo {
  type: 'network' | 'server' | 'timeout' | 'not_found' | 'validation' | 'unknown';
  message: string;
  userMessage: string;
  retryable: boolean;
  retryDelay?: number;
}

export class SmartErrorHandler {
  static handleApiError(error: any): ErrorInfo {
    // Network errors
    if (!navigator.onLine) {
      return {
        type: 'network',
        message: 'No internet connection',
        userMessage: 'You\'re offline. Please check your internet connection and try again.',
        retryable: true,
        retryDelay: 5000,
      };
    }

    // Axios/HTTP errors
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      switch (status) {
        case 400:
          return {
            type: 'validation',
            message: `Bad request: ${data?.error || 'Invalid data provided'}`,
            userMessage: 'Please check your input and try again.',
            retryable: false,
          };

        case 401:
          return {
            type: 'server',
            message: 'Unauthorized access',
            userMessage: 'Your session has expired. Please refresh the page.',
            retryable: false,
          };

        case 403:
          return {
            type: 'server',
            message: 'Forbidden access',
            userMessage: 'You don\'t have permission to perform this action.',
            retryable: false,
          };

        case 404:
          return {
            type: 'not_found',
            message: `Resource not found: ${error.config?.url || 'Unknown resource'}`,
            userMessage: 'The requested resource was not found. Please check the URL or try again.',
            retryable: false,
          };

        case 408:
        case 429:
          return {
            type: 'timeout',
            message: `Request timeout/rate limited: ${status}`,
            userMessage: 'The server is busy. Please wait a moment and try again.',
            retryable: true,
            retryDelay: 10000,
          };

        case 500:
        case 502:
        case 503:
        case 504:
          return {
            type: 'server',
            message: `Server error: ${status} - ${data?.error || 'Internal server error'}`,
            userMessage: 'The server is experiencing issues. Please try again in a few moments.',
            retryable: true,
            retryDelay: 5000,
          };

        default:
          return {
            type: 'server',
            message: `HTTP error ${status}: ${data?.error || 'Unknown server error'}`,
            userMessage: 'Something went wrong. Please try again.',
            retryable: status >= 500,
            retryDelay: status >= 500 ? 5000 : undefined,
          };
      }
    }

    // Network timeout errors
    if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
      return {
        type: 'timeout',
        message: 'Request timeout',
        userMessage: 'The request took too long. Please check your connection and try again.',
        retryable: true,
        retryDelay: 3000,
      };
    }

    // Network connection errors
    if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
      return {
        type: 'network',
        message: 'Network connection failed',
        userMessage: 'Unable to connect to the server. Please check your internet connection.',
        retryable: true,
        retryDelay: 3000,
      };
    }

    // Unknown errors
    return {
      type: 'unknown',
      message: error.message || 'Unknown error occurred',
      userMessage: 'An unexpected error occurred. Please try again.',
      retryable: false,
    };
  }

  static getRetryableErrors(): string[] {
    return ['network', 'timeout', 'server'];
  }

  static shouldRetry(error: ErrorInfo): boolean {
    return error.retryable;
  }

  static getRetryDelay(error: ErrorInfo): number {
    return error.retryDelay || 3000;
  }

  static formatErrorMessage(error: ErrorInfo): string {
    return error.userMessage;
  }

  static logError(error: any, context?: string): void {
    const errorInfo = this.handleApiError(error);
    console.error(`[${context || 'API Error'}]:`, {
      type: errorInfo.type,
      message: errorInfo.message,
      originalError: error,
      timestamp: new Date().toISOString(),
    });
  }
}

// Utility functions for common error scenarios
export const isNetworkError = (error: any): boolean => {
  return SmartErrorHandler.handleApiError(error).type === 'network';
};

export const isRetryableError = (error: any): boolean => {
  return SmartErrorHandler.handleApiError(error).retryable;
};

export const getErrorMessage = (error: any): string => {
  return SmartErrorHandler.handleApiError(error).userMessage;
};

export const getRetryDelay = (error: any): number => {
  return SmartErrorHandler.handleApiError(error).retryDelay || 3000;
}; 