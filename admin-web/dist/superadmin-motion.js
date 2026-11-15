'use strict';
// E8 — Transitions Établissement (600/480/180ms) étendues à toute la console.
// Scroll, cartes, chiffres, navigation, graphiques, survols et feedback tactile.
// Independent preview only: this module does not read or change API sessions.
window.SuperadminMotion = (() => {
  let observer, frame = 0, countFrame = 0, root;
  const reduced = () => document.documentElement.dataset.motion === 'off'
    || (document.documentElement.dataset.motion !== 'on'
      && (document.documentElement.dataset.reducedMotion === 'true'
        || window.matchMedia('(prefers-reduced-motion: reduce)').matches));
  const buttons = '.action,.smallbtn,.icon-btn,.nav-btn,.quick,.switch,.collapse-toggle,.command-link,.inline-link,.e36-refresh,.e36-row-action,.e36-pager button,.e36-dialog-actions button';

  function createRipple(event, element) {
    if (reduced() || element.disabled) return;
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const ripple = document.createElement('span');
    ripple.className = 'sa-ripple';
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${(event.detail ? event.clientX - rect.left : rect.width / 2) - size / 2}px`;
    ripple.style.top = `${(event.detail ? event.clientY - rect.top : rect.height / 2) - size / 2}px`;
    element.append(ripple);
    let host;
    ripple.addEventListener('animationend', () => { ripple.remove(); host?.remove(); }, {once:true});
    const radius = getComputedStyle(element).borderRadius;
    queueMicrotask(() => {
      // Navigating between pages replaces the clicked button immediately.
      if (ripple.isConnected || reduced()) return;
      host = document.createElement('div');
      host.className = 'sa-ripple-host' + (element.classList.contains('action') ? ' primary' : '');
      host.setAttribute('aria-hidden', 'true');
      Object.assign(host.style, {
        left:`${rect.left}px`, top:`${rect.top}px`, width:`${rect.width}px`,
        height:`${rect.height}px`, borderRadius:radius,
      });
      host.append(ripple);
      root.append(host);
    });
  }

  function initMagnetic(event) {
    const element = event.target.closest('.sa-magnetic');
    if (!element || reduced() || event.pointerType === 'touch') return;
    const rect = element.getBoundingClientRect();
    element.style.setProperty('--pointer-x', `${event.clientX - rect.left - rect.width / 2}px`);
    element.style.setProperty('--pointer-y', `${event.clientY - rect.top - rect.height / 2}px`);
  }

  function initScrollReveal(main) {
    observer?.disconnect();
    // Cards and inner rows across all screens: sessions, audit, organisations,
    // moderation, imports and billing share the Establishment reveal cadence.
    const items = main.querySelectorAll('.panel,.page-head,.notice,.overview-title,.import-tile,.kpi,.queue-item,.quick,.table tbody tr,.field,.empty-state,.switch,.billing-tier,.billing-step,.billing-head,.billing-placeholder,.command-link,.e36-metric,.e36-panel,.e36-checkline,.e36-table tbody tr,.e36-state');
    items.forEach((element, i) => {
      element.classList.add('sa-reveal');
      element.style.setProperty('--sa-delay', `${(i % 6) * 30}ms`);
      if (reduced()) element.classList.add('is-visible');
    });
    if (reduced() || typeof IntersectionObserver !== 'function') {
      items.forEach(element => element.classList.add('is-visible'));
      return;
    }
    observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    }), {threshold:0.1, rootMargin:'0px 0px -50px 0px'});
    items.forEach(element => {
      if (!element.classList.contains('is-visible')) observer.observe(element);
    });
  }

  function staggerEntrance(main) {
    main.querySelectorAll('.hero-content > *,.form > *,.page-head > *').forEach(element => {
      element.classList.add('sa-entrance');
      element.style.animationDelay = `${Math.min([...element.parentElement.children].indexOf(element), 5) * 30}ms`;
    });
  }

  function initParallax() {
    if (frame || reduced()) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      root.querySelectorAll('[data-parallax]').forEach(element => {
        element.style.transform = `translateY(${window.scrollY * (parseFloat(element.dataset.parallax) || 0.3)}px)`;
      });
    });
  }

  function createParticles(container, count = 15) {
    if (!container || container.children.length || reduced()) return;
    for (let i = 0; i < count; i++) {
      const particle = document.createElement('span');
      particle.className = 'sa-particle';
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.animationDelay = `${Math.random() * 8}s`;
      particle.style.animationDuration = `${6 + Math.random() * 4}s`;
      particle.style.width = particle.style.height = `${2 + Math.random() * 4}px`;
      container.append(particle);
    }
  }

  function initAmbient() {
    root.querySelectorAll('.ambient-glow').forEach((glow, i) => {
      glow.style.animationDelay = `${-i * 7}s`;
    });
    root.querySelectorAll('.particles').forEach(container => {
      if (reduced()) container.replaceChildren();
      else createParticles(container);
    });
  }

  function animateKpis(main) {
    cancelAnimationFrame(countFrame);
    countFrame = 0;
    const entries = [...main.querySelectorAll('.kpi strong,.e36-metric > strong')].map(node => {
      const original = node.textContent.trim();
      if (!/^\d[\d\s\u00a0\u202f]*$/.test(original)) return null;
      const total = Number(original.replace(/\s/g, ''));
      return Number.isFinite(total) && total > 0 ? {node, total, original} : null;
    }).filter(Boolean);
    if (reduced() || !entries.length) return;
    const started = performance.now();
    const format = new Intl.NumberFormat('fr-FR');
    const step = now => {
      const progress = Math.min(1, (now - started) / 850);
      const eased = 1 - (1 - progress) ** 3;
      entries.forEach(({node,total,original}) => {
        if (!node.isConnected) return;
        node.textContent = progress === 1 ? original : format.format(Math.round(eased * total));
      });
      countFrame = progress < 1 ? requestAnimationFrame(step) : 0;
    };
    countFrame = requestAnimationFrame(step);
  }

  function afterRender() {
    if (!root) return;
    const main = root.querySelector('#view');
    main.querySelectorAll('.hero-content .action,.quick,.form .action,.command-link').forEach(element => {
      element.classList.add('sa-magnetic');
    });
    staggerEntrance(main);
    initScrollReveal(main);
    initAmbient();
    animateKpis(main);
  }

  function preferenceChanged() {
    if (!root) return;
    cancelAnimationFrame(frame);
    frame = 0;
    cancelAnimationFrame(countFrame);
    countFrame = 0;
    root.querySelectorAll('.sa-ripple,.sa-ripple-host').forEach(element => element.remove());
    root.querySelectorAll('[data-parallax]').forEach(element => { element.style.transform = ''; });
    initScrollReveal(root.querySelector('#view'));
    initAmbient();
  }

  function init(element) {
    if (root) return;
    root = element;
    root.addEventListener('click', event => {
      const button = event.target.closest(buttons);
      if (button) createRipple(event, button);
    }, true);
    root.addEventListener('pointermove', initMagnetic, {passive:true});
    window.addEventListener('scroll', initParallax, {passive:true});
    afterRender();
  }

  return {init, afterRender, preferenceChanged};
})();
document.addEventListener('DOMContentLoaded', () => {
  window.SuperadminMotion.init(document.body);
});
