document.querySelectorAll('[data-office-audience]').forEach(select=>{
 const invites=select.form.querySelector('[data-office-invites]');
 if(!invites)return;
 const update=()=>{invites.hidden=select.value!=='Iglesias';};
 select.addEventListener('change',update);update();
});
// Impide dobles clics mientras viaja un formulario; los envíos financieros
// también tienen una clave de idempotencia validada por el servidor.
document.querySelectorAll('.office-form').forEach(form=>form.addEventListener('submit',()=>{
 const button=form.querySelector('button[type="submit"],button:not([type])');
 if(button){button.disabled=true;button.setAttribute('aria-busy','true');}
}));
