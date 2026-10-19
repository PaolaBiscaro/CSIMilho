import { afterEach, expect, it, vi } from 'vitest'

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules() })

it.each([[false, '/api/health'], [true, 'http://localhost:9000/api/health']])(
  'uses the build origin and keeps overrides confined to development (DEV=%s)', async (dev, url) => {
    vi.resetModules()
    vi.stubEnv('DEV', dev)
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:9000')
    const fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok', gemini_configured: false, model: 'test', version: '1.0.0' }) })
    vi.stubGlobal('fetch', fetch)
    const { getHealth } = await import('../src/api.js')
    await getHealth()
    expect(fetch).toHaveBeenCalledExactlyOnceWith(url, { signal: undefined })
  },
)
