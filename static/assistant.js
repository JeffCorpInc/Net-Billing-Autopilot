/**
 * NetBill Assist - AI Onboarding Copilot Client Engine
 * Active ONLY on New/Edit Application (/new, /case/U*/edit) and Custom User Cases (/case/U*).
 * Reads live form fields (or saved custom pack), calls POST /api/assistant/chat,
 * renders guidance, and highlights/scrolls to wrong form fields on click.
 */

(function () {
  'use strict';

  const AssistantCopilot = {
    caseId: 'DRAFT',
    contextMode: 'form', // 'form' or 'case_view'
    isOpen: false,
    isBusy: false,

    init() {
      const root = document.getElementById('ai-assistant-root');
      if (!root || root.getAttribute('data-initialized') === 'true') return;
      root.setAttribute('data-initialized', 'true');

      this.caseId = root.getAttribute('data-case-id') || 'DRAFT';
      this.contextMode = root.getAttribute('data-context-mode') || 'form';

      const form = document.getElementById('ai-assistant-form');

      if (form) {
        form.addEventListener('submit', (e) => {
          e.preventDefault();
          const input = document.getElementById('ai-assistant-input');
          const msg = input?.value.trim();
          if (!msg) return;
          input.value = '';
          this.sendPrompt(msg);
        });
      }

      root.querySelectorAll('[data-ai-prompt]').forEach(chip => {
        chip.addEventListener('click', () => {
          const prompt = chip.getAttribute('data-ai-prompt');
          if (prompt) this.sendPrompt(prompt);
        });
      });

      // If on the New/Edit form, attach blur/change listeners to update the live issue badge
      if (this.contextMode === 'form') {
        const appForm = document.getElementById('new-case-form');
        if (appForm) {
          let debounceTimer = null;
          appForm.addEventListener('change', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => this.silentBackgroundCheck(), 600);
          });
        }
        // Hook into sample preset buttons if clicked
        ['fill-clean-btn', 'fill-trap-btn'].forEach(btnId => {
          const b = document.getElementById(btnId);
          if (b) {
            b.addEventListener('click', () => {
              setTimeout(() => {
                this.openPanel();
                this.sendPrompt('Analyze the fields I just entered and tell me if there are any wrong entries or mismatches.');
              }, 250);
            });
          }
        });
      } else {
        // On a custom user case page (/case/U01), do an initial silent check to populate the issue badge
        setTimeout(() => this.silentBackgroundCheck(), 400);
      }
    },

    togglePanel() {
      if (this.isOpen) {
        this.closePanel();
      } else {
        this.openPanel();
      }
    },

    openPanel() {
      const panel = document.getElementById('ai-assistant-panel');
      if (!panel) return;
      panel.style.display = 'flex';
      this.isOpen = true;
      if (window.lucide) window.lucide.createIcons({ root: panel });
    },

    closePanel() {
      const panel = document.getElementById('ai-assistant-panel');
      if (!panel) return;
      panel.style.display = 'none';
      this.isOpen = false;
    },

    collectLiveDraftState() {
      if (this.contextMode !== 'form') {
        return null; // Backend will load the saved custom pack for case_id
      }

      const docsPresent = Array.from(document.querySelectorAll('.doc-checkbox:checked')).map(cb => cb.value);

      return {
        description: document.getElementById('f-description')?.value.trim() || '',
        applicant_type: document.getElementById('f-applicant-type')?.value || 'residential',
        is_tenant: Boolean(document.getElementById('f-is-tenant')?.checked),
        docs_present: docsPresent,
        cnic: {
          name: document.getElementById('f-cnic-name')?.value.trim() || '',
          father_name: document.getElementById('f-cnic-father')?.value.trim() || '',
          cnic_no: document.getElementById('f-cnic-no')?.value.trim() || '',
          expiry: document.getElementById('f-cnic-expiry')?.value.trim() || '',
          address: document.getElementById('f-cnic-address')?.value.trim() || '',
        },
        bill: {
          consumer_name: document.getElementById('f-bill-name')?.value.trim() || '',
          reference_no: document.getElementById('f-bill-ref')?.value.trim() || '',
          sanctioned_load_kw: document.getElementById('f-sanctioned-kw')?.value || '',
          connected_load_kw: document.getElementById('f-connected-kw')?.value || '',
          tariff: document.getElementById('f-bill-tariff')?.value || 'A-1',
          connection_phase: document.getElementById('f-phase')?.value || '3-phase',
          address: document.getElementById('f-bill-address')?.value.trim() || '',
        },
        ownership: {
          type: document.getElementById('f-ownership-type')?.value || 'sale_deed',
          owner_name: document.getElementById('f-owner-name')?.value.trim() || '',
          property_address: document.getElementById('f-property-address')?.value.trim() || '',
        },
        system: {
          proposed_kw: document.getElementById('f-proposed-kw')?.value || '',
          inverter_kw: document.getElementById('f-inverter-kw')?.value || '',
          panel_count: document.getElementById('f-panel-count')?.value || '',
          panel_watt: document.getElementById('f-panel-watt')?.value || '',
        },
      };
    },

    async silentBackgroundCheck() {
      try {
        const res = await fetch('/api/assistant/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            case_id: this.caseId,
            message: 'Quick status check',
            draft_state: this.collectLiveDraftState(),
          }),
        });
        if (!res.ok) return;
        const data = await res.json();
        this.updateIssueBadge(data.issues?.length || 0);
        this.highlightFormFields(data.issues || []);
      } catch {}
    },

    updateIssueBadge(issueCount) {
      const badge = document.getElementById('ai-assistant-badge');
      if (!badge) return;
      if (issueCount > 0) {
        badge.textContent = `${issueCount}`;
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    },

    highlightFormFields(issues) {
      if (this.contextMode !== 'form') return;

      // Clear previous assistant rings
      document.querySelectorAll('.ai-field-error').forEach(el => {
        el.classList.remove('ai-field-error', 'ring-2', 'ring-rose-500', 'border-rose-500');
      });

      issues.forEach(iss => {
        if (!iss.field_id) return;
        const fieldEl = document.getElementById(iss.field_id);
        if (fieldEl) {
          fieldEl.classList.add('ai-field-error', 'ring-2', 'ring-rose-500', 'border-rose-500');
        }
      });
    },

    focusField(fieldId) {
      if (this.contextMode !== 'form') {
        // On /case/U01 view, navigate to /case/U01/edit and focus the field
        window.location.href = `/case/${this.caseId}/edit#${fieldId}`;
        return;
      }
      const el = document.getElementById(fieldId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.focus();
        el.classList.add('ring-2', 'ring-amber-500');
        setTimeout(() => el.classList.remove('ring-amber-500'), 2000);
      }
    },

    formatMarkdown(text) {
      if (!text) return '';
      return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
    },

    appendMessage(role, htmlContent) {
      const box = document.getElementById('ai-assistant-messages');
      if (!box) return null;

      const msgEl = document.createElement('div');
      if (role === 'user') {
        msgEl.className = 'ml-8 p-2.5 rounded-2xl bg-amber-500 text-slate-950 font-semibold leading-snug shadow-sm';
      } else {
        msgEl.className = 'mr-4 p-3 rounded-2xl bg-slate-100 dark:bg-slate-800/90 text-slate-800 dark:text-slate-100 leading-relaxed border border-slate-200/70 dark:border-slate-700/70 space-y-2';
      }
      msgEl.innerHTML = htmlContent;
      box.appendChild(msgEl);
      box.scrollTop = box.scrollHeight;
      if (window.lucide) window.lucide.createIcons({ root: msgEl });
      return msgEl;
    },

    async sendPrompt(userText) {
      if (this.isBusy) return;
      this.openPanel();
      this.isBusy = true;

      this.appendMessage('user', this.formatMarkdown(userText));
      const loadingEl = this.appendMessage(
        'assistant',
        `<div class="flex items-center gap-2 text-slate-400">
           <span class="w-3.5 h-3.5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin"></span>
           <span>Checking rules &amp; consulting AI Copilot…</span>
         </div>`
      );

      try {
        const res = await fetch('/api/assistant/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            case_id: this.caseId,
            message: userText,
            draft_state: this.collectLiveDraftState(),
          }),
        });

        const data = await res.json();
        if (loadingEl) loadingEl.remove();

        if (!res.ok) {
          throw new Error(data.detail || 'Assistant request failed');
        }

        const issues = data.issues || [];
        this.updateIssueBadge(issues.length);
        this.highlightFormFields(issues);

        let issueChipsHtml = '';
        if (issues.length > 0) {
          issueChipsHtml = `
            <div class="pt-2 border-t border-slate-200 dark:border-slate-700 space-y-1.5">
              <div class="text-[10px] font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                Click to jump &amp; fix (${issues.length}):
              </div>
              <div class="flex flex-wrap gap-1.5">
                ${issues.map(iss => `
                  <button type="button" data-jump-field="${iss.field_id || ''}"
                          class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-50 dark:bg-rose-950/60 hover:bg-rose-100 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 inline-flex items-center gap-1 transition-colors">
                    <span>[${iss.rule_id}] ${iss.title}</span>
                    <i data-lucide="arrow-up-right" class="w-3 h-3"></i>
                  </button>
                `).join('')}
              </div>
            </div>
          `;
        }

        const metaFooter = `
          <div class="pt-1 flex items-center justify-between text-[10px] text-slate-400 font-mono">
            <span>Engine: ${data.source || 'llm'} (${data.model || 'gemini'})</span>
            <span>${data.latency_ms ?? 0} ms</span>
          </div>
        `;

        const msgNode = this.appendMessage(
          'assistant',
          `<div>${this.formatMarkdown(data.reply)}</div>${issueChipsHtml}${metaFooter}`
        );

        if (msgNode) {
          msgNode.querySelectorAll('[data-jump-field]').forEach(btn => {
            btn.addEventListener('click', () => {
              const fid = btn.getAttribute('data-jump-field');
              if (fid) this.focusField(fid);
            });
          });
        }

      } catch (err) {
        if (loadingEl) loadingEl.remove();
        this.appendMessage(
          'assistant',
          `<span class="text-rose-500 font-semibold">Error: ${this.formatMarkdown(err.message)}</span>`
        );
      } finally {
        this.isBusy = false;
      }
    }
  };

  window.AssistantCopilot = AssistantCopilot;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => AssistantCopilot.init());
  } else {
    AssistantCopilot.init();
  }
})();

