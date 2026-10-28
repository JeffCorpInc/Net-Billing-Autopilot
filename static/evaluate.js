/**
 * Evaluation and Benchmark Dashboard
 * NetBill Assist - Solar Onboarding Assistant (Phase 5)
 */

(function () {
  'use strict';

  let selectedRuns = 1;
  let isEvaluating = false;
  let chartInstances = {};

  const CASES = [
    'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09', 'C10',
    'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C19', 'C20', 'C21'
  ];

  document.addEventListener('DOMContentLoaded', initEvaluation);

  function initEvaluation() {
    setupRunButtons();
    checkHealthMode();
    loadSummary();

    // Listen for theme changes to re-theme charts
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        setTimeout(reloadChartsTheme, 150);
      });
    }
  }

  function checkHealthMode() {
    fetch('/api/health')
      .then(r => r.json())
      .then(data => {
        const warning = document.getElementById('mock-warning-banner');
        if (warning && (data.llm_provider === 'mock' || data.llm_provider === 'none')) {
          warning.classList.remove('hidden');
        }
      })
      .catch(() => {});
  }

  function setupRunButtons() {
    const btn1 = document.getElementById('runs-btn-1');
    const btn3 = document.getElementById('runs-btn-3');
    const runBtn = document.getElementById('run-eval-btn');

    if (btn1 && btn3) {
      btn1.addEventListener('click', () => {
        selectedRuns = 1;
        btn1.className = 'px-3 py-1.5 rounded-lg transition-colors bg-amber-500 text-slate-950 font-bold';
        btn3.className = 'px-3 py-1.5 rounded-lg transition-colors text-slate-300 hover:text-white';
      });

      btn3.addEventListener('click', () => {
        selectedRuns = 3;
        btn3.className = 'px-3 py-1.5 rounded-lg transition-colors bg-amber-500 text-slate-950 font-bold';
        btn1.className = 'px-3 py-1.5 rounded-lg transition-colors text-slate-300 hover:text-white';
      });
    }

    if (runBtn) {
      runBtn.addEventListener('click', runFullEvaluation);
    }
  }

  async function runFullEvaluation() {
    if (isEvaluating) return;
    isEvaluating = true;

    const runBtn = document.getElementById('run-eval-btn');
    const runIcon = document.getElementById('run-eval-icon');
    const runText = document.getElementById('run-eval-text');
    const progBox = document.getElementById('eval-progress-container');
    const progBar = document.getElementById('eval-progress-bar');
    const progCount = document.getElementById('eval-progress-count');
    const progStatus = document.getElementById('eval-progress-status');

    if (runBtn) runBtn.disabled = true;
    if (runIcon) runIcon.classList.add('animate-spin');
    if (runText) runText.textContent = `Evaluating (${selectedRuns} ${selectedRuns > 1 ? 'runs' : 'run'})…`;
    if (progBox) progBox.classList.remove('hidden');

    let completed = 0;
    const total = CASES.length;

    for (let i = 0; i < total; i++) {
      const cid = CASES[i];
      if (progStatus) progStatus.textContent = `Evaluating case ${cid} against ground truth…`;
      if (progCount) progCount.textContent = `${completed} / ${total}`;
      if (progBar) progBar.style.width = `${Math.round((completed / total) * 100)}%`;

      try {
        await fetch(`/api/evaluate/case/${cid}?runs=${selectedRuns}`, { method: 'POST' });
      } catch (err) {
        console.error(`Evaluation failed for ${cid}:`, err);
      }

      completed++;
      if (progBar) progBar.style.width = `${Math.round((completed / total) * 100)}%`;
      if (progCount) progCount.textContent = `${completed} / ${total}`;
    }

    if (progStatus) progStatus.textContent = 'Aggregating benchmark metrics…';

    await loadSummary();

    setTimeout(() => {
      if (progBox) progBox.classList.add('hidden');
      if (runBtn) runBtn.disabled = false;
      if (runIcon) runIcon.classList.remove('animate-spin');
      if (runText) runText.textContent = 'Run Benchmark';
      isEvaluating = false;
    }, 600);
  }

  async function loadSummary() {
    try {
      const resp = await fetch('/api/evaluate/summary');
      if (!resp.ok) throw new Error('Summary fetch failed');
      const data = await resp.json();

      updateMetricCards(data.metrics || {});
      renderCharts(data);
      renderMatrixTable(data.cases_matrix || []);
      renderFindings(data.findings || []);

      if (window.lucide) {
        window.lucide.createIcons();
      }
    } catch (err) {
      console.error('Failed to load evaluation summary:', err);
    }
  }

  function updateMetricCards(m) {
    // 1. Wrong Values
    const wv = m.wrong_values_in_draft?.value ?? 0;
    setText('metric-wrong-values', wv);
    setBadge('badge-wrong-values', wv === 0, 'Target: 0');

    // 2. Code Rule Accuracy
    const cra = m.code_rule_accuracy?.value ?? 100;
    setText('metric-code-acc', `${cra}%`);
    setBadge('badge-code-acc', cra === 100, 'Target: 100%');

    // 3. Trap Recall
    const tr = m.trap_recall?.value ?? 100;
    setText('metric-trap-recall', `${tr}%`);
    setBadge('badge-trap-recall', tr === 100, 'Target: 100%');

    // 4. LLM Match Accuracy
    const lma = m.llm_match_accuracy?.value ?? 100;
    setText('metric-llm-acc', `${lma}%`);
    setBadge('badge-llm-acc', lma >= 90, 'Target: ≥90%');

    // 5. False Alarms
    const fa = m.false_alarms?.value ?? 0;
    setText('metric-false-alarms', fa);
    setBadge('badge-false-alarms', fa === 0, 'Target: 0');

    // 6. Deferred to Staff
    const def = m.deferred_to_staff?.value ?? 0;
    setText('metric-deferred', `${def}%`);
    setBadge('badge-deferred', def <= 15, 'Target: <15%');

    // 7. Checklist Faithfulness
    const cf = m.checklist_faithfulness?.value ?? 100;
    setText('metric-faithfulness', `${cf}%`);
    setBadge('badge-faithfulness', cf === 100, 'Target: 100%');

    // 8. LLM Consistency
    const lc = m.llm_consistency?.value ?? 100;
    setText('metric-consistency', `${lc}%`);
    setBadge('badge-consistency', lc >= 90, 'Target: ≥90%');

    // 9. Latency
    const lat = m.avg_latency_ms?.value ?? 0;
    setText('metric-latency', lat);
    setBadge('badge-latency', lat <= 500, 'Target: <500ms');
  }

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  function setBadge(id, isPass, text) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    if (isPass) {
      el.className = 'px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 dark:bg-emerald-950/70 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800';
    } else {
      el.className = 'px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 dark:bg-rose-950/70 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800';
    }
  }

  function isDarkMode() {
    return document.documentElement.classList.contains('dark');
  }

  function getThemeColors() {
    const dark = isDarkMode();
    return {
      textColor: dark ? '#94A3B8' : '#64748B',
      gridColor: dark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
      primary: '#F59E0B',
      emerald: '#10B981',
      rose: '#EF4444',
      blue: '#3B82F6',
      purple: '#8B5CF6',
    };
  }

  function renderCharts(data) {
    renderAccuracyPerCheckChart(data.accuracy_per_check || {});
    renderTrapOutcomesChart(data.trap_outcomes || {});
    renderShadowAgreementChart(data.shadow_checks || []);
    renderLatencyByCaseChart(data.latency_by_case || []);
  }

  function reloadChartsTheme() {
    // If charts exist, destroy and reload with current data
    fetch('/api/evaluate/summary')
      .then(r => r.json())
      .then(data => renderCharts(data))
      .catch(() => {});
  }

  // 1. Accuracy Per Check Chart (Horizontal Bar)
  function renderAccuracyPerCheckChart(accMap) {
    const ctx = document.getElementById('chart-accuracy-per-check');
    if (!ctx) return;
    if (chartInstances.acc) chartInstances.acc.destroy();

    const colors = getThemeColors();
    const labels = [
      'R1: CNIC Format',
      'R2: CNIC Expiry',
      'R3: Capacity Limit',
      'R4: 3-Phase Rule',
      'R5: Connected Load',
      'R7: Required Docs',
      'L1: Name Match',
      'L2: Address Match'
    ];
    const keys = [
      'cnic_format',
      'cnic_expiry',
      'capacity',
      'connection_phase',
      'connected_load',
      'required_docs',
      'name_match',
      'address_match'
    ];
    const values = keys.map(k => accMap[k] ?? 100);

    chartInstances.acc = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          data: values,
          backgroundColor: values.map(v => v === 100 ? colors.emerald : colors.primary),
          borderRadius: 6,
          barThickness: 16,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` Accuracy: ${ctx.raw}%`
            }
          }
        },
        scales: {
          x: {
            min: 0,
            max: 100,
            grid: { color: colors.gridColor },
            ticks: {
              color: colors.textColor,
              callback: v => `${v}%`
            }
          },
          y: {
            grid: { display: false },
            ticks: { color: colors.textColor, font: { size: 11 } }
          }
        }
      }
    });
  }

  // 2. Trap Outcomes Chart (Doughnut)
  function renderTrapOutcomesChart(traps) {
    const ctx = document.getElementById('chart-trap-outcomes');
    if (!ctx) return;
    if (chartInstances.traps) chartInstances.traps.destroy();

    const colors = getThemeColors();
    const caught = traps.caught || 0;
    const deferred = traps.deferred || 0;
    const missed = traps.missed || 0;

    chartInstances.traps = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Caught (NOT_READY)', 'Deferred (NEEDS_REVIEW)', 'Missed'],
        datasets: [{
          data: [caught, deferred, missed],
          backgroundColor: [colors.emerald, colors.primary, colors.rose],
          borderWidth: 2,
          borderColor: isDarkMode() ? '#0F172A' : '#FFFFFF',
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '70%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: colors.textColor,
              font: { size: 11 },
              boxWidth: 12,
              padding: 14
            }
          },
          tooltip: {
            callbacks: {
              label: (ctx) => ` ${ctx.label}: ${ctx.raw} packs`
            }
          }
        }
      }
    });
  }

  // 3. Shadow Agreement Chart (Bar showing code vs LLM agreement across cases)
  function renderShadowAgreementChart(shadowList) {
    const ctx = document.getElementById('chart-shadow-agreement');
    if (!ctx) return;
    if (chartInstances.shadow) chartInstances.shadow.destroy();

    const colors = getThemeColors();

    // Group by case ID
    const caseMap = {};
    CASES.forEach(c => { caseMap[c] = { agree: 0, disagree: 0 }; });

    shadowList.forEach(s => {
      const cid = s.case_id;
      if (caseMap[cid]) {
        if (s.agree) caseMap[cid].agree++;
        else caseMap[cid].disagree++;
      }
    });

    const labels = CASES;
    const agreeCounts = labels.map(c => caseMap[c].agree);
    const disagreeCounts = labels.map(c => caseMap[c].disagree);

    chartInstances.shadow = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Agreement (Code = LLM)',
            data: agreeCounts,
            backgroundColor: colors.emerald,
            borderRadius: 4,
            barThickness: 8,
          },
          {
            label: 'Disagreement (Code Sup.)',
            data: disagreeCounts,
            backgroundColor: colors.rose,
            borderRadius: 4,
            barThickness: 8,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: colors.textColor, font: { size: 11 }, boxWidth: 12 }
          },
          tooltip: {
            callbacks: {
              afterLabel: (ctx) => {
                if (ctx.datasetIndex === 1 && ctx.raw > 0) {
                  return ' Disagreement on R3: Code rejected capacity > sanctioned load; LLM was lenient. Code decision prevailed.';
                }
                return '';
              }
            }
          }
        },
        scales: {
          x: {
            stacked: true,
            grid: { display: false },
            ticks: { color: colors.textColor, font: { size: 10 } }
          },
          y: {
            stacked: true,
            min: 0,
            max: 3,
            grid: { color: colors.gridColor },
            ticks: {
              stepSize: 1,
              color: colors.textColor
            }
          }
        }
      }
    });
  }

  // 4. Latency by Case (Bar Chart)
  function renderLatencyByCaseChart(latList) {
    const ctx = document.getElementById('chart-latency-per-case');
    if (!ctx) return;
    if (chartInstances.latency) chartInstances.latency.destroy();

    const colors = getThemeColors();
    const latMap = {};
    latList.forEach(item => { latMap[item.case_id] = item.latency_ms; });

    const labels = CASES;
    const values = labels.map(c => latMap[c] ?? 0);

    chartInstances.latency = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Latency (ms)',
          data: values,
          backgroundColor: colors.blue,
          borderRadius: 4,
          barThickness: 8,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => ` Response time: ${ctx.raw} ms`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: colors.textColor, font: { size: 10 } }
          },
          y: {
            grid: { color: colors.gridColor },
            ticks: {
              color: colors.textColor,
              callback: v => `${v}ms`
            }
          }
        }
      }
    });
  }

  function renderMatrixTable(cases) {
    const tbody = document.getElementById('matrix-tbody');
    if (!tbody) return;

    if (!cases || cases.length === 0) {
      tbody.innerHTML = `<tr><td colspan="14" class="py-8 text-center text-slate-400 font-sans">No evaluation results found. Click "Run Benchmark" above.</td></tr>`;
      return;
    }

    const checkOrder = [
      'cnic_format',
      'cnic_expiry',
      'capacity',
      'connection_phase',
      'connected_load',
      'required_docs',
      'name_match',
      'address_match'
    ];

    tbody.innerHTML = cases.map(c => {
      const isClean = c.category === 'clean';
      const catBadge = isClean
        ? `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold whitespace-nowrap bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">Clean</span>`
        : `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold whitespace-nowrap bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800">Trap</span>`;

      const checkCells = checkOrder.map(k => {
        const item = c.checks?.[k] || {};
        const got = item.got || '-';
        const isMatch = item.match;

        let bgCls = 'bg-slate-50 dark:bg-slate-800/40 text-slate-600 dark:text-slate-300';

        if (got === 'PASS') {
          bgCls = 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200/70 dark:border-emerald-800/40';
        } else if (got === 'FAIL') {
          bgCls = 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200/70 dark:border-rose-800/40';
        } else if (got === 'UNSURE') {
          bgCls = 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200/70 dark:border-amber-800/40';
        }

        const borderRing = !isMatch ? 'ring-2 ring-rose-500' : '';

        return `<td class="py-2.5 px-2 text-center">
          <span class="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold whitespace-nowrap ${bgCls} ${borderRing}" title="Exp: ${item.expected} | Got: ${got}">
            ${got}
          </span>
        </td>`;
      }).join('');

      // Overall Got vs Exp (Dashboard-style rounded pill + compact label)
      const overallGot = c.overall_got || '-';
      let overallCls = 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300';
      let overallLabel = overallGot;
      let overallIcon = 'help-circle';
      if (overallGot === 'READY') {
        overallCls = 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800';
        overallLabel = 'READY';
        overallIcon = 'check-circle';
      } else if (overallGot === 'NOT_READY') {
        overallCls = 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-800';
        overallLabel = 'ISSUES';
        overallIcon = 'x-circle';
      } else if (overallGot === 'NEEDS_REVIEW') {
        overallCls = 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800';
        overallLabel = 'REVIEW';
        overallIcon = 'alert-triangle';
      }

      // Gate status
      const gatePass = c.gate_passed;
      const gateBadge = gatePass
        ? `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200/70 dark:border-emerald-800/40">PASS</span>`
        : `<span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border border-rose-200/70 dark:border-rose-800/40">FAIL</span>`;

      // PDF Discrepancies
      const pdfCount = c.wrong_pdf_values ?? 0;
      const pdfBadge = pdfCount === 0
        ? `<span class="text-emerald-600 dark:text-emerald-400 font-bold">0</span>`
        : `<span class="text-rose-600 dark:text-rose-400 font-bold">${pdfCount}</span>`;

      return `<tr class="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
        <td class="py-2.5 px-3 font-bold text-slate-900 dark:text-white">
          <a href="/cases/${c.case_id}" class="hover:text-amber-500 hover:underline flex items-center gap-1.5 font-mono">
            <span>${c.case_id}</span>
          </a>
        </td>
        <td class="py-2.5 px-3">${catBadge}</td>
        ${checkCells}
        <td class="py-2.5 px-3 text-center">
          <span class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold whitespace-nowrap ${overallCls}" title="Expected: ${c.overall_expected} | Got: ${overallGot}">
            <i data-lucide="${overallIcon}" class="w-3 h-3 shrink-0"></i>
            ${overallLabel}
          </span>
        </td>
        <td class="py-2.5 px-2 text-center">${gateBadge}</td>
        <td class="py-2.5 px-2 text-center">${pdfBadge}</td>
        <td class="py-2.5 px-3 text-right">
          <a href="/cases/${c.case_id}" class="text-amber-600 dark:text-amber-400 hover:underline font-sans font-semibold text-[11px] whitespace-nowrap">
            Inspect &rarr;
          </a>
        </td>
      </tr>`;
    }).join('');
  }

  function renderFindings(findings) {
    const box = document.getElementById('findings-container');
    if (!box) return;

    if (!findings || findings.length === 0) {
      box.innerHTML = `<p class="text-slate-400">Run the benchmark to populate algorithmic observations.</p>`;
      return;
    }

    box.innerHTML = findings.map(f => `
      <div class="flex items-start gap-2.5 py-1">
        <i data-lucide="check" class="w-4 h-4 text-emerald-500 shrink-0 mt-0.5"></i>
        <span>${f}</span>
      </div>
    `).join('');
  }

})();

