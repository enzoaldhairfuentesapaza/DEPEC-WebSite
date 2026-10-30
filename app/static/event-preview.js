// Solo vista previa: el archivo no se envía hasta pulsar Guardar.
document.querySelectorAll('[data-event-editor]').forEach(form => {
  const stage = form.querySelector('[data-preview-card]');
  const config = JSON.parse(form.querySelector('[data-preview-config]').textContent);
  const card = stage.querySelector('.y-event');
  const status = form.querySelector('[data-preview-status]');
  const field = name => form.elements.namedItem(name);
  const value = name => field(name)?.value || '';
  let source = config.original, width = Number(config.width), height = Number(config.height);
  let objectUrl, generation = 0;
  const update = () => {
    const mode = value('image_mode'), layout = value('card_layout');
    const preset = value('generic_image') || 'Encuentro';
    const generic = mode === 'Imagen genérica';
    const src = generic ? config.generic[preset] : mode === 'Sin imagen' ? '' : source;
    const wide = !src || (generic ? preset !== 'Encuentro' : width > height);
    const orientation = layout === 'Horizontal' ? 'landscape' : layout === 'Vertical' ? 'portrait' : wide ? 'landscape' : 'portrait';
    card.classList.toggle('portrait', orientation === 'portrait');
    card.classList.toggle('landscape', orientation === 'landscape');
    card.classList.toggle('text-only', !src);
    let picture = card.querySelector('.y-event-picture');
    if (src) {
      if (!picture) {
        picture = document.createElement('div'); picture.className = 'y-event-picture';
        const img = document.createElement('img'); img.alt = 'Vista previa de la imagen del evento';
        const badge = document.createElement('span'); badge.className = 'file-kind';
        picture.append(img,badge); card.prepend(picture);
      }
      const img = picture.querySelector('img');
      if (img.getAttribute('src') !== src) img.src = src;
      picture.querySelector('.file-kind').textContent = generic ? 'Imagen genérica' : value('media_kind') || 'Afiche';
    } else picture?.remove();
    field('generic_image').closest('label').hidden = !generic;
    field('attachment').closest('label').hidden = mode !== 'Imagen propia';
    const group = field('group_id').selectedOptions[0];
    card.style.setProperty('--church',group.dataset.color);
    card.style.setProperty('--on-church',group.dataset.contrast);
    card.querySelector('.church-label').textContent = group.textContent;
    card.querySelector('h3').textContent = value('title') || 'Tu próximo encuentro';
    card.querySelector('.event-description p').textContent = value('body') || 'La descripción de tu evento aparecerá aquí.';
    const start = value('date'), end = value('end_date');
    field('date').required = field('end_date').required = value('status') !== 'Por programar';
    const format = raw => raw ? `${raw.slice(8,10)}/${raw.slice(5,7)}/${raw.slice(0,4)} · ${raw.slice(11,16)} h` : 'Fecha y hora por definir';
    card.querySelector('.event-calendar-link').textContent = start && end ? 'Ver en calendario ↗' : 'Fecha por confirmar';
    const time = card.querySelector('time'); time.textContent = format(start); time.dateTime = start;
    card.querySelector('.event-description p:last-child').textContent = end ? `Hasta ${format(end)}` : 'Finalización por definir';
    const facts = card.querySelector('.event-facts-large');
    let place = facts.querySelector('a,p');
    if (!place) { place = document.createElement('p'); facts.append(place); }
    place.textContent = `⌖ ${value('location') || group.dataset.address || 'Lugar por confirmar'}`;
    let state = value('status');
    if (state !== 'Cancelado' && state !== 'Por programar') {
      if (['Realizado','Finalizado'].includes(state) || end && Date.parse(end+'-05:00') <= Date.now()) state = 'Finalizado';
      else if (state !== 'Reprogramado') state = start && Date.parse(start+'-05:00') <= Date.now() ? 'En curso' : 'Pronto';
    }
    const badge = card.querySelector('.event-state');
    badge.textContent = state; badge.className = 'event-state state-'+state.toLowerCase().replaceAll(' ','-');
    status.textContent = `${orientation === 'portrait' ? 'Vertical' : 'Horizontal'} · ${layout === 'Automático' ? 'detectado automáticamente' : 'elegido por ti'} · ${src ? generic ? 'imagen del sistema' : 'imagen propia' : 'solo información'}`;
  };
  form.addEventListener('input', update);
  form.addEventListener('change', update);
  field('attachment').addEventListener('change', () => {
    const current = ++generation, file = field('attachment').files[0];
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    if (!file) { source = config.original; width = config.width; height = config.height; update(); return; }
    objectUrl = URL.createObjectURL(file);
    const candidate = objectUrl, img = new Image();
    status.textContent = 'Leyendo imagen…';
    img.onload = () => {
      if (generation !== current) return;
      source = candidate; width = img.naturalWidth; height = img.naturalHeight;
      field('image_mode').value = 'Imagen propia'; update();
    };
    img.onerror = () => { if (generation === current) { source = ''; update(); status.textContent = 'No se pudo leer esta imagen. Selecciona un PNG o JPG válido.'; } };
    img.src = candidate;
  });
  window.addEventListener('pagehide', () => { if (objectUrl) URL.revokeObjectURL(objectUrl); });
  const venue = form.querySelector('[data-venue-picker]');
  const applyVenue = () => {
    if (!venue) return;
    const location = field('location');
    if (venue.value) location.value = venue.selectedOptions[0].dataset.address || '';
    location.readOnly = Boolean(venue.value); update();
  };
  venue?.addEventListener('change',applyVenue);
  field('group_id').addEventListener('change',applyVenue);
  field('attachment').addEventListener('change',() => {
    const note=form.querySelector('[data-file-name]');
    if(note) note.textContent=field('attachment').files[0]?.name || 'Sin archivo: puedes continuar sin imagen.';
  });
  applyVenue(); update();
});
