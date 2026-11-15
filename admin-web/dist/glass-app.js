/* G-Connect Glassmorphism Premium — Advanced Interactions v2.0 */

const icons = {
  home: 'house',
  jobs: 'briefcase-business',
  network: 'users-round',
  school: 'graduation-cap',
  messages: 'message-circle',
  profile: 'circle-user-round',
  settings: 'settings',
  search: 'search',
  menu: 'menu',
  close: 'panel-left-close',
  open: 'panel-left-open',
  bell: 'bell',
  arrow: 'arrow-up-right',
  calendar: 'calendar-days',
  bookmark: 'bookmark',
  check: 'check',
  globe: 'globe-2',
  chevron: 'chevron',
  sun: 'sun',
  moon: 'moon',
  linkedin: 'linkedin',
  github: 'github',
  twitter: 'twitter'
};

const paths = {
  house: 'M3 10.5 12 3l9 7.5V21h-6v-7H9v7H3z',
  'briefcase-business': 'M3 7h18v14H3z M8 7V4h8v3 M3 12h18',
  'users-round': 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M22 21v-2a4 4 0 0 0-3-3.87 M16 3.13a4 4 0 0 1 0 7.75',
  'graduation-cap': 'm2 10 10-5 10 5-10 5z M6 12v5c4 3 8 3 12 0v-5 M22 10v6',
  'message-circle': 'M21 11.5a8.5 8.5 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-5.5a9 9 0 0 1-.9-4A8.5 8.5 0 0 1 12.5 3a8.5 8.5 0 0 1 8.5 8.5z',
  'circle-user-round': 'M20 21a8 8 0 1 0-16 0 M12 13a4 4 0 1 0 0-8 4 4 0 0 0 0 8 M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20',
  settings: 'M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7 M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2 2-.06-.06a1.7 1.7 0 0 0-1.88-.34l-.09.04V21h-3v-.09a1.7 1.7 0 0 0-1.12-1.6 M4.6 9a1.7 1.7 0 0 0-.34-1.88L4.2 7.06l2-2 .06.06a1.7 1.7 0 0 0 1.88.34L8.23 5V3h3v.09 M20 9l.8-1.9-2-2-.1.1',
  search: 'm21 21-4.4-4.4 M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  menu: 'M4 6h16 M4 12h16 M4 18h16',
  'panel-left-close': 'M3 4h18v16H3z M9 4v16 m7-11-3 3 3 3',
  'panel-left-open': 'M3 4h18v16H3z M9 4v16 m4-11 3 3-3 3',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
  'arrow-up-right': 'M7 17 17 7 M7 7h10v10',
  'calendar-days': 'M3 5h18v16H3z M7 3v4 M17 3v4 M3 10h18 M7 14h2 M12 14h2',
  bookmark: 'M5 3h14v18l-7-5-7 5z',
  check: 'M4 12l5 5L20 6',
  'globe-2': 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20 M2 12h20 M12 2c-6 6-6 14 0 20 M12 2c6 6 6 14 0 20',
  chevron: 'M9 18l6-6-6-6',
  sun: 'M12 7v-2 M12 19v2 M4.93 4.93l-1.41 1.41 M18.36 18.36l-1.41 1.41 M7 12H5 M19 12h-2 M4.93 19.07l-1.41-1.41 M18.36 5.64l-1.41-1.41 M12 4a8 8 0 1 0 0 16 8 8 0 0 0 0-16z',
  moon: 'M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z',
  linkedin: 'M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z M2 9h4v12H2z M4 6a2 2 0 1 0 0 4 2 2 0 0 0 0-4z',
  github: 'M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.93 3.58C.94 6.76.64 7.95.64 8.23V19',
  twitter: 'M23 3a10.9 10.9 0 0 1-3.14 1.53 4.48 4.48 0 0 0-7.86 3v1A10.66 10.66 0 0 1 3 4s-4 9 5 13a11.64 11.64 0 0 1-7 2c9 5 20 0 20-11.5a4.5 4.5 0 0 0-.08-.83A7.72 7.72 0 0 0 23 3z'
};

function ico(name, size = 20) {
  const path = paths[icons[name] || name] || paths.house;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${path}"/></svg>`;
}

// Data
const opportunities = [
  { name: 'Stage Développeur Full Stack', company: 'Wave Sénégal', initial: 'W', location: 'Dakar, Sénégal', type: 'Stage', sector: 'Technologie', date: 'Il y a 2 h', color: '#1c2c67' },
  { name: 'Assistant(e) Marketing Digital', company: 'Orange Sénégal', initial: 'O', location: 'Dakar · Hybride', type: 'Stage', sector: 'Marketing', date: 'Il y a 5 h', color: '#ff9b3c' },
  { name: 'Junior Data Analyst', company: 'Sonatel', initial: 'S', location: 'Dakar, Sénégal', type: 'Emploi', sector: 'Data', date: 'Hier', color: '#315bd7' },
  { name: 'UX/UI Designer Junior', company: 'Jokkolabs', initial: 'J', location: 'Dakar · À distance', type: 'Emploi', sector: 'Design', date: 'Il y a 2 j', color: '#254d51' },
  { name: 'Stage Audit & Contrôle', company: 'Cabinet Horizon', initial: 'H', location: 'Dakar, Sénégal', type: 'Stage', sector: 'Finance', date: 'Il y a 3 j', color: '#8264cc' }
];

const people = [
  { name: 'Awa Diop', role: 'Développeuse frontend · Alumni', initial: 'AD' },
  { name: 'Moussa Fall', role: 'Data Analyst · Alumni', initial: 'MF' },
  { name: 'Fatou Ndiaye', role: 'Responsable recrutement', initial: 'FN' },
  { name: 'Ibrahima Ba', role: 'Étudiant en informatique', initial: 'IB' }
];

const schools = [
  { name: 'ISI', full: 'Institut Supérieur d\'Informatique', location: 'Dakar, Sénégal' },
  { name: 'UCAD', full: 'Université Cheikh Anta Diop', location: 'Dakar, Sénégal' },
  { name: 'ESP', full: 'École Supérieure Polytechnique', location: 'Dakar, Sénégal' }
];

const events = [
  { day: '24', month: 'OCT', title: 'Rencontre Alumni', desc: 'Échange autour des métiers du numérique' },
  { day: '07', month: 'NOV', title: 'Forum stages & emplois', desc: 'Entreprises et étudiants réunis' },
  { day: '15', month: 'NOV', title: 'Atelier CV & LinkedIn', desc: 'Valoriser son parcours' }
];

const pages = [
  ['home', 'Accueil'],
  ['jobs', 'Offres'],
  ['network', 'Réseau'],
  ['school', 'Établissements'],
  ['messages', 'Messages'],
  ['profile', 'Mon profil']
];

// State
let view = 'home';
let collapsed = false;
let mobile = false;
let filter = 'Toutes';
let query = '';
let saved = new Set();
let role = 'Étudiant';
let theme = 'light';

// DOM
const app = document.getElementById('app');
let observer = null;
let magneticElements = [];
let reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

// ===== UTILITIES =====
function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({'&':'&','<':'<','>':'>','"':'"',"'":''}[c]));
}

function debounce(fn, ms) {
  let t; return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function throttle(fn, ms) {
  let last = 0; return (...args) => { const now = performance.now(); if (now - last >= ms) { last = now; fn(...args); } };
}

// ===== ANIMATION ENGINE =====
const AnimationEngine = {
  // Ripple effect
  createRipple(event, element) {
    if (reducedMotion) return;
    const rect = element.getBoundingClientRect();
    const ripple = document.createElement('span');
    ripple.className = 'ripple';
    const size = Math.max(rect.width, rect.height);
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
    element.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
  },

  // Magnetic button
  initMagnetic(element) {
    if (reducedMotion) return;
    element.addEventListener('mousemove', (e) => {
      const rect = element.getBoundingClientRect();
      const x = e.clientX - rect.left - rect.width / 2;
      const y = e.clientY - rect.top - rect.height / 2;
      element.style.setProperty('--pointer-x', `${x}px`);
      element.style.setProperty('--pointer-y', `${y}px`);
    });
    element.addEventListener('mouseleave', () => {
      element.style.transform = '';
    });
    element.addEventListener('mousedown', () => {
      element.style.transform = 'scale(0.97)';
    });
    element.addEventListener('mouseup', () => {
      element.style.transform = '';
    });
  },

  // Scroll reveal
  initScrollReveal() {
    if (reducedMotion) {
      document.querySelectorAll('.reveal').forEach(el => el.classList.add('visible'));
      return;
    }
    observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  },

  // Staggered entrance
  staggerEntrance(container, selector = '.stagger-children > *') {
    if (reducedMotion) return;
    const items = container.querySelectorAll(selector);
    items.forEach((item, i) => {
      item.style.animationDelay = `${Math.min(i, 5) * 30}ms`;
    });
  },

  // Parallax on scroll
  initParallax() {
    if (reducedMotion) return;
    const elements = document.querySelectorAll('[data-parallax]');
    const handleScroll = throttle(() => {
      const scrolled = window.scrollY;
      elements.forEach(el => {
        const speed = parseFloat(el.dataset.parallax) || 0.3;
        const y = scrolled * speed;
        el.style.transform = `translateY(${y}px)`;
      });
    }, 16);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  },

  // Floating animation for ambient elements
  initAmbient() {
    if (reducedMotion) return;
    const glows = document.querySelectorAll('.ambient-glow');
    glows.forEach((glow, i) => {
      glow.style.animationDelay = `${-i * 7}s`;
    });
  },

  // Particle system
  createParticles(container, count = 12) {
    if (reducedMotion) return;
    for (let i = 0; i < count; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      particle.style.left = `${Math.random() * 100}%`;
      particle.style.animationDelay = `${Math.random() * 8}s`;
      particle.style.animationDuration = `${6 + Math.random() * 4}s`;
      const size = 2 + Math.random() * 4;
      particle.style.width = particle.style.height = `${size}px`;
      container.appendChild(particle);
    }
  }
};

// ===== TOAST SYSTEM =====
function notify(message, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => toast.classList.add('visible'));

  setTimeout(() => {
    toast.classList.add('removing');
    toast.addEventListener('animationend', () => toast.remove());
  }, 3000);
}

// ===== RENDER FUNCTIONS =====
function renderSidebar() {
  return `
    <aside class="sidebar" id="primary-navigation" aria-label="Navigation principale">
      <div class="brand">
        <img class="full-logo" src="/assets/logo.png" alt="G-Connect">
        <img class="compact-logo" src="/assets/logo_icon.png" alt="G">
        <button class="icon-btn collapse-trigger" id="collapse" aria-controls="primary-navigation" aria-expanded="${!collapsed}" title="Réduire ou déployer la navigation">
          ${ico('chevron')}
        </button>
      </div>
      <div class="searchbox">
        <button id="search-trigger" aria-label="Rechercher">${ico('search')}</button>
        <input id="side-search" placeholder="Rechercher..." value="${escapeHTML(query)}" aria-label="Rechercher sur G-Connect">
      </div>
      <div class="nav-label">Menu principal</div>
      <nav class="nav">
        ${pages.map(([key, label]) => `
          <button class="nav-btn ${view === key ? 'active' : ''}" data-page="${key}" title="${label}">
            ${ico(key)}
            <span>${label}</span>
          </button>
        `).join('')}
      </nav>
      <div class="side-bottom">
        <div class="nav-label">Compte</div>
        <button class="nav-btn ${view === 'settings' ? 'active' : ''}" data-page="settings" title="Paramètres">
          ${ico('settings')}<span>Paramètres</span>
        </button>
        <div class="profile-small">
          <div class="avatar">TT</div>
          <div>
            <strong>Mon espace G-Connect</strong>
            <small>Compte de démonstration</small>
          </div>
        </div>
      </div>
    </aside>
  `;
}

function renderTopbar() {
  const currentPage = [...pages, ['settings', 'Paramètres']].find(p => p[0] === view) || pages[0];
  return `
    <header class="topbar">
      <div style="display:flex;align-items:center;gap:10px">
        <button class="icon-btn mobile-toggle" id="mobile-menu" aria-controls="primary-navigation" aria-expanded="${mobile}" aria-label="Ouvrir le menu">
          ${ico('menu', 22)}
        </button>
        <img class="mobile-brand" src="/assets/logo.png" alt="G-Connect">
        <div class="breadcrumb">G-Connect &nbsp; / &nbsp; <b>${currentPage[1]}</b></div>
      </div>
      <div class="top-actions"><a href="/auth.html" class="btn primary">Connexion</a>
        <button class="round" id="notifications" title="Notifications">${ico('bell')}</button>
        <div class="member-pill" data-page="profile" role="button" tabindex="0">
          <div class="avatar">TT</div>
          <span>Mon espace</span>
        </div>
      </div>
    </header>
  `;
}

function renderHero() {
  return `
    <section class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <span class="eyebrow">Bienvenue dans votre communauté</span>
        <h1 id="hero-title">Votre réseau aujourd’hui.<br>Vos opportunités demain.</h1>
        <p>Rencontrez les bonnes personnes, explorez les offres qui vous correspondent et avancez avec votre communauté académique.</p>
        <div class="actions">
          <button class="btn primary magnetic" data-page="jobs">Explorer les offres ${ico('arrow', 16)}</button>
          <button class="btn outline magnetic" data-page="network">Découvrir le réseau</button>
        </div>
      </div>
      <img class="hero-photo" src="/assets/hero-gconnect.jpg" alt="Un jeune professionnel noir avec son ordinateur, en extérieur" width="800" height="900" fetchpriority="high">
      <div class="hero-overlay"></div>
    </section>
  `;
}

function renderOpportunity(o, i) {
  const isSaved = saved.has(i);
  return `
    <article class="op-card reveal reveal-delay-${(i % 6) + 1}">
      <div class="op-card-header">
        <div class="company-badge" style="background: linear-gradient(135deg, ${o.color}, ${adjustColor(o.color, 30)})">${o.initial}</div>
        <div class="op-main">
          <h3>${escapeHTML(o.name)}</h3>
          <div class="op-meta">
            <span>${escapeHTML(o.company)}</span>
            <span>${escapeHTML(o.location)}</span>
            <span>${escapeHTML(o.date)}</span>
          </div>
          <div class="op-tags">
            <span class="tag">${escapeHTML(o.type)}</span>
            <span class="tag green">${escapeHTML(o.sector)}</span>
          </div>
        </div>
      </div>
      <div class="op-footer">
        <span style="font-size:12px;color:var(--ink-subtle)">${isSaved ? '✓ Enregistré' : ''}</span>
        <button class="apply-btn ${isSaved ? 'saved' : ''}" data-save="${i}" aria-label="${isSaved ? 'Retirer des favoris' : 'Sauvegarder l\'offre'}">
          ${isSaved ? 'Enregistré ✓' : 'Sauvegarder'}
        </button>
      </div>
    </article>
  `;
}

function adjustColor(hex, amount) {
  const num = parseInt(hex.replace('#', ''), 16);
  const r = Math.min(255, Math.max(0, (num >> 16) + amount));
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0xFF) + amount));
  const b = Math.min(255, Math.max(0, (num & 0xFF) + amount));
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}

function renderHome() {
  return `
    <div class="page">
      ${renderHero()}
      <p class="demo-note">Espace de démonstration · Offres, profils et événements présentés à titre d’exemple.</p>
      <div class="dash-grid">
        <div>
          <div class="section-head">
            <div>
              <h2>Opportunités à la une</h2>
              <p>Une sélection pour commencer votre parcours</p>
            </div>
            <button class="text-link" data-page="jobs">Voir toutes les offres ${ico('chevron', 16)}</button>
          </div>
          <div class="op-list stagger-children">
            ${opportunities.slice(0, 3).map(renderOpportunity).join('')}
          </div>
        </div>
        <div>
          <div class="section-head">
            <div><h2>À ne pas manquer</h2><p>Les prochains rendez-vous</p></div>
          </div>
          <div class="panel reveal reveal-delay-1">
            <h3>Événements du réseau</h3>
            ${events.map(e => `
              <div class="event">
                <div class="date-tile"><strong>${e.day}</strong><small>${e.month}</small></div>
                <div><b>${escapeHTML(e.title)}</b><p>${escapeHTML(e.desc)}</p></div>
              </div>
            `).join('')}
            <button class="text-link" data-page="school">Explorer les établissements ${ico('chevron', 16)}</button>
          </div>
        </div>
      </div>
      <div class="wide-banner reveal reveal-delay-2">
        <div>
          <h3>Votre parcours mérite d’être vu.</h3>
          <p>Complétez votre profil pour vous présenter à votre communauté.</p>
        </div>
        <button class="btn primary magnetic" data-page="profile">Compléter mon profil ${ico('arrow', 16)}</button>
      </div>
    </div>
  `;
}

function renderJobs() {
  const items = opportunities.filter(o =>
    (filter === 'Toutes' || o.type === filter) &&
    [o.name, o.company, o.sector].join(' ').toLowerCase().includes(query.toLowerCase())
  );

  return `
    <div class="page">
      <div class="intro reveal">
        <span class="eyebrow">Carrière & opportunités</span>
        <h1>Trouvez votre prochaine opportunité.</h1>
        <p>Explorez les offres proposées par les entreprises de notre réseau.</p>
      </div>
      <div class="search-large reveal reveal-delay-1">
        ${ico('search')}
        <input id="big-search" aria-label="Rechercher une offre" placeholder="Rechercher un poste, une entreprise, un domaine..." value="${escapeHTML(query)}">
      </div>
      <div class="filters reveal reveal-delay-2">
        ${['Toutes', 'Stage', 'Emploi'].map(f => `
          <button class="chip ${filter === f ? 'active' : ''}" data-filter="${f}">${f}</button>
        `).join('')}
      </div>
      <div class="op-list stagger-children">
        ${items.length ? items.map((o, idx) => renderOpportunity(o, opportunities.indexOf(o))).join('') : `
          <div class="empty reveal">
            ${ico('briefcase-business', 48)}
            <h3>Aucun résultat</h3>
            <p>Essayez un autre mot-clé ou changez de filtre.</p>
          </div>
        `}
      </div>
    </div>
  `;
}

function renderNetwork() {
  return `
    <div class="page">
      <div class="intro reveal">
        <span class="eyebrow">Une communauté, des connexions</span>
        <h1>Grandissez ensemble.</h1>
        <p>Découvrez des profils et développez votre réseau professionnel.</p>
      </div>
      <div class="section-head reveal reveal-delay-1">
        <h2>Membres à découvrir</h2>
      </div>
      <div class="cards-grid stagger-children">
        ${people.map(p => `
          <article class="people-card reveal">
            <div class="avatar">${p.initial}</div>
            <h3>${escapeHTML(p.name)}</h3>
            <p>${escapeHTML(p.role)}</p>
            <button class="btn primary magnetic invite">Se connecter</button>
          </article>
        `).join('')}
      </div>
    </div>
  `;
}

function renderSchools() {
  return `
    <div class="page">
      <div class="intro reveal">
        <span class="eyebrow">Écoles et universités</span>
        <h1>Votre communauté académique.</h1>
        <p>Retrouvez votre établissement et développez vos liens avec les promotions.</p>
      </div>
      <div class="cards-grid stagger-children" style="margin-top:24px">
        ${schools.map(s => `
          <article class="people-card reveal">
            <div class="avatar">${s.name[0]}</div>
            <h3>${escapeHTML(s.full)}</h3>
            <p>${escapeHTML(s.location)}</p>
            <button class="btn primary magnetic join">Découvrir</button>
          </article>
        `).join('')}
      </div>
    </div>
  `;
}

function renderMessages() {
  return `
    <div class="page">
      <div class="intro reveal">
        <span class="eyebrow">Conversations</span>
        <h1>Messages</h1>
        <p>Échangez avec votre réseau et vos contacts.</p>
      </div>
      <div class="panel reveal reveal-delay-1" style="margin-top:24px">
        <div class="empty">
          ${ico('message-circle', 48)}
          <h3>Aucune conversation pour le moment</h3>
          <p>La messagerie sera activée après l’intégration de l’authentification et du backend.</p>
          <button class="btn primary magnetic" data-page="network">Explorer le réseau</button>
        </div>
      </div>
    </div>
  `;
}

function renderProfile() {
  return `
    <div class="page">
      <div class="intro reveal">
        <span class="eyebrow">Mon identité professionnelle</span>
        <h1>Votre profil G-Connect</h1>
        <p>Présentez votre parcours et vos ambitions à votre communauté.</p>
      </div>
      <div class="auth-panel reveal reveal-delay-1">
        <div style="display:flex;align-items:center;gap:15px;margin-bottom:30px">
          <div class="avatar" style="width:68px;height:68px;font-size:22px">TT</div>
          <div>
            <h2 style="margin:0">Bienvenue sur G-Connect</h2>
            <p style="font-size:12px;color:#8896b0">Configurez votre futur profil</p>
          </div>
        </div>
        <div class="form-field">
          <label for="profile-name">Nom complet</label>
          <input id="profile-name" placeholder="Votre nom et prénom">
        </div>
        <div class="form-field">
          <label for="role">Type de profil</label>
          <select id="role">
            ${['Étudiant', 'Alumni', 'Entreprise', 'Établissement'].map(r => `<option ${role === r ? 'selected' : ''}>${r}</option>`).join('')}
          </select>
        </div>
        <div class="form-field">
          <label for="profile-bio">Votre présentation</label>
          <input id="profile-bio" placeholder="Votre filière, poste ou domaine">
        </div>
        <button class="btn primary magnetic preview-only" style="width:100%">Enregistrer mon profil ${ico('arrow', 16)}</button>
        <p class="fine">Aperçu frontend : l’enregistrement réel sera disponible après connexion à l’API.</p>
      </div>
    </div>
  `;
}

function renderSettings() {
  return `
    <div class="page">
      <div class="intro reveal">
        <h1>Préférences</h1>
        <p>Personnalisez votre expérience.</p>
      </div>
      <div class="panel reveal reveal-delay-1" style="margin-top:24px">
        <h3>Navigation</h3>
        <p style="color:var(--ink-muted);font-size:13px">Vous pouvez réduire ou déployer la barre latérale avec le bouton situé en haut de celle-ci.</p>
        <button class="btn primary magnetic" id="toggle-settings" style="margin-top:16px">Basculer la sidebar ${ico(collapsed ? 'open' : 'close', 16)}</button>
      </div>
      <div class="panel reveal reveal-delay-2" style="margin-top:24px">
        <h3>Thème</h3>
        <p style="color:var(--ink-muted);font-size:13px">Choisissez votre apparence préférée.</p>
        <div style="display:flex;gap:12px;margin-top:16px;flex-wrap:wrap">
          <button class="btn ${theme === 'light' ? 'primary' : 'outline'}" data-theme="light" style="min-width:140px">${ico('sun', 16)} Clair</button>
          <button class="btn ${theme === 'dark' ? 'primary' : 'outline'}" data-theme="dark" style="min-width:140px">${ico('moon', 16)} Sombre</button>
          <button class="btn outline" data-theme="system" style="min-width:140px">${ico('globe', 16)} Système</button>
        </div>
      </div>
      <div class="panel reveal reveal-delay-3" style="margin-top:24px">
        <h3>Animations</h3>
        <p style="color:var(--ink-muted);font-size:13px">Contrôlez les effets visuels.</p>
        <label style="display:flex;align-items:center;gap:12px;margin-top:16px;cursor:pointer">
          <input type="checkbox" id="reduce-motion" ${reducedMotion ? 'checked' : ''} style="width:20px;height:20px;accent-color:var(--brand)">
          <span>Réduire les animations (préférence système: ${window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'Oui' : 'Non'})</span>
        </label>
      </div>
    </div>
  `;
}

// ===== RENDER ORCHESTRATOR =====
function render() {
  observer?.disconnect();
  document.documentElement.dataset.reducedMotion = String(reducedMotion);
  const contentRenderers = {
    home: renderHome,
    jobs: renderJobs,
    network: renderNetwork,
    school: renderSchools,
    messages: renderMessages,
    profile: renderProfile,
    settings: renderSettings
  };

  const content = contentRenderers[view]?.() || renderHome();

  app.innerHTML = `
    <a class="skip-link" href="#main-content">Aller au contenu</a>
    <div class="ambient-bg" aria-hidden="true">
      <div class="ambient-glow"></div>
      <div class="ambient-glow"></div>
      <div class="ambient-glow"></div>
      <div class="particles" id="particles"></div>
    </div>
    <div class="shell ${collapsed ? 'collapsed' : ''} ${mobile ? 'mobile-open' : ''}">
      <div class="mobile-backdrop" id="backdrop"></div>
      ${renderSidebar()}
      <main class="content" id="main-content" tabindex="-1">
        ${renderTopbar()}
        ${content}
      </main>
    </div>
  `;

  document.title = ([...pages, ['settings', 'Paramètres']].find(p => p[0] === view) || pages[0])[1] + ' · G-Connect';

  // Initialize animations after render
  requestAnimationFrame(() => {
    initInteractions();
    AnimationEngine.initScrollReveal();
    AnimationEngine.initAmbient();
    AnimationEngine.createParticles(document.getElementById('particles'), 15);
    AnimationEngine.initParallax();

    // Stagger entrance for visible elements
    document.querySelectorAll('.stagger-children').forEach(container => {
      AnimationEngine.staggerEntrance(container);
    });
  });
}

// ===== INTERACTION BINDING =====
function initInteractions() {
  const shell = document.querySelector('.shell');

  // Navigation
  document.querySelectorAll('[data-page]').forEach(el => {
    el.onclick = () => {
      navigate(el.dataset.page);
      // Add ripple
      if (el.classList.contains('btn') || el.classList.contains('apply-btn') || el.classList.contains('chip')) {
        AnimationEngine.createRipple({ clientX: el.getBoundingClientRect().left + el.offsetWidth/2, clientY: el.getBoundingClientRect().top + el.offsetHeight/2 }, el);
      }
    };
  });

  document.querySelector('.member-pill')?.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('profile'); }
  });

  // Collapse sidebar
  const collapseBtn = document.getElementById('collapse');
  if (collapseBtn) {
    collapseBtn.onclick = () => {
      if (window.innerWidth <= 900) {
        mobile = false;
      } else {
        collapsed = !collapsed;
      }
      updateNavigation();
    };
  }

  // Mobile menu
  const mobileMenu = document.getElementById('mobile-menu');
  if (mobileMenu) {
    mobileMenu.onclick = () => {
      mobile = true;
      updateNavigation();
    };
  }

  // Backdrop
  const backdrop = document.getElementById('backdrop');
  if (backdrop) {
    backdrop.onclick = () => {
      mobile = false;
      updateNavigation();
    };
  }

  // Search trigger
  const searchTrigger = document.getElementById('search-trigger');
  const sideSearch = document.getElementById('side-search');
  if (searchTrigger && sideSearch) {
    searchTrigger.onclick = () => {
      if (collapsed) {
        collapsed = false;
        updateNavigation();
      }
      sideSearch.focus();
    };
    sideSearch.onkeydown = (e) => {
      if (e.key === 'Enter') {
        query = sideSearch.value;
        view = 'jobs';
        mobile = false;
        render();
        requestAnimationFrame(() => {
          const bigSearch = document.getElementById('big-search');
          if (bigSearch) bigSearch.focus();
        });
      }
    };
  }

  // Save/unsave opportunities
  document.querySelectorAll('[data-save]').forEach(el => {
    el.onclick = (e) => {
      e.stopPropagation();
      const i = +el.dataset.save;
      saved.has(i) ? saved.delete(i) : saved.add(i);
      notify(saved.has(i) ? 'Offre ajoutée aux favoris' : 'Offre retirée des favoris');
      render();
    };
  });

  // Filters
  document.querySelectorAll('[data-filter]').forEach(el => {
    el.onclick = () => {
      filter = el.dataset.filter;
      render();
    };
  });

  // Large search
  const bigSearch = document.getElementById('big-search');
  if (bigSearch) {
    let searchDebounce = debounce(() => {
      query = bigSearch.value;
      render();
    }, 150);
    bigSearch.oninput = () => {
      const pos = bigSearch.selectionStart;
      searchDebounce();
      requestAnimationFrame(() => {
        const newSearch = document.getElementById('big-search');
        if (newSearch) {
          newSearch.focus();
          newSearch.setSelectionRange(pos, pos);
        }
      });
    };
  }

  // Notification button
  const notifBtn = document.getElementById('notifications');
  if (notifBtn) {
    notifBtn.onclick = () => notify('Aucune nouvelle notification');
  }

  // Role select
  const roleSelect = document.getElementById('role');
  if (roleSelect) {
    roleSelect.onchange = () => { role = roleSelect.value; };
  }

  // Theme toggle
  document.querySelectorAll('button[data-theme]').forEach(btn => {
    btn.onclick = () => {
      theme = btn.dataset.theme;
      applyTheme();
      render();
    };
  });

  // Reduce motion toggle
  const reduceMotion = document.getElementById('reduce-motion');
  if (reduceMotion) {
    reduceMotion.onchange = () => {
      reducedMotion = reduceMotion.checked;
      document.documentElement.style.setProperty('--duration-entrance', reducedMotion ? '0ms' : '280ms');
      render();
    };
  }

  // Toggle sidebar from settings
  const toggleSettings = document.getElementById('toggle-settings');
  if (toggleSettings) {
    toggleSettings.onclick = () => {
      if (window.innerWidth <= 900) {
        mobile = !mobile;
      } else {
        collapsed = !collapsed;
      }
      updateNavigation();
      render();
    };
  }

  // Magnetic buttons
  document.querySelectorAll('.btn.magnetic').forEach(btn => {
    AnimationEngine.initMagnetic(btn);
  });

  // Ripple on all buttons
  document.querySelectorAll('.btn, .apply-btn, .chip, .round, .nav-btn, .text-link').forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (!reducedMotion && (btn.classList.contains('btn') || btn.classList.contains('apply-btn') || btn.classList.contains('chip'))) {
        AnimationEngine.createRipple(e, btn);
      }
    });
  });

  // Keyboard navigation
  document.addEventListener('keydown', handleKeydown);
}

function handleKeydown(e) {
  if (e.key === 'Escape' && mobile) {
    mobile = false;
    updateNavigation();
    document.getElementById('mobile-menu')?.focus();
  }
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault();
    const search = document.getElementById('side-search') || document.getElementById('big-search');
    if (search) {
      if (collapsed) { collapsed = false; updateNavigation(); }
      search.focus();
    }
  }
}

function updateNavigation() {
  const shell = document.querySelector('.shell');
  if (!shell) return;
  shell.classList.toggle('collapsed', collapsed);
  shell.classList.toggle('mobile-open', mobile);
  const collapseBtn = document.getElementById('collapse');
  const mobileMenu = document.getElementById('mobile-menu');
  if (collapseBtn) collapseBtn.setAttribute('aria-expanded', String(!collapsed));
  if (mobileMenu) mobileMenu.setAttribute('aria-expanded', String(mobile));
}

function navigate(v) {
  view = v;
  query = '';
  mobile = false;
  render();
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  window.scrollTo({ top: 0, behavior: prefersReduced ? 'instant' : 'smooth' });
}

function applyTheme() {
  const root = document.documentElement;
  root.setAttribute('data-theme', theme === 'system'
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : theme);
}

// ===== INIT =====
function init() {
  // Check system preference
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Listen for theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (theme === 'system') {
      applyTheme();
    }
  });

  // Listen for reduced motion changes
  window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
    reducedMotion = e.matches;
    render();
  });

  // Initial render
  applyTheme();
  render();
}

// Start when DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Export for testing
window.GConnect = { navigate, notify, render, initInteractions, AnimationEngine };