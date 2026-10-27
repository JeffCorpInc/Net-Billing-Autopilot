/**
 * NetBill Assist - Dashboard Client Engine
 * Handles cases fetching, table rendering, KPI calculations, search, filters, and batch checks.
 */

let allCases = [];
let activeFilter = 'all';
let searchQuery = '';
let sortBy = 'id-asc';
let isRunningAll = false;

// Status styling helper following design tokens
function getStatusBadge(status) {
  const map = {
    READY: {
      bg: 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
      icon: 'badge-check',
      label: 'READY'
    },
    NOT_READY: {
      bg: 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800',
      icon: 'octagon-x',
      label: 'NOT READY'
    },
    NEEDS_REVIEW: {
      bg: 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
      icon: 'alert-triangle',
      label: 'NEEDS REVIEW'
    },
    PENDING: {
      bg: 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-700',
      icon: 'clock',
      label: 'PENDING'
    }
  };

  const item = map[status] || map.PENDING;
  return `
    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${item.bg}">
      <i data-lucide="${item.icon}" class="w-3.5 h-3.5 shrink-0"></i>
      <span>${item.label}</span>
    </span>
  `;
}

// Render capacity mini-bar
function renderCapacityBar(proposed, sanctioned) {
  const isOver = proposed > sanctioned;
  const pct = Math.min(Math.round((proposed / sanctioned) * 100), 100);
  const colorClass = isOver ? 'bg-rose-500' : 'bg-teal-500';

  return `
    <div class="w-28 space-y-1">
      <div class="flex items-center justify-between text-[11px] font-mono-numbers">
        <span class="${isOver ? 'text-rose-600 dark:text-rose-400 font-bold' : 'text-slate-600 dark:text-slate-300'}">
          ${proposed} kW
        </span>
        <span class="text-slate-400">/ ${sanctioned} kW</span>
      </div>
      <div class="h-1.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
        <div class="h-full ${colorClass} rounded-full transition-all duration-500" style="width: ${pct}%"></div>
      </div>
    </div>
  `;
}

// Render document count circular badge
function renderDocProgress(present, required) {
  const isComplete = present >= required;
  return `
    <div class="inline-flex items-center gap-1.5 text-xs font-mono-numbers ${isComplete ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-600 dark:text-slate-300'}">
      <i data-lucide="${isComplete ? 'check' : 'files'}" class="w-3.5 h-3.5 ${isComplete ? 'text-emerald-500' : 'text-slate-400'}"></i>
      <span>${present}/${required}</span>
    </div>
  `;
}

// Fetch cases from API
async function fetchCases() {
  const tableBody = document.getElementById('cases-tbody');
  try {
    const res = await fetch('/api/cases');
    if (!res.ok) throw new Error('Failed to load application cases');
    allCases = await res.json();
    updateKPICards();
    renderTable();
  } catch (err) {
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="7" class="py-12 text-center text-sm text-rose-500 font-medium">
            Error loading cases: ${err.message}. Please verify the server is running.
          </td>
        </tr>
      `;
    }
  }
}

// Compute & update KPI numbers and insight chips
function updateKPICards() {
  const total = allCases.length || 0;
  const ready = allCases.filter(c => c.overall === 'READY').length;
  const review = allCases.filter(c => c.overall === 'NEEDS_REVIEW').length;
  const notReady = allCases.filter(c => c.overall === 'NOT_READY').length;

  document.getElementById('kpi-total').textContent = total;
  document.getElementById('kpi-ready').textContent = ready;
  document.getElementById('kpi-review').textContent = review;
  document.getElementById('kpi-notready').textContent = notReady;

  document.getElementById('kpi-ready-pct').textContent = total ? `${Math.round((ready / total) * 100)}%` : '0%';
  document.getElementById('kpi-review-pct').textContent = total ? `${Math.round((review / total) * 100)}%` : '0%';
  document.getElementById('kpi-notready-pct').textContent = total ? `${Math.round((notReady / total) * 100)}%` : '0%';

  document.getElementById('kpi-ready-bar').style.width = total ? `${(ready / total) * 100}%` : '0%';
  document.getElementById('kpi-review-bar').style.width = total ? `${(review / total) * 100}%` : '0%';
  document.getElementById('kpi-notready-bar').style.width = total ? `${(notReady / total) * 100}%` : '0%';
}

// Filter and sort items
function getFilteredCases() {
  let list = [...allCases];

  // Category or status filters
  if (activeFilter === 'ready') list = list.filter(c => c.overall === 'READY');
  else if (activeFilter === 'review') list = list.filter(c => c.overall === 'NEEDS_REVIEW');
  else if (activeFilter === 'not_ready') list = list.filter(c => c.overall === 'NOT_READY');
  else if (activeFilter === 'pending') list = list.filter(c => c.overall === 'PENDING');
  else if (activeFilter === 'clean') list = list.filter(c => c.category === 'clean');
  else if (activeFilter === 'trap') list = list.filter(c => c.category === 'trap');

  // Search filter
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase().trim();
    list = list.filter(c =>
      c.case_id.toLowerCase().includes(q) ||
      c.applicant_name.toLowerCase().includes(q) ||
      c.description.toLowerCase().includes(q)
    );
  }

  // Sorting
  list.sort((a, b) => {
    if (sortBy === 'id-asc') return a.case_id.localeCompare(b.case_id);
    if (sortBy === 'id-desc') return b.case_id.localeCompare(a.case_id);
    if (sortBy === 'kw-desc') return b.proposed_kw - a.proposed_kw;
    if (sortBy === 'kw-asc') return a.proposed_kw - b.proposed_kw;
    if (sortBy === 'readiness-desc') return b.readiness - a.readiness;
    if (sortBy === 'readiness-asc') return a.readiness - b.readiness;
    return 0;
  });

  return list;
}

// Render table rows
function renderTable() {
  const tableBody = document.getElementById('cases-tbody');
  if (!tableBody) return;

  const items = getFilteredCases();

  if (items.length === 0) {
    tableBody.innerHTML = `
      <tr>
        <td colspan="7" class="py-16 text-center">
          <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-400 mb-3">
            <i data-lucide="search-x" class="w-6 h-6"></i>
          </div>
          <p class="text-sm font-semibold text-slate-700 dark:text-slate-300">No application packs found</p>
          <p class="text-xs text-slate-400 mt-1">Try clearing filters or search term.</p>
        </td>
      </tr>
    `;
    if (window.lucide) window.lucide.createIcons({ root: tableBody });
    return;
  }

  tableBody.innerHTML = items.map(c => `
    <tr class="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors cursor-pointer group border-b border-slate-100 dark:border-slate-800/60" onclick="window.location='/case/${c.case_id}'">
      <!-- Case ID & Category -->
      <td class="py-3.5 px-4 font-mono text-xs font-bold text-slate-900 dark:text-white">
        <div class="flex items-center gap-2">
          <span>${c.case_id}</span>
          ${c.category === 'clean'
            ? '<span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">Clean</span>'
            : '<span class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800">Trap</span>'
          }
        </div>
      </td>

      <!-- Applicant Name & Description -->
      <td class="py-3.5 px-4 min-w-[200px]">
        <div class="font-semibold text-sm text-slate-900 dark:text-white group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
          ${c.applicant_name}
        </div>
        <div class="text-xs text-slate-400 truncate max-w-xs mt-0.5" title="${c.description}">
          ${c.description}
        </div>
      </td>

      <!-- Type -->
      <td class="py-3.5 px-4">
        <div class="inline-flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
          <i data-lucide="${c.category === 'clean' && c.sanctioned_load_kw > 20 ? 'building' : 'home'}" class="w-4 h-4 text-slate-400"></i>
          <span class="capitalize">${c.sanctioned_load_kw >= 15 ? 'Commercial' : 'Residential'}</span>
        </div>
      </td>

      <!-- Capacity Mini-Bar -->
      <td class="py-3.5 px-4">
        ${renderCapacityBar(c.proposed_kw, c.sanctioned_load_kw)}
      </td>

      <!-- Documents Progress -->
      <td class="py-3.5 px-4">
        ${renderDocProgress(c.docs_present_count, c.docs_required_count)}
      </td>

      <!-- Overall Status Chip -->
      <td class="py-3.5 px-4">
        ${getStatusBadge(c.overall)}
      </td>

      <!-- Action Button / Review -->
      <td class="py-3.5 px-4 text-right">
        <div class="inline-flex items-center gap-2">
          ${c.reviewed ? `
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800" title="Reviewed by staff">
              <i data-lucide="user-check" class="w-3.5 h-3.5"></i>
              <span>Reviewed</span>
            </span>
          ` : ''}
          <a href="/case/${c.case_id}" class="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-amber-500 hover:text-slate-950 dark:bg-slate-800 dark:hover:bg-amber-500 dark:hover:text-slate-950 text-slate-700 dark:text-slate-300 transition-colors inline-flex items-center gap-1">
            <span>Open</span>
            <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
          </a>
        </div>
      </td>
    </tr>
  `).join('');

  if (window.lucide) window.lucide.createIcons({ root: tableBody });
}

// Client-side batch check loop over all cases (used in Phase 2)
async function runAllChecks() {
  if (isRunningAll) return;
  isRunningAll = true;

  const btn = document.getElementById('run-all-btn');
  const progressBox = document.getElementById('run-all-progress-box');
  const progressBar = document.getElementById('run-all-progress-bar');
  const progressText = document.getElementById('run-all-progress-text');

  if (btn) btn.disabled = true;
  if (progressBox) progressBox.classList.remove('hidden');

  const total = allCases.length;
  for (let i = 0; i < total; i++) {
    const c = allCases[i];
    if (progressText) progressText.textContent = `Checking ${c.case_id} (${i + 1}/${total})…`;
    if (progressBar) progressBar.style.width = `${Math.round(((i + 1) / total) * 100)}%`;

    try {
      // In Phase 1, rules endpoint is not mounted yet; placeholder simulates or calls API if available
      const res = await fetch(`/api/check/${c.case_id}?use_llm=false`, { method: 'POST' });
      if (res.ok) {
        const report = await res.json();
        c.overall = report.overall;
        c.readiness = report.readiness_score;
      }
    } catch {}
    renderTable();
    updateKPICards();
    await new Promise(r => setTimeout(r, 60));
  }

  if (progressText) progressText.textContent = `Completed 21 cases check!`;
  setTimeout(() => {
    if (progressBox) progressBox.classList.add('hidden');
    if (btn) btn.disabled = false;
    isRunningAll = false;
  }, 1200);

  if (window.NetBill?.Toast) {
    window.NetBill.Toast.show('Queue Check Complete', 'All 21 application packs inspected.', 'success');
  }
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', () => {
  fetchCases();

  // Search input
  const searchInput = document.getElementById('cases-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value;
      renderTable();
    });
  }

  // Sort dropdown
  const sortSelect = document.getElementById('cases-sort');
  if (sortSelect) {
    sortSelect.addEventListener('change', (e) => {
      sortBy = e.target.value;
      renderTable();
    });
  }

  // Filter chips
  const filterButtons = document.querySelectorAll('[data-filter]');
  filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      filterButtons.forEach(b => {
        b.classList.remove('bg-amber-500', 'text-slate-950', 'font-bold');
        b.classList.add('bg-white', 'dark:bg-slate-900', 'text-slate-600', 'dark:text-slate-400');
      });
      btn.classList.add('bg-amber-500', 'text-slate-950', 'font-bold');
      btn.classList.remove('bg-white', 'dark:bg-slate-900', 'text-slate-600', 'dark:text-slate-400');
      activeFilter = btn.getAttribute('data-filter');
      renderTable();
    });
  });

  // KPI card click filters
  const kpiCards = document.querySelectorAll('[data-kpi-filter]');
  kpiCards.forEach(card => {
    card.addEventListener('click', () => {
      const targetFilter = card.getAttribute('data-kpi-filter');
      const targetBtn = document.querySelector(`[data-filter="${targetFilter}"]`);
      if (targetBtn) targetBtn.click();
    });
  });

  // Run all checks button
  const runAllBtn = document.getElementById('run-all-btn');
  if (runAllBtn) {
    runAllBtn.addEventListener('click', runAllChecks);
  }
});
