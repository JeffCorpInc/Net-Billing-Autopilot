/**
 * NetBill Assist - Case Page Client Engine
 * Handles check execution, SVG gauge needle animation, readiness ring update, and review modal.
 */

const CasePage = {
  caseId: '',
  isChecking: false,

  init(caseId) {
    this.caseId = caseId;
    this.bindEvents();
    this.updateGauge();
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
  },

  async runChecks() {
    if (this.isChecking) return;
    this.isChecking = true;

    const btn = document.getElementById('case-run-checks-btn');
    const btnText = document.getElementById('case-run-btn-text');
    const spinner = document.getElementById('case-run-spinner');

    if (btn) btn.disabled = true;
    if (btnText) btnText.textContent = 'Running Checks…';
    if (spinner) spinner.classList.remove('hidden');

    try {
      const res = await fetch(`/api/check/${this.caseId}?use_llm=false`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Failed to run regulatory checks');
      const report = await res.json();

      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show(
          'Checks Complete',
          `Case status: ${report.overall} (${report.readiness_score}% readiness)`,
          report.overall === 'READY' ? 'success' : report.overall === 'NOT_READY' ? 'error' : 'info'
        );
      }

      // Reload page to re-render all check states, gauges, outlines and badges
      setTimeout(() => {
        window.location.reload();
      }, 500);

    } catch (err) {
      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Error', err.message, 'error');
      }
      if (btn) btn.disabled = false;
      if (btnText) btnText.textContent = 'Run Checks';
      if (spinner) spinner.classList.add('hidden');
      this.isChecking = false;
    }
  },

  updateGauge() {
    const gaugeNeedle = document.getElementById('gauge-needle');
    if (!gaugeNeedle) return;

    const proposed = parseFloat(gaugeNeedle.getAttribute('data-proposed') || '0');
    const sanctioned = parseFloat(gaugeNeedle.getAttribute('data-sanctioned') || '10');

    // Semicircle gauge: 0 kW = -90deg, sanctioned = 0deg, 1.5*sanctioned = +90deg
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
  }
};

window.CasePage = CasePage;
