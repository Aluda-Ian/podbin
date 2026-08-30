/**
 * chunked_upload_injector.js
 *
 * Intercepts frontend XMLHttpRequest file uploads and splits large files into 5 MB chunks.
 * Uses a clean wrapper class around native XMLHttpRequest to provide fully writable
 * properties (status, readyState, responseText) and realistic progress events without
 * any fragile native property redefinitions or prototype collisions.
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

  const NativeXMLHttpRequest = window.XMLHttpRequest;

  class FakeUploadEventTarget extends EventTarget {
    constructor() {
      super();
      this.onprogress = null;
    }
  }

  class ChunkedXMLHttpRequest extends EventTarget {
    constructor() {
      super();
      this.upload = new FakeUploadEventTarget();
      this.readyState = 0;
      this.status = 0;
      this.statusText = '';
      this.responseText = '';
      this.response = '';
      this.onload = null;
      this.onerror = null;
      this.onreadystatechange = null;
      this.onloadend = null;

      this._headers = {};
      this._method = 'GET';
      this._url = '';
      this._nativeXhr = null;
    }

    open(method, url, async, user, password) {
      this._method = (method || '').toUpperCase();
      this._url = url || '';
      this.readyState = 1;

      // For non-direct-upload requests, instantiate a real XMLHttpRequest
      if (!this._isDirectUpload()) {
        this._nativeXhr = new NativeXMLHttpRequest();

        this._nativeXhr.upload.onprogress = (ev) => {
          if (typeof this.upload.onprogress === 'function') {
            this.upload.onprogress(ev);
          }
          this.upload.dispatchEvent(new CustomEvent('progress', { detail: ev }));
        };

        this._nativeXhr.onreadystatechange = () => {
          this.readyState = this._nativeXhr.readyState;
          this.status = this._nativeXhr.status;
          this.statusText = this._nativeXhr.statusText;
          this.responseText = this._nativeXhr.responseText;
          this.response = this._nativeXhr.response;
          if (typeof this.onreadystatechange === 'function') {
            this.onreadystatechange();
          }
        };

        this._nativeXhr.onload = () => {
          this.readyState = this._nativeXhr.readyState;
          this.status = this._nativeXhr.status;
          this.statusText = this._nativeXhr.statusText;
          this.responseText = this._nativeXhr.responseText;
          this.response = this._nativeXhr.response;
          if (typeof this.onload === 'function') {
            this.onload();
          }
          this.dispatchEvent(new Event('load'));
        };

        this._nativeXhr.onerror = (err) => {
          if (typeof this.onerror === 'function') {
            this.onerror(err);
          }
          this.dispatchEvent(new Event('error'));
        };

        this._nativeXhr.open(method, url, async !== false, user, password);
      }
    }

    setRequestHeader(header, value) {
      this._headers[header] = value;
      if (this._nativeXhr) {
        this._nativeXhr.setRequestHeader(header, value);
      }
    }

    _isDirectUpload() {
      return typeof this._url === 'string' && this._url.includes('/upload-direct');
    }

    send(body) {
      const isFile = body instanceof Blob || (typeof File !== 'undefined' && body instanceof File);

      if (this._method === 'PUT' && this._isDirectUpload() && isFile) {
        this._performChunkedUpload(body);
        return;
      }

      if (this._nativeXhr) {
        this._nativeXhr.send(body);
      }
    }

    async _performChunkedUpload(fileBlob) {
      try {
        let filename = 'media.mp4';
        try {
          const urlObj = new URL(this._url, window.location.href);
          filename = urlObj.searchParams.get('filename') || 'media.mp4';
        } catch (_) {}

        const contentType = fileBlob.type || this._headers['Content-Type'] || 'video/mp4';
        const token = getAuthToken();
        const uploadId = randomId();
        const totalChunks = Math.max(1, Math.ceil(fileBlob.size / CHUNK_SIZE));

        console.log('[ChunkedUpload] Splitting upload:', filename, '| size:', (fileBlob.size / (1024 * 1024)).toFixed(2), 'MB | chunks:', totalChunks);

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
            throw new Error('Chunk ' + (i + 1) + '/' + totalChunks + ' failed with status ' + res.status + ': ' + errText);
          }

          const pct = Math.round(((i + 1) / totalChunks) * 95);
          const progEvent = { lengthComputable: true, loaded: pct, total: 100 };
          if (typeof this.upload.onprogress === 'function') {
            this.upload.onprogress(progEvent);
          }
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
          throw new Error('Assemble failed with status ' + asmRes.status + ': ' + errText);
        }

        const asmData = await asmRes.json();
        console.log('[ChunkedUpload] Assembly complete:', asmData);

        const doneProg = { lengthComputable: true, loaded: 100, total: 100 };
        if (typeof this.upload.onprogress === 'function') {
          this.upload.onprogress(doneProg);
        }

        this.readyState = 4;
        this.status = 200;
        this.statusText = 'OK';
        this.responseText = JSON.stringify(asmData);
        this.response = JSON.stringify(asmData);

        if (typeof this.onreadystatechange === 'function') {
          this.onreadystatechange();
        }
        if (typeof this.onload === 'function') {
          this.onload();
        }
        if (typeof this.onloadend === 'function') {
          this.onloadend();
        }
        this.dispatchEvent(new Event('load'));
        this.dispatchEvent(new Event('loadend'));

      } catch (err) {
        console.error('[ChunkedUpload] Upload error:', err);
        this.readyState = 4;
        this.status = 500;
        this.statusText = 'Upload Error';

        if (typeof this.onerror === 'function') {
          this.onerror(err);
        }
        if (typeof this.onloadend === 'function') {
          this.onloadend();
        }
        this.dispatchEvent(new Event('error'));
        this.dispatchEvent(new Event('loadend'));
      }
    }
  }

  // Install custom XMLHttpRequest constructor
  window.XMLHttpRequest = ChunkedXMLHttpRequest;

  console.log('[ChunkedUpload] Robust ChunkedXMLHttpRequest installed.');
})();
