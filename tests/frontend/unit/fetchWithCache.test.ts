import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Plotly before import as it might be required by frontend
vi.mock('plotly.js', () => ({}));

describe('fetchWithCache Optimization', () => {
    beforeEach(async () => {
        vi.resetModules();
        document.body.innerHTML = '';

        // Mock LocalStorage
        const localStorageMock = (function() {
          let store: any = {};
          return {
            getItem: function(key: string) { return store[key] || null; },
            setItem: function(key: string, value: string) { store[key] = value.toString(); },
            removeItem: function(key: string) { delete store[key]; },
            clear: function() { store = {}; }
          };
        })();
        Object.defineProperty(window, 'localStorage', { value: localStorageMock });

        // Import frontend to attach globals
        await import('../../../static/ts/foamflask_frontend.ts');
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it('should store ETag and Last-Modified on initial fetch', async () => {
        const { _fetchWithCache, _requestCache } = window as any;

        const mockResponse = {
            ok: true,
            status: 200,
            json: async () => ({ success: true }),
            headers: new Headers({
                'ETag': '"12345"',
                'Last-Modified': 'Wed, 21 Oct 2015 07:28:00 GMT'
            })
        };

        global.fetch = vi.fn().mockResolvedValue(mockResponse);

        await _fetchWithCache('/api/test');

        const cacheKey = '/api/test{}';
        const entry = _requestCache.get(cacheKey);

        expect(entry).toBeDefined();
        expect(entry.etag).toBe('"12345"');
        expect(entry.lastModified).toBe('Wed, 21 Oct 2015 07:28:00 GMT');
    });

    it('should send conditional headers on cache expiry', async () => {
        const { _fetchWithCache, _requestCache } = window as any;

        // Seed cache
        const cacheKey = '/api/test{}';
        _requestCache.set(cacheKey, {
            data: { success: true },
            timestamp: Date.now() - 2000, // Expired (> 1000ms)
            etag: '"12345"',
            lastModified: 'Wed, 21 Oct 2015 07:28:00 GMT'
        });

        const mockResponse = {
            ok: true,
            status: 200,
            json: async () => ({ success: true }),
            headers: new Headers()
        };

        const fetchMock = vi.fn().mockResolvedValue(mockResponse);
        global.fetch = fetchMock;

        await _fetchWithCache('/api/test');

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const headers = fetchMock.mock.calls[0][1].headers;
        expect(headers.get('If-None-Match')).toBe('"12345"');
        expect(headers.get('If-Modified-Since')).toBe('Wed, 21 Oct 2015 07:28:00 GMT');
    });

    it('should handle 304 Not Modified by returning cached data', async () => {
        const { _fetchWithCache, _requestCache } = window as any;

        const initialData = { success: true, version: 1 };
        const cacheKey = '/api/test{}';
        const initialTimestamp = Date.now() - 2000;

        _requestCache.set(cacheKey, {
            data: initialData,
            timestamp: initialTimestamp,
            etag: '"12345"'
        });

        const mockResponse = {
            ok: false, // 304 is not ok
            status: 304,
            json: async () => ({}),
            headers: new Headers()
        };

        global.fetch = vi.fn().mockResolvedValue(mockResponse);

        const result = await _fetchWithCache('/api/test');

        expect(result).toEqual(initialData);

        const entry = _requestCache.get(cacheKey);
        expect(entry.timestamp).toBeGreaterThan(initialTimestamp); // Timestamp updated
    });

    it('should update cache on 200 OK with new headers', async () => {
        const { _fetchWithCache, _requestCache } = window as any;

        const cacheKey = '/api/test{}';
        _requestCache.set(cacheKey, {
            data: { version: 1 },
            timestamp: Date.now() - 2000,
            etag: '"old"'
        });

        const mockResponse = {
            ok: true,
            status: 200,
            json: async () => ({ version: 2 }),
            headers: new Headers({ 'ETag': '"new"' })
        };

        global.fetch = vi.fn().mockResolvedValue(mockResponse);

        const result = await _fetchWithCache('/api/test');

        expect(result).toEqual({ version: 2 });

        const entry = _requestCache.get(cacheKey);
        expect(entry.data).toEqual({ version: 2 });
        expect(entry.etag).toBe('"new"');
    });
});
