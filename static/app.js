/**
 * NetBill Assist - Core Frontend Script
 * Handles theme, toasts, modal, responsive drawer, and LLM mode sync.
 */

// Theme Management
const Theme = {
  get() {
    try {
      return localStorage.getItem('netbill_theme') || 'light';
    } catch {
      return 'light';
    }
  },
  set(mode) {
    try {
      localStorage.setItem('netbill_theme', mode);
    } catch {}
    if (mode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  },
  toggle() {
    const next = this.get() === 'dark' ? 'light' : 'dark';
    this.set(next);
  },
  init() {
    this.set(this.get());
  }
};

// Immediate theme execution to prevent flash
Theme.init();

// Toast Notification System
const Toast = {
  container: null,
  init() {
    this.container = document.getElementById('toast-container');
  },
  show(title, message = '', variant = 'info') {
    if (!this.container) this.init();
    if (!this.container) return;

    const el = document.createElement('div');
    el.className = `flex items-start gap-3 p-4 rounded-xl shadow-lg border text-sm transition-all duration-300 transform translate-y-2 opacity-0 max-w-sm pointer-events-auto ${
      variant === 'success'
        ? 'bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-950/80 dark:border-emerald-800 dark:text-emerald-200'
        : variant === 'error'
        ? 'bg-rose-50 border-rose-200 text-rose-900 dark:bg-rose-950/80 dark:border-rose-800 dark:text-rose-200'
        : 'bg-white border-slate-200 text-slate-800 dark:bg-slate-900 dark:border-slate-800 dark:text-slate-100'
    }`;

    const iconMap = {
      success: 'check-circle',
      error: 'alert-circle',
      info: 'info'
    };

    el.innerHTML = `
      <i data-lucide="${iconMap[variant] || 'info'}" class="w-5 h-5 shrink-0 mt-0.5 ${
        variant === 'success' ? 'text-emerald-500' : variant === 'error' ? 'text-rose-500' : 'text-amber-500'
      }"></i>
      <div class="flex-1 min-w-0">
        <p class="font-semibold text-xs uppercase tracking-wider">${title}</p>
        ${message ? `<p class="mt-0.5 text-xs opacity-90">${message}</p>` : ''}
      </div>
      <button type="button" aria-label="Close notification" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 shrink-0 ml-1">
        <i data-lucide="x" class="w-4 h-4"></i>
      </button>
    `;

    // Close button handler
    el.querySelector('button').addEventListener('click', () => {
      this.dismiss(el);
    });

    this.container.appendChild(el);
    if (window.lucide) window.lucide.createIcons({ root: el });

    // Animate in
    requestAnimationFrame(() => {
      el.classList.remove('translate-y-2', 'opacity-0');
    });

    // Auto dismiss after 4 seconds
    setTimeout(() => {
      this.dismiss(el);
    }, 4000);
  },
  dismiss(el) {
    el.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 300);
  }
};

// Modal Component
const Modal = {
  overlay: null,
  init() {
    this.overlay = document.getElementById('global-modal-overlay');
  },
  open(title, contentHtml, onConfirm = null) {
    if (!this.overlay) this.init();
    if (!this.overlay) return;

    document.getElementById('modal-title').textContent = title;
    document.getElementById('modal-body').innerHTML = contentHtml;
    const confirmBtn = document.getElementById('modal-confirm-btn');

    if (onConfirm) {
      confirmBtn.classList.remove('hidden');
      confirmBtn.onclick = () => {
        onConfirm();
        this.close();
      };
    } else {
      confirmBtn.classList.add('hidden');
    }

    this.overlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    if (window.lucide) window.lucide.createIcons({ root: this.overlay });
  },
  close() {
    if (!this.overlay) return;
    this.overlay.classList.add('hidden');
    document.body.style.overflow = '';
  }
};

// Banner & Language Management
const Prefs = {
  getLang() {
    try {
      return localStorage.getItem('netbill_lang') || 'en';
    } catch {
      return 'en';
    }
  },
  setLang(lang) {
    try {
      localStorage.setItem('netbill_lang', lang);
    } catch {}
    this.updateLangUI(lang);
  },
  updateLangUI(lang) {
    const btnEn = document.getElementById('lang-btn-en');
    const btnUr = document.getElementById('lang-btn-ur');
    if (btnEn && btnUr) {
      if (lang === 'ur') {
        btnUr.classList.add('bg-amber-500', 'text-white');
        btnUr.classList.remove('text-slate-600', 'dark:text-slate-400');
        btnEn.classList.remove('bg-amber-500', 'text-white');
        btnEn.classList.add('text-slate-600', 'dark:text-slate-400');
      } else {
        btnEn.classList.add('bg-amber-500', 'text-white');
        btnEn.classList.remove('text-slate-600', 'dark:text-slate-400');
        btnUr.classList.remove('bg-amber-500', 'text-white');
        btnUr.classList.add('text-slate-600', 'dark:text-slate-400');
      }
    }
  },
  initBanner() {
    const banner = document.getElementById('safety-banner');
    const closeBtn = document.getElementById('dismiss-safety-banner');
    if (!banner || !closeBtn) return;

    try {
      if (sessionStorage.getItem('netbill_banner_dismissed') === '1') {
        banner.style.display = 'none';
      }
    } catch {}

    closeBtn.addEventListener('click', () => {
      banner.style.display = 'none';
      try {
        sessionStorage.setItem('netbill_banner_dismissed', '1');
      } catch {}
    });
  }
};

// LLM Mode Indicator updater from /api/health
async function updateLLMIndicator() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById('llm-mode-badge');
    const dot = document.getElementById('llm-mode-dot');
    const text = document.getElementById('llm-mode-text');

    if (!badge || !dot || !text) return;

    if (data.mode === 'live') {
      dot.className = 'w-2 h-2 rounded-full bg-emerald-500 shrink-0';
      text.textContent = 'Gemini Live';
      badge.className = 'inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/50 dark:border-emerald-800 dark:text-emerald-300';
    } else if (data.mode === 'mock') {
      dot.className = 'w-2 h-2 rounded-full bg-purple-500 shrink-0';
      text.textContent = 'Mock LLM';
      badge.className = 'inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-950/50 dark:border-purple-800 dark:text-purple-300';
    } else {
      dot.className = 'w-2 h-2 rounded-full bg-amber-500 shrink-0';
      text.textContent = 'Fallback · no LLM';
      badge.className = 'inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/50 dark:border-amber-800 dark:text-amber-300';
    }
  } catch (err) {
    console.debug('Health check failed', err);
  }
}

// Drawer toggle for mobile screen sizes
function initDrawer() {
  const toggleBtn = document.getElementById('drawer-toggle-btn');
  const closeBtn = document.getElementById('drawer-close-btn');
  const sidebar = document.getElementById('app-sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  if (!toggleBtn || !sidebar || !backdrop) return;

  const open = () => {
    sidebar.classList.remove('-translate-x-full');
    backdrop.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  };

  const close = () => {
    sidebar.classList.add('-translate-x-full');
    backdrop.classList.add('hidden');
    document.body.style.overflow = '';
  };

  toggleBtn.addEventListener('click', open);
  if (closeBtn) closeBtn.addEventListener('click', close);
  backdrop.addEventListener('click', close);
}

// Global DOM Content Loaded Listener
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) window.lucide.createIcons();
  Toast.init();
  Modal.init();
  Prefs.initBanner();
  Prefs.updateLangUI(Prefs.getLang());
  initDrawer();
  updateLLMIndicator();

  // Dark mode button listeners
  const themeToggle = document.getElementById('theme-toggle-btn');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      Theme.toggle();
      if (window.lucide) window.lucide.createIcons();
    });
  }

  // Language switcher listeners
  const btnEn = document.getElementById('lang-btn-en');
  const btnUr = document.getElementById('lang-btn-ur');
  if (btnEn) btnEn.addEventListener('click', () => Prefs.setLang('en'));
  if (btnUr) btnUr.addEventListener('click', () => Prefs.setLang('ur'));
});

// Expose utilities on window
window.NetBill = {
  Theme,
  Toast,
  Modal,
  Prefs,
  updateLLMIndicator
};
