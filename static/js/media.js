// Shared media helpers used by the gallery and event pages:
//  - drag & drop upload: expects #drop-zone, #file-input, #preview-strip, #upload-actions, #file-count
//  - lightbox: expects #lightbox, #lightbox-img, #lightbox-vid; items call openLightbox(el)
// ---- Drag & drop upload ----
// Files are sent one per request (a few in parallel) because Cloudflare rejects any single
// request over 100 MB with a 413. The form can opt into extra behaviour with data attributes:
//   data-create-first  POST the other form fields first; the JSON reply gives {upload_url, redirect}
//   data-done-url      after uploading, go to this URL with the new MediaFile ids appended
//   (neither)          upload to the form's own URL, then reload the page
(function () {
    const zone    = document.getElementById('drop-zone');
    if (!zone) return;

    const input   = document.getElementById('file-input');
    const strip   = document.getElementById('preview-strip');
    const actions = document.getElementById('upload-actions');
    const countEl = document.getElementById('file-count');
    const form    = input.form;
    let dt = new DataTransfer();

    const MAX_BYTES   = 95 * 1000 * 1000;  // stay under Cloudflare's 100 MB request limit
    const CONCURRENCY = 3;

    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        addFiles(e.dataTransfer.files);
    });
    input.addEventListener('change', () => { addFiles(input.files); });

    function addFiles(files) {
        const tooBig = [];
        for (const f of files) {
            if (!f.type.startsWith('image/') && !f.type.startsWith('video/')) continue;
            if (f.size > MAX_BYTES) { tooBig.push(f.name); continue; }
            dt.items.add(f);
            addThumb(f);
        }
        input.files = dt.files;
        update();
        if (tooBig.length) {
            alert('These files are over 95 MB, which is the most that can be uploaded at once, ' +
                  'so they were skipped:\n\n' + tooBig.join('\n'));
        }
    }

    function addThumb(file) {
        const thumb = document.createElement('div');
        thumb.className = 'preview-thumb';
        thumb.dataset.name = file.name;

        const url = URL.createObjectURL(file);
        const media = file.type.startsWith('video/')
            ? Object.assign(document.createElement('video'), { src: url, muted: true })
            : Object.assign(document.createElement('img'), { src: url });
        thumb.appendChild(media);

        const btn = document.createElement('button');
        btn.className = 'rm';
        btn.type = 'button';
        btn.textContent = '×';
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const newDt = new DataTransfer();
            for (const f of dt.files) { if (f !== file) newDt.items.add(f); }
            dt = newDt;
            input.files = dt.files;
            thumb.remove();
            update();
        });
        thumb.appendChild(btn);
        strip.appendChild(thumb);
    }

    function update() {
        const n = dt.files.length;
        strip.style.display   = n ? 'flex' : 'none';
        actions.style.cssText = n ? '' : 'display:none !important';
        countEl.textContent   = n + ' file' + (n !== 1 ? 's' : '') + ' selected';
    }

    // POST a FormData with XHR (fetch can't report upload progress). Resolves with parsed JSON.
    function post(url, data, onProgress) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            xhr.open('POST', url);
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            if (onProgress) xhr.upload.onprogress = e => onProgress(e.loaded);
            xhr.onload = () => {
                let body = null;
                try { body = JSON.parse(xhr.responseText); } catch (_) { /* non-JSON error page */ }
                if (xhr.status >= 200 && xhr.status < 300 && body) resolve(body);
                else reject({ status: xhr.status, body });
            };
            xhr.onerror = () => reject({ status: 0, body: null });
            xhr.send(data);
        });
    }

    function setBusy(busy) {
        form.querySelectorAll('button[type=submit]').forEach(b => { b.disabled = busy; b.classList.toggle('opacity-60', busy); });
        zone.style.pointerEvents = busy ? 'none' : '';
    }

    form.addEventListener('submit', async e => {
        const files = Array.from(dt.files);
        if (!files.length) return;          // nothing to upload: normal form submit
        e.preventDefault();
        setBusy(true);

        const csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
        let uploadUrl = form.action || window.location.href;
        let nextUrl = null;

        // Event creation: save the event details first, then attach photos to it
        if ('createFirst' in form.dataset) {
            const fields = new FormData(form);
            fields.delete('images');
            try {
                const res = await post(uploadUrl, fields);
                uploadUrl = res.upload_url;
                nextUrl = res.redirect;
            } catch (err) {
                setBusy(false);
                const errors = err.body && err.body.errors;
                alert(errors
                    ? Object.entries(errors).map(([f, msgs]) => `${f}: ${msgs.join(' ')}`).join('\n')
                    : 'Could not save the event (error ' + err.status + '). Please try again.');
                return;
            }
        }

        // Upload files individually with a small worker pool, tracking total bytes for progress
        const total = files.reduce((n, f) => n + f.size, 0);
        const loaded = new Map();
        const ids = [], failed = [];
        let done = 0, queue = files.slice();
        const report = () => {
            const sent = [...loaded.values()].reduce((a, b) => a + b, 0);
            countEl.textContent = `Uploading ${done} of ${files.length}… ${Math.round(100 * sent / total)}%`;
        };
        report();

        async function worker() {
            while (queue.length) {
                const file = queue.shift();
                const data = new FormData();
                data.append('csrfmiddlewaretoken', csrf);
                data.append('images', file);
                try {
                    const res = await post(uploadUrl, data, n => { loaded.set(file, n); report(); });
                    ids.push(...(res.ids || []));
                } catch (err) {
                    failed.push(`${file.name} (error ${err.status || 'network'})`);
                }
                loaded.set(file, file.size);
                done++;
                report();
            }
        }
        await Promise.all(Array.from({ length: Math.min(CONCURRENCY, files.length) }, worker));

        if (failed.length) alert('Some files did not upload:\n\n' + failed.join('\n'));

        if (form.dataset.doneUrl) {
            window.location.href = ids.length ? form.dataset.doneUrl + ids.join(',') : window.location.href;
        } else if (nextUrl) {
            window.location.href = nextUrl;
        } else {
            window.location.reload();
        }
    });
})();

// ---- Lightbox ----
function openLightbox(el) {
    const lb  = document.getElementById('lightbox');
    const img = document.getElementById('lightbox-img');
    const vid = document.getElementById('lightbox-vid');
    if (el.dataset.type === 'video') {
        vid.src = el.dataset.src;
        vid.style.display = ''; img.style.display = 'none';
    } else {
        img.src = el.dataset.src;
        img.style.display = ''; vid.style.display = 'none';
    }
    lb.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeLightbox() {
    const lb  = document.getElementById('lightbox');
    if (!lb) return;  // page has no lightbox (e.g. event form)
    const vid = document.getElementById('lightbox-vid');
    vid.pause(); vid.src = '';
    document.getElementById('lightbox-img').src = '';
    lb.classList.remove('open');
    document.body.style.overflow = '';
}

function handleLightboxClick(e) {
    if (e.target.id === 'lightbox' || e.target.closest('.lightbox-close')) closeLightbox();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });
