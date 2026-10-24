document.querySelectorAll('.auto-submit').forEach(el => el.addEventListener('change', () => el.form.requestSubmit()));
document.querySelectorAll('form[data-confirm]').forEach(el => el.addEventListener('submit', event => { if (!window.confirm(el.dataset.confirm)) event.preventDefault(); }));
document.querySelector('.menu-toggle')?.addEventListener('click', () => document.body.classList.toggle('menu-open'));
document.querySelector('.print-button')?.addEventListener('click', () => window.print());
