/**
 * chunked_upload_injector.js
 *
 * Intercepts the XMLHttpRequest that the compiled frontend uses to upload
 * media files.  When the destination URL contains "/upload-direct", it
 * replaces the single large PUT with a multi-part chunked POST flow:
 *
 *   1. Slice the file into CHUNK_SIZE pieces (5 MB default)
 *   2. POST each slice to  /api/v1/episodes/upload-chunk  (tiny request, no 413)
 *   3. POST to             /api/v1/episodes/upload-assemble  (JSON only, no file)
 *   4. Resolve the original XHR with a synthetic 200 OK response
 *
 * This bypasses ALL web-server body-size limits (Apache LimitRequestBody,
 * Nginx client_max_body_size, cPanel, Cloudflare, etc.) because no single
 * HTTP request ever exceeds CHUNK_SIZE bytes.
 */
(function () {
  'use strict';

  const CHUNK_SIZE   = 5 * 1024 * 1024;   // 5 MB per chunk
  const API_BASE     = '/api/v1/episodes';
  const CHUNK_URL    = API_BASE + '/upload-chunk';
  const ASSEMBLE_URL = API_BASE + '/upload-assemble';

  // ── helpers ──────────────────────────────────────────────────────────────

  function getAuthToken() {
    try {
      const stored =
        localStorage.getItem('podule_auth_token') ||
        localStorage.getItem('token') ||
        localStorage.getItem('auth_token');
      if (stored) return stored.replace(/^"|"$/g, '');
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && k.toLowerCase().includes('token')) {
          const v = localStorage.getItem(k);
          if (v && v.length > 20) return v.replace(/^"|"$/g, '');
        }
      }
    } catch (_) {}
    return '';
  }

  function randomId() {
    return Math.random().toString(36).slice(2, 10) +
           Math.random().toString(36).slice(2, 10);
  }

  /**
   * Upload a single ArrayBuffer chunk via fetch (no size limit on fetch).
   */
  async function postChunk(uploadId, chunkIndex, totalChunks, blob, token) {
    const form = new FormData();
    form.append('upload_id',    uploadId);
    form.append('chunk_index',  String(chunkIndex));
    form.append('total_chunks', String(totalChunks));
    form.append('file',         blob, 'chunk');

    const headers = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const res = await fetch(CHUNK_URL, { method: 'POST', headers, body: form });
    if (!res.ok) {
      const text = await res.text().catch(() => res.status);
      throw new Error('Chunk ' + chunkIndex + ' failed (' + res.status + '): ' + text);
    }
    return res.json();
  }

  /**
   * Tell the backend to assemble the chunks and return the final download URL.
   */
  async function assembleChunks(uploadId, totalChunks, filename, contentType, token) {
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const res = await fetch(ASSEMBLE_URL, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        upload_id:    uploadId,
        total_chunks: totalChunks,
        filename,
        content_type: contentType,
      }),
    });
    if (!res.ok) {
      const text = await res.text().catch(() => res.status);
      throw new Error('Assemble failed (' + res.status + '): ' + text);
    }
    return res.json();
  }

  // ── XHR intercept ────────────────────────────────────────────────────────

  const OriginalXHR = window.XMLHttpRequest;

  function PatchedXHR() {
    const real     = new OriginalXHR();
    let   _method  = 'GET';
    let   _url     = '';
    let   _headers = {};
    let   _onprogress = null;
    let   _onload     = null;
    let   _onerror    = null;

    // Proxy all property reads/writes to the real XHR
    const proxy = new Proxy(this, {
      get(_, prop) {
        if (prop === 'upload') {
          // Return a fake upload object so onprogress can be attached
          if (!proxy.__fakeUpload) {
            proxy.__fakeUpload = {
              set onprogress(fn) { _onprogress = fn; },
              get onprogress()   { return _onprogress; },
            };
          }
          return proxy.__fakeUpload;
        }
        if (prop === 'onload')  return _onload;
        if (prop === 'onerror') return _onerror;
        const v = real[prop];
        return typeof v === 'function' ? v.bind(real) : v;
      },
      set(_, prop, value) {
        if (prop === 'onload')  { _onload  = value; return true; }
        if (prop === 'onerror') { _onerror = value; return true; }
        try { real[prop] = value; } catch (_) {}
        return true;
      },
    });

    proxy.open = function (method, url) {
      _method = (method || '').toUpperCase();
      _url    = url || '';
      real.open(method, url);
    };

    proxy.setRequestHeader = function (name, value) {
      _headers[name] = value;
      // do NOT forward to real XHR — we'll handle headers in fetch
    };

    proxy.send = function (body) {
      // Only intercept PUT to /upload-direct with a real Blob/File body
      const isUploadDirect = _url && _url.includes('/upload-direct');
      const isFile = body instanceof Blob || body instanceof File || body instanceof ArrayBuffer;

      if (_method === 'PUT' && isUploadDirect && isFile) {
        // ── Chunked upload path ─────────────────────────────────────────
        const fileBlob    = body instanceof ArrayBuffer ? new Blob([body]) : body;
        const filename    = (new URL(_url, location.href)).searchParams.get('filename') || 'media.mp4';
        const contentType = fileBlob.type || _headers['Content-Type'] || 'video/mp4';
        const token       = getAuthToken();
        const uploadId    = randomId();
        const totalChunks = Math.ceil(fileBlob.size / CHUNK_SIZE);

        console.log('[ChunkedUpload] Starting: ' + filename +
                    ' | ' + (fileBlob.size / 1024 / 1024).toFixed(1) + ' MB' +
                    ' | ' + totalChunks + ' chunk(s)');

        (async () => {
          try {
            for (let i = 0; i < totalChunks; i++) {
              const start  = i * CHUNK_SIZE;
              const end    = Math.min(start + CHUNK_SIZE, fileBlob.size);
              const slice  = fileBlob.slice(start, end, contentType);

              await postChunk(uploadId, i, totalChunks, slice, token);

              // Report progress
              const pct = Math.round(((i + 1) / totalChunks) * 95); // up to 95% during chunks
              if (_onprogress) {
                _onprogress({ lengthComputable: true, loaded: pct, total: 100 });
              }
              console.log('[ChunkedUpload] Chunk ' + (i + 1) + '/' + totalChunks + ' sent');
            }

            // Assemble
            const result = await assembleChunks(uploadId, totalChunks, filename, contentType, token);
            console.log('[ChunkedUpload] Assembled:', result);

            // Report 100%
            if (_onprogress) {
              _onprogress({ lengthComputable: true, loaded: 100, total: 100 });
            }

            // Synthesise a successful XHR response so the original onload fires
            Object.defineProperty(real, 'status',       { get: () => 200 });
            Object.defineProperty(real, 'responseText', { get: () => JSON.stringify(result) });
            Object.defineProperty(real, 'response',     { get: () => JSON.stringify(result) });
            if (_onload) _onload({ target: real });

          } catch (err) {
            console.error('[ChunkedUpload] Error:', err);
            Object.defineProperty(real, 'status', { get: () => 0 });
            if (_onerror) _onerror(new ProgressEvent('error'));
            else if (_onload) {
              // Some frontends only bind onload and check status
              Object.defineProperty(real, 'status', { get: () => 500 });
              _onload({ target: real });
            }
          }
        })();

      } else {
        // ── Normal (non-upload) XHR — pass through unchanged ────────────
        if (_onload)  real.onload  = _onload;
        if (_onerror) real.onerror = _onerror;
        if (real.upload && _onprogress) real.upload.onprogress = _onprogress;
        // Re-apply any stored headers
        for (const [k, v] of Object.entries(_headers)) {
          try { real.setRequestHeader(k, v); } catch (_) {}
        }
        real.send(body);
      }
    };

    return proxy;
  }

  // Inherit prototype so instanceof checks still work
  PatchedXHR.prototype = OriginalXHR.prototype;
  window.XMLHttpRequest = PatchedXHR;

  console.log('[ChunkedUpload] XHR interceptor active — uploads will be sent in 5 MB chunks');
})();
