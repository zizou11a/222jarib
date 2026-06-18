/* وظيفتي | Wazifati — Main JavaScript */

'use strict';

// ══ MOBILE NAV ══════════════════════════════════════════
const navToggle = document.getElementById('navToggle');
const navLinks  = document.getElementById('navLinks');

if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', open);
  });
  document.addEventListener('click', (e) => {
    if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
      navLinks.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    }
  });
}

// ══ MODAL ════════════════════════════════════════════════
function openModal(id) {
  const m = document.getElementById(id);
  if (m) { m.classList.add('open'); m.querySelector('.modal')?.focus(); }
}
function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove('open');
}
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

// ══ ROLE PICKER ══════════════════════════════════════════
function selectRole(role) {
  const roleInput   = document.getElementById('roleVal');
  const cardSeeker  = document.getElementById('cardSeeker');
  const cardCompany = document.getElementById('cardCompany');
  const coFields    = document.getElementById('companyFields');
  if (!roleInput) return;
  roleInput.value = role;
  cardSeeker?.classList.toggle('selected',  role === 'seeker');
  cardCompany?.classList.toggle('selected', role === 'company');
  if (coFields) coFields.style.display = role === 'company' ? 'block' : 'none';
}

// ══ AUTO-DISMISS FLASH ═══════════════════════════════════
setTimeout(() => {
  document.querySelectorAll('.flash').forEach(f => {
    f.style.transition = 'opacity .5s';
    f.style.opacity = '0';
    setTimeout(() => f.remove(), 500);
  });
}, 5000);

// ══ CONFIRM DELETE ═══════════════════════════════════════
document.querySelectorAll('[data-confirm]').forEach(btn => {
  btn.addEventListener('click', (e) => {
    if (!confirm(btn.dataset.confirm)) e.preventDefault();
  });
});

// ══ STATS COUNTER ANIMATION ══════════════════════════════
function animateCounter(el, target, duration = 1500) {
  let start = 0;
  const step = target / (duration / 16);
  const timer = setInterval(() => {
    start += step;
    if (start >= target) { el.textContent = target.toLocaleString('ar-DZ'); clearInterval(timer); }
    else el.textContent = Math.floor(start).toLocaleString('ar-DZ');
  }, 16);
}
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const el  = entry.target;
      const val = parseInt(el.dataset.count, 10);
      if (!isNaN(val)) animateCounter(el, val);
      observer.unobserve(el);
    }
  });
}, { threshold: 0.5 });
document.querySelectorAll('[data-count]').forEach(el => observer.observe(el));

// ══ FILTER FORM AUTO-SUBMIT ══════════════════════════════
document.querySelectorAll('.filter-auto select').forEach(sel => {
  sel.addEventListener('change', () => sel.closest('form').submit());
});
