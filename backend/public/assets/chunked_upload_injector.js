/**
 * chunked_upload_injector.js
 *
 * Intercepts XMLHttpRequest prototype to chunk large file uploads (5 MB per chunk).
 * Uses standard prototype method wrapping (NO Proxies) to prevent stack overflows
 * or circular event references.
 */
(function () {
  'use strict';

  const CHUNK_SIZE   = 5 * 1024 * 1024;   // 5 MB per chunk
  const API_BASE     = '/api/v1/episodes';
  const CHUNK_URL    = API_BASE + '/upload-chunk';
  const ASSEMBLE_URL = API_BASE + '/upload-assemble';

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

  // Preserve native prototype methods
  const rawOpen = XMLHttpRequest.prototype.open;
  const rawSend = XMLHttpRequest.prototype.send;
  const rawSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;

  XMLHttpRequest.prototype.open = function (method, url) {
    this._customMethod = (method || '').toUpperCase();
    this._customUrl = url || '';
    this._customHeaders = {};
    return rawOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.setRequestHeader = function (header, value) {
    if (this._customHeaders) {
      this._customHeaders[header] = value;
    }
    return rawSetRequestHeader.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function (body) {
    const isDirectUpload = typeof this._customUrl === 'string' && this._customUrl.includes('/upload-direct');
    const isFile = body instanceof Blob || (typeof File !== 'undefined' && body instanceof File);

    // Only intercept PUT uploads directed to /upload-direct
    if (this._customMethod === 'PUT' && isDirectUpload && isFile) {
      const xhr = this;
      const fileBlob = body;
      let filename = 'media.mp4';
      try {
        const urlObj = new URL(xhr._customUrl, window.location.href);
        filename = urlObj.searchParams.get('filename') || 'media.mp4';
      } catch (_) {}

      const contentType = fileBlob.type || (xhr._customHeaders && xhr._customHeaders['Content-Type']) || 'video/mp4';
      const token = getAuthToken();
      const uploadId = randomId();
      const totalChunks = Math.max(1, Math.ceil(fileBlob.size / CHUNK_SIZE));

      console.log('[ChunkedUpload] Slicing upload:', filename, '| size:', (fileBlob.size / (1024 * 1024)).toFixed(2), 'MB | chunks:', totalChunks);

      (async function () {
        try {
          for (let i = 0; i < totalChunks; i++) {
            const start = i * CHUNK_SIZE;
            const end = Math.min(start + CHUNK_SIZE, fileBlob.size);
            const slice = fileBlob.slice(start, end, contentType);

            const form = new FormData();
            form.append('upload_id', uploadId);
            form.append('chunk_index', String(i));
            form.append('total_chunks', String(totalChunks));
            form.append('file', slice, 'chunk');

            const h = {};
            if (token) h['Authorization'] = 'Bearer ' + token;

            const res = await fetch(CHUNK_URL, { method: 'POST', headers: h, body: form });
            if (!res.ok) {
              const errText = await res.text().catch(() => String(res.status));
              throw new Error('Chunk ' + (i + 1) + '/' + totalChunks + ' error (' + res.status + '): ' + errText);
            }

            // Fire progress on xhr.upload
            const pct = Math.round(((i + 1) / totalChunks) * 90);
            try {
              if (xhr.upload && typeof xhr.upload.onprogress === 'function') {
                xhr.upload.onprogress({ lengthComputable: true, loaded: pct, total: 100 });
              }
            } catch (_) {}
          }

          // Assemble chunks
          const asmHeaders = { 'Content-Type': 'application/json' };
          if (token) asmHeaders['Authorization'] = 'Bearer ' + token;

          const asmRes = await fetch(ASSEMBLE_URL, {
            method: 'POST',
            headers: asmHeaders,
            body: JSON.stringify({
              upload_id: uploadId,
              total_chunks: totalChunks,
              filename: filename,
              content_type: contentType,
            }),
          });

          if (!asmRes.ok) {
            const errText = await asmRes.text().catch(() => String(asmRes.status));
            throw new Error('Assembly error (' + asmRes.status + '): ' + errText);
          }

          const asmData = await asmRes.json();
          console.log('[ChunkedUpload] Assembly complete:', asmData);

          try {
            if (xhr.upload && typeof xhr.upload.onprogress === 'function') {
              xhr.upload.onprogress({ lengthComputable: true, loaded: 100, total: 100 });
            }
          } catch (_) {}

          // Populate standard response properties on native XHR instance
          Object.defineProperty(xhr, 'readyState', { value: 4, configurable: true, writable: true });
          Object.defineProperty(xhr, 'status', { value: 200, configurable: true, writable: true });
          Object.defineProperty(xhr, 'statusText', { value: 'OK', configurable: true, writable: true });
          Object.defineProperty(xhr, 'responseText', { value: JSON.stringify(asmData), configurable: true, writable: true });
          Object.defineProperty(xhr, 'response', { value: JSON.stringify(asmData), configurable: true, writable: true });

          if (typeof xhr.onload === 'function') {
            xhr.onload();
          }
          if (typeof xhr.onreadystatechange === 'function') {
            xhr.onreadystatechange();
          }
          try {
            xhr.dispatchEvent(new Event('load'));
            xhr.dispatchEvent(new Event('loadend'));
          } catch (_) {}

        } catch (err) {
          console.error('[ChunkedUpload] Upload failed:', err);
          Object.defineProperty(xhr, 'readyState', { value: 4, configurable: true, writable: true });
          Object.defineProperty(xhr, 'status', { value: 500, configurable: true, writable: true });
          Object.defineProperty(xhr, 'statusText', { value: 'Upload Error', configurable: true, writable: true });

          if (typeof xhr.onerror === 'function') {
            xhr.onerror(err);
          } else if (typeof xhr.onload === 'function') {
            xhr.onload();
          }
          try {
            xhr.dispatchEvent(new Event('error'));
            xhr.dispatchEvent(new Event('loadend'));
          } catch (_) {}
        }
      })();

      return;
    }

    return rawSend.apply(this, arguments);
  };

  console.log('[ChunkedUpload] Prototype-based XHR interceptor successfully installed.');
})();
