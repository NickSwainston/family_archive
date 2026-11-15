// Shared media helpers used by the gallery and event pages:
//  - drag & drop upload: expects #drop-zone, #file-input, #preview-strip, #upload-actions, #file-count
//  - lightbox: expects #lightbox, #lightbox-img, #lightbox-vid; items call openLightbox(el)
// ---- Drag & drop upload ----
(function () {
    const zone    = document.getElementById('drop-zone');
    if (!zone) return;

    const input   = document.getElementById('file-input');
    const strip   = document.getElementById('preview-strip');
    const actions = document.getElementById('upload-actions');
    const countEl = document.getElementById('file-count');
    let dt = new DataTransfer();

    zone.addEventListener('dragover',  e => { e.preventDefault(); zone.classList.add('drag-over'); });
    zone.addEventListener('dragleave', ()  => zone.classList.remove('drag-over'));
    zone.addEventListener('drop', e => {
        e.preventDefault();
        zone.classList.remove('drag-over');
        addFiles(e.dataTransfer.files);
    });
    input.addEventListener('change', () => { addFiles(input.files); });

    function addFiles(files) {
        for (const f of files) {
            if (!f.type.startsWith('image/') && !f.type.startsWith('video/')) continue;
            dt.items.add(f);
            addThumb(f);
        }
        input.files = dt.files;
        update();
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
            for (const f of dt.files) { if (f.name !== file.name) newDt.items.add(f); }
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
