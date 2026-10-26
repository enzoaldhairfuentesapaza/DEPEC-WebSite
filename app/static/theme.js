// Se ejecuta antes de los estilos para aplicar la preferencia sin destellos.
(() => {
  const key = 'depec-color-theme';
  const preference = window.matchMedia('(prefers-color-scheme: dark)');
  let mode = 'system';
  try { const saved = localStorage.getItem(key); if (['light','dark','system'].includes(saved)) mode = saved; } catch (_) {}
  const apply = () => {
    const effective = mode === 'system' ? (preference.matches ? 'dark' : 'light') : mode;
    document.documentElement.dataset.theme = effective;
    document.documentElement.style.colorScheme = effective;
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      const label = mode === 'system' ? 'Sistema' : mode === 'dark' ? 'Oscuro' : 'Claro';
      button.textContent = `${effective === 'dark' ? '☾' : '☀'} ${label}`;
      button.setAttribute('aria-label',`Tema ${label}. Cambiar tema de color`);
      button.dataset.mode = mode;
    });
  };
  apply();
  document.addEventListener('DOMContentLoaded',() => {
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.hidden = false;
      button.addEventListener('click',() => {
        mode = mode === 'system' ? 'light' : mode === 'light' ? 'dark' : 'system';
        try { localStorage.setItem(key,mode); } catch (_) {}
        apply();
      });
    });
    apply();
  });
  preference.addEventListener('change',apply);
})();
