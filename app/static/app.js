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
