export interface ApiClientConfig {
  baseUrl: string;
}

export class ApiClient {
  private readonly baseUrl: string;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl;
  }

  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return (await res.json()) as T;
  }
}
