document.querySelectorAll('.auto-submit').forEach(el => el.addEventListener('change', () => el.form.requestSubmit()));
document.querySelectorAll('form[data-confirm]').forEach(el => el.addEventListener('submit', event => { if (!window.confirm(el.dataset.confirm)) event.preventDefault(); }));
document.querySelector('.menu-toggle')?.addEventListener('click', () => document.body.classList.toggle('menu-open'));
document.querySelector('.print-button')?.addEventListener('click', () => window.print());

// El menú se mantiene visible sin JavaScript; se mejora al vincular sus controles.
const publicHeader = document.querySelector('.site-header');
const publicMenuButton = document.querySelector('.public-menu-toggle');
if (publicHeader && publicMenuButton) {
  publicMenuButton.hidden = false;
  publicHeader.classList.add('nav-enhanced');
  const closePublicMenu = () => {
    publicHeader.classList.remove('nav-open');
    publicMenuButton.setAttribute('aria-expanded', 'false');
    publicMenuButton.setAttribute('aria-label', 'Abrir menú de navegación');
  };
  publicMenuButton.addEventListener('click', () => {
    const expanded = publicHeader.classList.toggle('nav-open');
    publicMenuButton.setAttribute('aria-expanded', String(expanded));
    publicMenuButton.setAttribute('aria-label', expanded ? 'Cerrar menú de navegación' : 'Abrir menú de navegación');
  });
  publicHeader.querySelectorAll('.public-links a').forEach(link => link.addEventListener('click', closePublicMenu));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && publicHeader.classList.contains('nav-open')) {
      closePublicMenu(); publicMenuButton.focus();
    }
  });
  document.addEventListener('click', event => {
    if (!publicHeader.contains(event.target)) closePublicMenu();
  });
}
const groupFilters = document.querySelector('.group-segment');
if (groupFilters) {
  groupFilters.hidden = false;
  const cards = [...document.querySelectorAll('[data-group-kind]')];
  groupFilters.querySelectorAll('[data-group-filter]').forEach(button => {
    button.addEventListener('click', () => {
      const kind = button.dataset.groupFilter;
      groupFilters.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
      cards.forEach(card => { card.hidden = kind !== 'all' && card.dataset.groupKind !== kind; });
      const result = document.querySelector('#group-filter-result');
      if (result) result.textContent = `${cards.filter(card => !card.hidden).length} grupos visibles${kind === 'all' ? '' : ' de tipo ' + kind}.`;
    });
  });
}

// Menú móvil nativo: funciona incluso si JavaScript no carga.
const nativeMenu = document.querySelector('.native-mobile-menu');
if (nativeMenu) {
  nativeMenu.querySelectorAll('nav a').forEach(link => link.addEventListener('click', () => { nativeMenu.open = false; }));
  document.addEventListener('click', event => { if (!nativeMenu.contains(event.target)) nativeMenu.open = false; });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && nativeMenu.open) { nativeMenu.open = false; nativeMenu.querySelector('summary').focus(); }
  });
}
// Carrusel de archivos. Sin avance automático para no interrumpir la lectura.
document.querySelectorAll('[data-carousel]').forEach(carousel => {
  const slides = [...carousel.querySelectorAll('[data-slide]')];
  let position = 0;
  const show = offset => {
    if (!slides.length) return;
    position = (position + offset + slides.length) % slides.length;
    slides.forEach((slide,index) => { slide.hidden = index !== position; slide.classList.toggle('active',index === position); });
    const counter = carousel.querySelector('[data-slide-counter]');
    if (counter) counter.textContent = `${position + 1} / ${slides.length}`;
  };
  carousel.querySelector('[data-carousel-prev]')?.addEventListener('click', () => show(-1));
  carousel.querySelector('[data-carousel-next]')?.addEventListener('click', () => show(1));
});
const eventGroup = document.querySelector('[data-event-group]');
const eventLocation = document.querySelector('input[name="location"]');
if (eventGroup && eventLocation) {
  let previousDefault = '';
  const setDefaultLocation = () => {
    const address = eventGroup.selectedOptions[0]?.dataset.address || '';
    if (!eventLocation.value || eventLocation.value === previousDefault) eventLocation.value = address;
    previousDefault = address;
  };
  setDefaultLocation(); eventGroup.addEventListener('change', setDefaultLocation);
}
// El servidor devuelve la tarjeta autorizada. Los enlaces siguen funcionando sin JS.
let calendarRequest;
document.querySelectorAll('[data-calendar-event]').forEach(link => {
  link.addEventListener('click', async event => {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const detail = document.querySelector('#calendar-detail');
    if (!detail) return;
    event.preventDefault(); calendarRequest?.abort(); calendarRequest = new AbortController();
    detail.setAttribute('aria-busy','true');
    try {
      const response = await fetch(link.href,{signal:calendarRequest.signal});
      if (!response.ok) throw new Error('No disponible');
      const page = new DOMParser().parseFromString(await response.text(),'text/html');
      const updated = page.querySelector('#calendar-detail');
      if (!updated) throw new Error('Sin detalle');
      detail.replaceChildren(...updated.childNodes); detail.removeAttribute('aria-busy');
      document.querySelectorAll('[data-calendar-event]').forEach(item => {
        if (item.dataset.calendarEvent === link.dataset.calendarEvent) item.setAttribute('aria-current','true');
        else item.removeAttribute('aria-current');
      });
      history.replaceState(null,'',link.href);
      const description = detail.querySelector('.event-description');
      if (description) description.open = true;
      if (window.matchMedia('(max-width:900px)').matches) detail.scrollIntoView({behavior:'auto',block:'start'});
      detail.focus({preventScroll:true});
    } catch(error) {
      if (error.name !== 'AbortError') window.location.assign(link.href);
    }
  });
});
