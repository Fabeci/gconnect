'use strict';
// Adapted from glass-app.js AnimationEngine. No student application state or handlers.
window.EstablishmentMotion = (() => {
  let observer, frame = 0, root;
  const reduced = () => document.documentElement.dataset.reducedMotion === 'true';
  const buttons = '.ea-button,.ea-icon-button,.ea-nav-item,.ea-step,.ea-text-button,.ea-plan';
  function createRipple(event, element) {
    if (reduced() || element.disabled) return;
    const rect = element.getBoundingClientRect(), size = Math.max(rect.width, rect.height);
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${(event.detail ? event.clientX - rect.left : rect.width / 2) - size / 2}px`;
    ripple.style.top = `${(event.detail ? event.clientY - rect.top : rect.height / 2) - size / 2}px`;
    element.append(ripple);
    let host;
    ripple.addEventListener('animationend', () => {ripple.remove();host?.remove();}, {once:true});
    // A route/form action may replace its button immediately. Keep that click's
    // feedback at its original position until the 500ms ripple finishes.
    const radius = getComputedStyle(element).borderRadius;
    queueMicrotask(() => {
      if (ripple.isConnected || reduced()) return;
      host = document.createElement('div');
      host.className = 'ea-ripple-host' + (element.classList.contains('primary') ? ' primary' : '');
      host.setAttribute('aria-hidden', 'true');
      Object.assign(host.style, {left:`${rect.left}px`, top:`${rect.top}px`, width:`${rect.width}px`, height:`${rect.height}px`, borderRadius:radius});
      host.append(ripple); root.append(host);
    });
  }
  function initMagnetic(event) {
    const element = event.target.closest('.ea-magnetic');
    if (!element || reduced() || event.pointerType === 'touch') return;
    const rect = element.getBoundingClientRect();
    // Same pointer coordinates as the reference (which does not translate on hover).
    element.style.setProperty('--pointer-x', `${event.clientX - rect.left - rect.width / 2}px`);
    element.style.setProperty('--pointer-y', `${event.clientY - rect.top - rect.height / 2}px`);
  }
  function initScrollReveal(main) {
    observer?.disconnect();
    const items = main.querySelectorAll('.ea-card,.ea-role,.ea-plan,.ea-settings-stack > .panel,.ea-feature-row,.ea-page-head,.ea-filter-bar');
    items.forEach((el, i) => {
      el.classList.add('ea-reveal');
      el.style.setProperty('--ea-delay', `${(i % 6) * 30}ms`);
      if (reduced()) el.classList.add('is-visible');
    });
    if (reduced()) return;
    observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    }), {threshold:0.1, rootMargin:'0px 0px -50px 0px'});
    items.forEach(el => { if (!el.classList.contains('is-visible')) observer.observe(el); });
  }
  function staggerEntrance(main) {
    main.querySelectorAll('.hero-copy > *,.ea-form > *').forEach(el => {
      el.classList.add('ea-entrance');
      el.style.animationDelay = `${Math.min([...el.parentElement.children].indexOf(el), 5) * 30}ms`;
    });
  }
  function initParallax() {
    if (frame || reduced()) return;
    frame = requestAnimationFrame(() => {
      frame = 0;
      root.querySelectorAll('[data-parallax]').forEach(el => {
        el.style.transform = `translateY(${window.scrollY * (parseFloat(el.dataset.parallax) || 0.3)}px)`;
      });
    });
  }
  function initAmbient() {
    root.querySelectorAll('.ambient-glow').forEach((glow, i) => {glow.style.animationDelay = `${-i * 7}s`;});
    const container = root.querySelector('.particles');
    if (reduced()) {container.replaceChildren(); return;}
    createParticles(container);
  }
  function createParticles(container, count = 15) {
    if (container.children.length || reduced()) return;
    for (let i = 0; i < count; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.animationDelay = `${Math.random() * 8}s`;
      particle.style.animationDuration = `${6 + Math.random() * 4}s`;
      particle.style.width = particle.style.height = `${2 + Math.random() * 4}px`;
      container.append(particle);
    }
  }
  function afterRender() {
    const main = root.querySelector('.ea-main');
    main.querySelectorAll('.ea-actions .ea-button,.ea-feature-row .ea-button').forEach(el => el.classList.add('ea-magnetic'));
    staggerEntrance(main);
    initScrollReveal(main);
    initAmbient();
  }
  function preferenceChanged() {
    if (!root) return;
    cancelAnimationFrame(frame); frame = 0;
    root.querySelectorAll('.ripple,.ea-ripple-host').forEach(el => el.remove());
    root.querySelectorAll('[data-parallax]').forEach(el => {el.style.transform = '';});
    initScrollReveal(root.querySelector('.ea-main'));
    initAmbient();
  }
  function init(element) {
    if (root) return;
    root = element;
    // Delegation is registered once; rerenders only replace the observer's targets.
    root.addEventListener('click', event => {
      const button = event.target.closest(buttons);
      if (button) createRipple(event, button);
    }, true);
    root.addEventListener('pointermove', initMagnetic, {passive:true});
    window.addEventListener('scroll', initParallax, {passive:true});
  }
  return {init, afterRender, preferenceChanged};
})();
