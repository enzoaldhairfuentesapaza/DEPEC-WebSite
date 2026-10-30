(() => {
  const viewer = document.querySelector('[data-image-viewer]');
  const main = document.querySelector('.public-main');
  if (!viewer || !main || typeof viewer.showModal !== 'function') return;
  const fullImage = viewer.querySelector('[data-viewer-image]');
  const stage = viewer.querySelector('[data-viewer-stage]');
  const zoom = viewer.querySelector('[data-viewer-zoom]');
  const previous = viewer.querySelector('[data-viewer-prev]');
  const next = viewer.querySelector('[data-viewer-next]');
  const error = viewer.querySelector('[data-viewer-error]');
  let images = [], position = 0, opener;
  const eligible = img => !img.closest('.collage-filler,.avatar-options,[aria-hidden="true"],[inert]');
  const resetZoom = () => {
    stage.classList.remove('is-original'); stage.scrollTop = 0; stage.scrollLeft = 0;
    zoom.setAttribute('aria-pressed','false'); zoom.textContent = 'Tamaño original';
  };
  const show = index => {
    position = (index + images.length) % images.length;
    const image = images[position];
    const source = image.currentSrc || image.src;
    resetZoom(); error.hidden = true;
    fullImage.alt = image.alt || 'Imagen ampliada'; fullImage.src = source;
    const caption = image.closest('figure')?.querySelector('figcaption')?.innerText.trim();
    viewer.querySelector('[data-viewer-caption]').textContent = caption || image.alt || 'Imagen de nuestra comunidad';
    viewer.querySelector('[data-viewer-counter]').textContent = `${position + 1} / ${images.length}`;
    viewer.querySelector('[data-viewer-original]').href = source;
    previous.hidden = next.hidden = images.length < 2;
  };
  const open = (image,trigger) => {
    const group = image.closest('.album-photos,[data-carousel],section') || main;
    images = [...group.querySelectorAll('img[data-viewer-bound]')].filter(img => eligible(img) && img.getClientRects().length);
    if (!images.includes(image)) images = [image];
    opener = trigger || image.closest('a') || document.activeElement;
    show(images.indexOf(image)); viewer.showModal(); document.body.classList.add('image-viewer-open');
  };
  const enhance = () => {
    main.querySelectorAll('img:not([data-viewer-bound])').forEach(image => {
      if (!eligible(image)) return;
      image.dataset.viewerBound = '1';
      const label = 'Ampliar: '+(image.alt || 'imagen');
      const link = image.closest('a');
      if (link && !link.textContent.trim()) {
        link.dataset.viewerLink = '1'; link.setAttribute('aria-label',label);
        // El clic amplía la foto; el destino del álbum continúa en su leyenda.
        if (link.href.includes('/album/')) {
          const caption = image.closest('figure')?.querySelector('figcaption');
          if (caption && !caption.querySelector('.viewer-context-link')) {
            const albumLink = document.createElement('a'); albumLink.className = 'viewer-context-link';
            albumLink.href = link.href; albumLink.textContent = 'Ver álbum ↗'; caption.append(albumLink);
          }
        }
        return;
      }
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'image-expand-trigger';
      button.textContent = '⤢'; button.setAttribute('aria-label',label); button.title = label;
      button.addEventListener('click',event => { event.preventDefault(); event.stopPropagation(); open(image,button); });
      if (link) {
        // Botón hermano del enlace: sin controles interactivos anidados.
        const wrapper = document.createElement('div'); wrapper.className = 'image-linked-wrapper';
        link.before(wrapper); wrapper.append(link,button); wrapper.hidden = link.hidden;
      } else {
        image.parentElement.classList.add('image-zoom-container'); image.after(button);
      }
    });
  };
  main.addEventListener('click',event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const image = event.target.closest('img[data-viewer-bound]') || event.target.closest('a[data-viewer-link]')?.querySelector('img');
    if (!image) return;
    event.preventDefault(); event.stopPropagation(); open(image,image.closest('a') || document.activeElement);
  });
  previous.addEventListener('click',() => show(position - 1));
  next.addEventListener('click',() => show(position + 1));
  zoom.addEventListener('click',() => {
    const original = stage.classList.toggle('is-original');
    zoom.setAttribute('aria-pressed',String(original)); zoom.textContent = original ? 'Ajustar a pantalla' : 'Tamaño original';
  });
  fullImage.addEventListener('error',() => { error.hidden = false; });
  viewer.addEventListener('keydown',event => {
    if (images.length < 2) return;
    if (event.key === 'ArrowLeft') { event.preventDefault(); show(position - 1); }
    if (event.key === 'ArrowRight') { event.preventDefault(); show(position + 1); }
  });
  viewer.addEventListener('click',event => { if (event.target === viewer) viewer.close(); });
  viewer.addEventListener('close',() => {
    document.body.classList.remove('image-viewer-open');
    fullImage.removeAttribute('src');
    if (opener?.isConnected) opener.focus({preventScroll:true});
  });
  enhance();
  new MutationObserver(changes => {
    changes.forEach(change => {
      if (change.type === 'attributes' && change.target.parentElement?.classList.contains('image-linked-wrapper')) {
        change.target.parentElement.hidden = change.target.hidden;
      }
    });
    enhance();
  }).observe(main,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden']});
})();

const contactBubble = document.querySelector('[data-contact-bubble]');
if (contactBubble) {
  document.addEventListener('click',event => {
    if (contactBubble.open && !contactBubble.contains(event.target)) contactBubble.open = false;
  });
  document.addEventListener('keydown',event => {
    if (event.key === 'Escape' && contactBubble.open && !document.querySelector('[data-image-viewer]')?.open) {
      contactBubble.open = false; contactBubble.querySelector('summary').focus();
    }
  });
}
