import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

describe('fetchWithCache', () => {
  let fetchWithCache: any;
  let requestCache: Map<string, any>;
  let fetchMock: any;

  beforeEach(async () => {
    document.body.innerHTML = '';

    // Mock global fetch
    fetchMock = vi.fn();
    global.fetch = fetchMock;
    window.fetch = fetchMock;

    // Import module
    await import('../../../static/ts/foamflask_frontend.ts');

    // Access exposed internals
    fetchWithCache = (window as any)._fetchWithCache;
    requestCache = (window as any)._requestCache;

    // Clear cache
    if (requestCache) requestCache.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should fetch data when cache is empty', async () => {
    const mockData = { success: true };
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => mockData,
    });

    const data = await fetchWithCache('/api/test');
    expect(data).toEqual(mockData);
    expect(fetchMock).toHaveBeenCalledWith('/api/test', expect.anything());
    expect(requestCache.size).toBe(1);
  });

  it('should return cached data if within duration', async () => {
    const mockData = { success: true };
    const url = '/api/test';
    const cacheKey = `${url}{}`; // Assuming default options stringify to "{}"

    requestCache.set(cacheKey, {
      data: mockData,
      timestamp: Date.now()
    });

    const data = await fetchWithCache(url);
    expect(data).toEqual(mockData);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('should perform conditional fetch when cache is expired', async () => {
    const mockData = { success: true };
    const url = '/api/test_conditional';
    const cacheKey = `${url}{}`;
    const etag = '"12345"';
    const lastModified = 'Wed, 21 Oct 2015 07:28:00 GMT';

    // Seed cache with expired entry + headers
    requestCache.set(cacheKey, {
      data: mockData,
      timestamp: Date.now() - 2000, // Expired (> 1000ms)
      etag: etag,
      lastModified: lastModified
    });

    // Mock 304 response
    // Note: When using manual conditional headers, fetch returns 304 if server sends 304.
    // However, if we don't mock ok=true, fetchWithCache might throw depending on implementation.
    // MDN says 304 has ok=false (redirect/client error range? No, 3xx).
    // fetch response.ok is true for 200-299. 304 is NOT ok.
    // We need to handle this in implementation.
    fetchMock.mockResolvedValue({
      ok: false, // 304 is not "ok" by default fetch standards
      status: 304,
      headers: new Headers(),
      json: async () => { throw new Error("Should not parse JSON on 304"); }
    });

    const data = await fetchWithCache(url);

    // Should verify headers were sent
    // We check the second argument (options)
    const callArgs = fetchMock.mock.calls[0];
    const options = callArgs[1];

    // Headers can be Headers object or plain object
    // Our implementation currently spreads options...

    // We expect headers to be present
    expect(options.headers).toBeDefined();

    // If it's a Headers object
    if (options.headers instanceof Headers) {
        expect(options.headers.get('If-None-Match')).toBe(etag);
        expect(options.headers.get('If-Modified-Since')).toBe(lastModified);
    } else {
        // Plain object or array
        // We will implement using plain object for simplicity in test check or adapt
        expect(options.headers['If-None-Match']).toBe(etag);
        expect(options.headers['If-Modified-Since']).toBe(lastModified);
    }

    // Should return cached data
    expect(data).toEqual(mockData);

    // Should update timestamp
    const entry = requestCache.get(cacheKey);
    expect(Date.now() - entry.timestamp).toBeLessThan(100);
  });

  it('should update cache on 200 response with new headers', async () => {
    const oldData = { val: 1 };
    const newData = { val: 2 };
    const url = '/api/test_update';
    const cacheKey = `${url}{}`;

    requestCache.set(cacheKey, {
      data: oldData,
      timestamp: Date.now() - 2000,
      etag: '"old"',
    });

    const newEtag = '"new"';
    fetchMock.mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'ETag': newEtag }),
      json: async () => newData,
    });

    const data = await fetchWithCache(url);
    expect(data).toEqual(newData);

    const entry = requestCache.get(cacheKey);
    expect(entry.data).toEqual(newData);
    expect(entry.etag).toBe(newEtag);
  });
});
