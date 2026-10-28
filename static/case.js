/**
 * NetBill Assist - Case Page Client Engine
 * Handles check execution, SVG gauge needle animation, LLM accordion details,
 * cross-document field hover highlights, customer checklist, draft PDF iframe,
 * audit trail timeline, staff review modal, and custom case deletion.
 */

const CasePage = {
  caseId: '',
  isChecking: false,
  checklistLang: 'en',
  currentTab: 'checklist',
  cachedChecklist: null,

  init(caseId) {
    this.caseId = caseId;
    this.bindEvents();
    this.initCrossDocHover();
    this.updateGauge();
    this.loadChecklist();
  },

  bindEvents() {
    const runBtn = document.getElementById('case-run-checks-btn');
    if (runBtn) {
      runBtn.addEventListener('click', () => this.runChecks());
    }

    const reviewBtn = document.getElementById('case-review-btn');
    if (reviewBtn) {
      reviewBtn.addEventListener('click', () => this.openReviewModal());
    }

    const deleteBtn = document.getElementById('case-delete-btn');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', () => this.deleteCustomCase());
    }
  },

  initCrossDocHover() {
    const nameEls = document.querySelectorAll('.cross-doc-name');
    nameEls.forEach(el => {
      el.addEventListener('mouseenter', () => {
        nameEls.forEach(n => {
          const isCnic = n.id === 'cross-name-cnic';
          n.classList.add('ring-2', 'ring-amber-400');
          if (isCnic) {
            n.classList.add('bg-amber-500/25', 'text-white');
          } else {
            n.classList.add('bg-amber-100/70', 'dark:bg-amber-950/50');
          }
        });
      });
      el.addEventListener('mouseleave', () => {
        nameEls.forEach(n => {
          n.classList.remove(
            'ring-2',
            'ring-amber-400',
            'bg-amber-500/25',
            'text-white',
            'bg-amber-100/70',
            'dark:bg-amber-950/50'
          );
        });
      });
    });

    const addrEls = document.querySelectorAll('.cross-doc-addr');
    addrEls.forEach(el => {
      el.addEventListener('mouseenter', () => {
        addrEls.forEach(a => {
          const isCnic = a.id === 'cross-addr-cnic';
          a.classList.add('ring-2', 'ring-teal-400');
          if (isCnic) {
            a.classList.add('bg-teal-500/25', 'text-white');
          } else {
            a.classList.add('bg-teal-100/70', 'dark:bg-teal-950/50');
          }
        });
      });
      el.addEventListener('mouseleave', () => {
        addrEls.forEach(a => {
          a.classList.remove(
            'ring-2',
            'ring-teal-400',
            'bg-teal-500/25',
            'text-white',
            'bg-teal-100/70',
            'dark:bg-teal-950/50'
          );
        });
      });
    });
  },

  toggleLLMDetails(checkId) {
    const panel = document.getElementById(`llm-panel-${checkId}`);
    const chevron = document.getElementById(`chevron-${checkId}`);
    if (!panel) return;

    if (panel.classList.contains('hidden')) {
      panel.classList.remove('hidden');
      if (chevron) chevron.classList.add('rotate-180');
    } else {
      panel.classList.add('hidden');
      if (chevron) chevron.classList.remove('rotate-180');
    }
  },

  switchTab(tab) {
    this.currentTab = tab;
    const tabs = ['checklist', 'draft', 'audit'];
    tabs.forEach(t => {
      const btn = document.getElementById(`tab-btn-${t}`);
      const content = document.getElementById(`tab-content-${t}`);
      if (btn && content) {
        if (t === tab) {
          btn.className = 'px-4 py-2.5 text-xs font-bold border-b-2 border-amber-500 text-amber-600 dark:text-amber-400 flex items-center gap-2 transition-colors';
          content.classList.remove('hidden');
        } else {
          btn.className = 'px-4 py-2.5 text-xs font-semibold border-b-2 border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 flex items-center gap-2 transition-colors';
          content.classList.add('hidden');
        }
      }
    });

    const controls = document.getElementById('checklist-controls');
    if (controls) {
      if (tab === 'checklist') controls.classList.remove('hidden');
      else controls.classList.add('hidden');
    }

    if (tab === 'audit') {
      this.loadAuditTrail();
    }
  },

  setChecklistLang(lang) {
    this.checklistLang = lang;
    this.loadChecklist();
  },

  async loadChecklist() {
    const container = document.getElementById('checklist-items-container');
    const gateBadge = document.getElementById('checklist-gate-badge');
    const gateText = document.getElementById('checklist-gate-text');
    const sourceBadge = document.getElementById('checklist-source-badge');

    if (container) {
      container.innerHTML = `
        <div class="p-6 text-center text-xs text-slate-400">
          <div class="inline-block w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mb-2"></div>
          <div>Generating customer checklist (${this.checklistLang.toUpperCase()})…</div>
        </div>
      `;
    }

    try {
      const res = await fetch(`/api/checklist/${this.caseId}?lang=${this.checklistLang}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to load checklist');
      const data = await res.json();
      this.cachedChecklist = data;

      // Update gate badge
      if (gateBadge && gateText) {
        if (data.gate === 'passed') {
          gateBadge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800';
          gateText.textContent = 'Verified against checks (Faithfulness Gate Passed)';
          gateBadge.title = '';
        } else if (data.gate === 'rejected') {
          gateBadge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 cursor-help';
          gateText.textContent = 'Template fallback: LLM output rejected by gate';
          gateBadge.title = data.gate_reason || 'Gate rejected output';
        } else {
          gateBadge.className = 'inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-bold bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800';
          gateText.textContent = 'All checks passed · Ready for signature';
        }
      }

      if (sourceBadge) {
        sourceBadge.textContent = `SOURCE: ${data.source.toUpperCase()}`;
      }

      // Render items
      if (container) {
        const isUrdu = this.checklistLang === 'ur';
        container.innerHTML = data.items.map((item, idx) => `
          <div class="p-4 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800 flex items-start gap-3 ${isUrdu ? 'font-urdu' : ''}" ${isUrdu ? 'dir="rtl" style="font-size: 16px; line-height: 2.2;"' : ''}>
            <div class="w-6 h-6 rounded-full bg-amber-500 text-slate-950 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5 font-sans">
              ${idx + 1}
            </div>
            <div class="flex-1 text-slate-800 dark:text-slate-100">
              ${item.text}
            </div>
          </div>
        `).join('');
      }

      if (window.lucide) window.lucide.createIcons();

    } catch (err) {
      if (container) {
        container.innerHTML = `
          <div class="p-4 text-xs text-rose-500 bg-rose-50 dark:bg-rose-950/40 rounded-xl border border-rose-200 dark:border-rose-800">
            Error loading checklist: ${err.message}
          </div>
        `;
      }
    }
  },

  copyChecklistText() {
    if (!this.cachedChecklist || !this.cachedChecklist.items) return;
    const text = this.cachedChecklist.items
      .map((it, idx) => `${idx + 1}. ${it.text}`)
      .join('\n\n');

    navigator.clipboard.writeText(text).then(() => {
      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Copied to Clipboard', 'Checklist items copied as plain text.', 'success');
      }
    });
  },

  async loadAuditTrail() {
    const container = document.getElementById('audit-timeline-container');
    if (!container) return;

    container.innerHTML = `
      <div class="p-4 text-xs text-slate-400">Loading audit history…</div>
    `;

    try {
      const res = await fetch(`/api/audit/${this.caseId}`);
      if (!res.ok) throw new Error('Failed to load audit history');
      const data = await res.json();
      const entries = data.entries || [];

      if (entries.length === 0) {
        container.innerHTML = `
          <div class="text-xs text-slate-400 py-2">No audit events recorded for this case yet.</div>
        `;
        return;
      }

      const iconMap = {
        case_created: 'file-plus-2',
        files_uploaded: 'paperclip',
        checks_run: 'play-circle',
        checklist_generated: 'list-checks',
        draft_generated: 'file-text',
        staff_review: 'user-check',
      };

      container.innerHTML = entries.map(ev => {
        const time = new Date(ev.timestamp);
        const timeStr = time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        const dateStr = time.toLocaleDateString();
        const icon = iconMap[ev.event] || 'activity';

        const d = ev.details || ev || {};
        let detailText = '';
        if (ev.event === 'case_created') {
          detailText = `Custom application pack created for <strong>${d.applicant_name || 'Applicant'}</strong> (${d.proposed_kw ?? 0} kW system, ${d.docs_count ?? 0} docs attached)`;
        } else if (ev.event === 'files_uploaded') {
          detailText = `Uploaded ${d.count ?? 0} supporting scan(s): <strong>${(d.files || []).join(', ')}</strong>`;
        } else if (ev.event === 'checks_run') {
          detailText = `Ran compliance checks (${d.mode || 'code'} mode) → Status: <strong>${d.overall || 'PENDING'}</strong> (${d.readiness_score ?? 0}% readiness)`;
        } else if (ev.event === 'checklist_generated') {
          detailText = `Customer checklist compiled in <strong>${(d.lang || 'en').toUpperCase()}</strong> (${d.gate || 'passed'} gate, source: ${d.source || 'template'})`;
        } else if (ev.event === 'draft_generated') {
          detailText = `Draft PDF generated (${d.disposition || 'inline'})`;
        } else if (ev.event === 'staff_review') {
          detailText = `Staff review by <strong>${d.staff_name || 'Staff'}</strong>${d.note ? `: "${d.note}"` : ''}`;
        } else {
          detailText = JSON.stringify(d);
        }

        return `
          <div class="relative pl-6 pb-2 group">
            <div class="absolute -left-[25px] top-0 w-6 h-6 rounded-full bg-white dark:bg-slate-900 border-2 border-amber-500 text-amber-600 dark:text-amber-400 flex items-center justify-center">
              <i data-lucide="${icon}" class="w-3 h-3"></i>
            </div>
            <div class="flex items-center gap-2 text-[11px] text-slate-400">
              <span class="font-mono">${dateStr} ${timeStr}</span>
              <span>•</span>
              <span class="uppercase font-bold tracking-wider text-[10px] text-slate-500 dark:text-slate-400">${ev.event.replace('_', ' ')}</span>
            </div>
            <div class="mt-1 text-slate-800 dark:text-slate-200">
              ${detailText}
            </div>
          </div>
        `;
      }).join('');

      if (window.lucide) window.lucide.createIcons();

    } catch (err) {
      container.innerHTML = `
        <div class="text-xs text-rose-500">Error loading audit: ${err.message}</div>
      `;
    }
  },

  async runChecks() {
    if (this.isChecking) return;
    this.isChecking = true;

    const btn = document.getElementById('case-run-checks-btn');
    const btnText = document.getElementById('case-run-btn-text');
    const spinner = document.getElementById('case-run-spinner');

    if (btn) btn.disabled = true;
    if (btnText) btnText.textContent = 'Running Checks (with LLM)…';
    if (spinner) spinner.classList.remove('hidden');

    try {
      const res = await fetch(`/api/check/${this.caseId}?use_llm=true`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to run regulatory and LLM checks');
      const report = await res.json();

      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show(
          'Checks Complete',
          `Case status: ${report.overall} (${report.readiness_score}% readiness)`,
          report.overall === 'READY' ? 'success' : report.overall === 'NOT_READY' ? 'error' : 'info'
        );
      }

      setTimeout(() => {
        window.location.reload();
      }, 500);

    } catch (err) {
      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Error', err.message, 'error');
      }
      if (btn) btn.disabled = false;
      if (btnText) btnText.textContent = 'Run Checks (with LLM)';
      if (spinner) spinner.classList.add('hidden');
      this.isChecking = false;
    }
  },

  updateGauge() {
    const gaugeNeedle = document.getElementById('gauge-needle');
    if (!gaugeNeedle) return;

    const proposed = parseFloat(gaugeNeedle.getAttribute('data-proposed') || '0');
    const sanctioned = parseFloat(gaugeNeedle.getAttribute('data-sanctioned') || '10');

    const maxVal = Math.max(sanctioned * 1.5, proposed * 1.1, 15);
    const ratio = Math.min(proposed / maxVal, 1.0);
    const degrees = -90 + (ratio * 180);

    requestAnimationFrame(() => {
      gaugeNeedle.style.transform = `rotate(${degrees}deg)`;
    });
  },

  openReviewModal() {
    const content = `
      <div class="space-y-4">
        <p class="text-xs text-slate-500 dark:text-slate-400">
          Record staff review confirmation. Note: This action is an internal audit step and does not submit or alter regulatory check verdicts.
        </p>
        <div>
          <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Staff Member Name *</label>
          <input id="review-staff-name" type="text" placeholder="e.g. Asim Munir" class="w-full text-xs px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-amber-500 focus:outline-none">
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Internal Onboarding Note (Optional)</label>
          <textarea id="review-staff-note" rows="3" placeholder="Verified customer identity and property papers..." class="w-full text-xs px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-amber-500 focus:outline-none"></textarea>
        </div>
      </div>
    `;

    window.NetBill.Modal.open('Mark Case Reviewed', content, async () => {
      const name = document.getElementById('review-staff-name')?.value.trim();
      const note = document.getElementById('review-staff-note')?.value.trim() || '';

      if (!name) {
        if (window.NetBill?.Toast) {
          window.NetBill.Toast.show('Validation Error', 'Staff name is required.', 'error');
        }
        return;
      }

      try {
        const res = await fetch(`/api/review/${this.caseId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ staff_name: name, note: note })
        });
        if (!res.ok) throw new Error('Failed to record staff review');

        if (window.NetBill?.Toast) {
          window.NetBill.Toast.show('Reviewed', `Review logged by ${name}.`, 'success');
        }
        setTimeout(() => window.location.reload(), 600);
      } catch (err) {
        if (window.NetBill?.Toast) {
          window.NetBill.Toast.show('Error', err.message, 'error');
        }
      }
    });
  },

  deleteCustomCase() {
    window.NetBill.Modal.open(
      `Delete Custom Case ${this.caseId}?`,
      `<p class="text-xs text-slate-600 dark:text-slate-300">Are you sure you want to permanently delete custom application pack <strong>${this.caseId}</strong> and its audit history?</p>`,
      async () => {
        try {
          const res = await fetch(`/api/cases/${this.caseId}`, { method: 'DELETE' });
          if (!res.ok) throw new Error('Failed to delete custom case');
          if (window.NetBill?.Toast) {
            window.NetBill.Toast.show('Case Deleted', `${this.caseId} was removed.`, 'success');
          }
          setTimeout(() => { window.location.href = '/'; }, 400);
        } catch (err) {
          if (window.NetBill?.Toast) {
            window.NetBill.Toast.show('Error', err.message, 'error');
          }
        }
      }
    );
  }
};

window.CasePage = CasePage;
