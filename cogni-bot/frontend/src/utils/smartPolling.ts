export interface PollingConfig {
  maxRetries?: number;
  baseDelay?: number;
  maxDelay?: number;
  timeout?: number;
  onSuccess?: () => void;
  onError?: (error: any, retryCount: number) => void;
  onTimeout?: () => void;
}

export interface PollingState {
  isPolling: boolean;
  retryCount: number;
  lastError: any;
  startTime: number;
}

export class SmartPoller {
  private config: Required<PollingConfig>;
  private state: PollingState;
  private timeoutId: NodeJS.Timeout | null = null;
  private retryTimeoutId: NodeJS.Timeout | null = null;

  constructor(config: PollingConfig = {}) {
    this.config = {
      maxRetries: config.maxRetries ?? 5,
      baseDelay: config.baseDelay ?? 1000,
      maxDelay: config.maxDelay ?? 30000,
      timeout: config.timeout ?? 60000,
      onSuccess: config.onSuccess ?? (() => {}),
      onError: config.onError ?? (() => {}),
      onTimeout: config.onTimeout ?? (() => {}),
    };

    this.state = {
      isPolling: false,
      retryCount: 0,
      lastError: null,
      startTime: 0,
    };
  }

  public start<T>(
    pollFunction: () => Promise<T>,
    interval: number = 1000
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      this.state = {
        isPolling: true,
        retryCount: 0,
        lastError: null,
        startTime: Date.now(),
      };

      // Set overall timeout
      this.timeoutId = setTimeout(() => {
        this.stop();
        this.config.onTimeout();
        reject(new Error('Polling timeout reached'));
      }, this.config.timeout);

      const poll = async () => {
        if (!this.state.isPolling) return;

        try {
          const result = await pollFunction();
          this.stop();
          this.config.onSuccess();
          resolve(result);
        } catch (error) {
          this.state.lastError = error;
          this.state.retryCount++;

          this.config.onError(error, this.state.retryCount);

          if (this.state.retryCount >= this.config.maxRetries) {
            this.stop();
            reject(new Error(`Max retries (${this.config.maxRetries}) exceeded`));
            return;
          }

          // Exponential backoff with jitter
          const delay = Math.min(
            this.config.baseDelay * Math.pow(2, this.state.retryCount - 1),
            this.config.maxDelay
          );
          const jitter = Math.random() * 0.1 * delay; // 10% jitter
          const finalDelay = delay + jitter;

          this.retryTimeoutId = setTimeout(poll, finalDelay);
        }
      };

      // Start polling
      poll();
    });
  }

  public stop(): void {
    this.state.isPolling = false;
    
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
    
    if (this.retryTimeoutId) {
      clearTimeout(this.retryTimeoutId);
      this.retryTimeoutId = null;
    }
  }

  public getState(): PollingState {
    return { ...this.state };
  }

  public isActive(): boolean {
    return this.state.isPolling;
  }
}

// Utility function for simple polling
export const createSmartPoller = (config?: PollingConfig) => {
  return new SmartPoller(config);
};

// Pre-configured pollers for common use cases
export const createMessagePoller = () => {
  return new SmartPoller({
    maxRetries: 10,
    baseDelay: 1000,
    maxDelay: 10000,
    timeout: 120000, // 2 minutes for message processing
  });
};

export const createStatusPoller = () => {
  return new SmartPoller({
    maxRetries: 20,
    baseDelay: 500,
    maxDelay: 5000,
    timeout: 60000, // 1 minute for status updates
  });
};

export const createBenchmarkPoller = () => {
  return new SmartPoller({
    maxRetries: 30,
    baseDelay: 500, // Faster initial polling (500ms instead of 2000ms)
    maxDelay: 15000,
    timeout: 300000, // 5 minutes for benchmarks
  });
}; 