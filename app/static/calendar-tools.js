const cardModal=document.querySelector('[data-card-modal]');
let cardTrigger;
document.querySelectorAll('[data-card-open]').forEach(trigger=>trigger.addEventListener('click',event=>{
  if(!cardModal || !cardModal.showModal)return;
  event.preventDefault();cardTrigger=trigger;
  cardModal.querySelector('[data-modal-content]').replaceChildren(document.getElementById(trigger.dataset.cardOpen).content.cloneNode(true));
  cardModal.showModal();
}));
cardModal?.querySelector('.modal-close').addEventListener('click',()=>cardModal.close());
cardModal?.addEventListener('click',event=>{if(event.target===cardModal){const r=cardModal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)cardModal.close();}});
cardModal?.addEventListener('close',()=>cardTrigger?.focus());
document.querySelectorAll('[data-worship-day]').forEach(button=>button.addEventListener('click',()=>{
 const editor=document.getElementById('worship-editor');const form=editor.querySelector('[data-worship-exception]');
 editor.open=true;form.elements.group_id.value=button.dataset.worshipGroup;form.elements.day.value=button.dataset.worshipDay;
 form.elements.cancelled.checked=button.closest('.worship-marker').classList.contains('cancelled');
 form.elements.note.value=button.closest('.worship-marker').querySelector('small')?.textContent||'';
 form.scrollIntoView({behavior:'smooth',block:'center'});form.elements.note.focus();
}));
const weeklyForm=document.querySelector('.worship-forms form');
if(weeklyForm){const select=weeklyForm.elements.group_id;const fill=()=>{const option=select.selectedOptions[0];weeklyForm.elements.weekday.value=option.dataset.weekday;weeklyForm.elements.hour.value=option.dataset.hour;};select.addEventListener('change',fill);fill();}
