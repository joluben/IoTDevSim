/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_BASE_URL: string
    readonly VITE_WS_URL: string
    readonly VITE_ENABLE_ANALYTICS: string
    readonly VITE_ENABLE_WEBSOCKET: string
    readonly VITE_ENABLE_BETA: string
    readonly VITE_ENABLE_FEDERATED_AUTH: string
    readonly VITE_FEDERATED_AUTH_PROVIDER: string
    readonly VITE_SENTRY_DSN: string
    readonly VITE_GOOGLE_ANALYTICS_ID: string
    readonly NODE_ENV: 'development' | 'production' | 'test'
    readonly DEV: boolean
    readonly PROD: boolean
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}