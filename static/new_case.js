/**
 * NetBill Assist - Guided New & Edit Application Intake Script
 * Handles empty/preset form state, edit-mode pre-population, base64 file uploads,
 * existing file deletion, and POST / PUT submission.
 */

(function () {
  'use strict';

  let isEditMode = false;
  let editCaseId = '';
  let selectedFilesBuffer = []; // Array of File objects pending upload
  let hasScrolledToBottom = false;

  document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('new-case-root');
    if (root) {
      isEditMode = root.getAttribute('data-edit-mode') === 'true';
      editCaseId = root.getAttribute('data-case-id') || '';
    }

    const form = document.getElementById('new-case-form');
    const cleanBtn = document.getElementById('fill-clean-btn');
    const trapBtn = document.getElementById('fill-trap-btn');
    const heroClearBtn = document.getElementById('hero-clear-form-btn');
    const fileInput = document.getElementById('f-file-upload');
    const openConsentBtn = document.getElementById('open-consent-btn');
    const closeConsentBtn = document.getElementById('close-consent-btn');
    const cancelConsentBtn = document.getElementById('cancel-consent-btn');
    const consentScrollDownBtn = document.getElementById('consent-scroll-down-btn');
    const consentScrollBody = document.getElementById('consent-scroll-body');
    const consentCheckbox = document.getElementById('consent-agree-checkbox');

    // If in Edit Mode, populate form with existing pack data
    if (isEditMode && window.__INITIAL_PACK__) {
      populateFromPack(window.__INITIAL_PACK__);
    }

    // If redirected via hash (#f-...) from AI Assistant jump link, focus & highlight target field
    if (window.location.hash && window.location.hash.startsWith('#f-')) {
      const targetId = window.location.hash.substring(1);
      setTimeout(() => {
        const el = document.getElementById(targetId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          el.focus();
          el.classList.add('ring-2', 'ring-amber-500');
        }
      }, 250);
    }

    if (cleanBtn) cleanBtn.addEventListener('click', () => {
      fillCleanSample();
      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Clean Sample Loaded', 'Populated compliant 9.9 kW DHA application.', 'success');
      }
    });

    if (trapBtn) trapBtn.addEventListener('click', () => {
      fillTrapSample();
      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Trap Sample Loaded', 'Populated application with capacity & name mismatch violations.', 'info');
      }
    });

    if (heroClearBtn && form) {
      heroClearBtn.addEventListener('click', () => {
        form.reset();
        selectedFilesBuffer = [];
        renderSelectedFiles();
        hasScrolledToBottom = false;
        if (consentCheckbox) consentCheckbox.checked = false;
        if (consentScrollBody) consentScrollBody.scrollTop = 0;
        const ocrBanner = document.getElementById('ocr-status-banner');
        if (ocrBanner) ocrBanner.classList.add('hidden');
        updateConsentSubmitState();
        if (window.NetBill?.Toast) {
          window.NetBill.Toast.show('Form Cleared', 'All application fields and consent have been reset.', 'info');
        }
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', async (e) => {
        const incoming = Array.from(e.target.files || []);
        incoming.forEach(f => {
          if (!selectedFilesBuffer.some(existing => existing.name === f.name)) {
            selectedFilesBuffer.push(f);
          }
        });
        fileInput.value = ''; // Reset input so user can pick more files if desired
        renderSelectedFiles();
        if (incoming.length > 0) {
          await runAutoOcrOnFiles(incoming);
        }
      });
    }

    bindExistingFileDeleteButtons();

    // Consent Modal controls
    if (openConsentBtn) {
      openConsentBtn.addEventListener('click', () => {
        if (form && !form.reportValidity()) {
          return;
        }
        openConsentModal();
      });
    }

    if (closeConsentBtn) closeConsentBtn.addEventListener('click', closeConsentModal);
    if (cancelConsentBtn) cancelConsentBtn.addEventListener('click', closeConsentModal);

    if (consentScrollDownBtn) {
      consentScrollDownBtn.addEventListener('click', () => {
        if (consentScrollBody) {
          consentScrollBody.scrollTo({
            top: consentScrollBody.scrollHeight,
            behavior: 'smooth',
          });
        }
        hasScrolledToBottom = true;
        if (consentCheckbox) {
          consentCheckbox.checked = true;
        }
        updateConsentSubmitState();
      });
    }

    if (consentScrollBody) {
      consentScrollBody.addEventListener('scroll', () => {
        const atBottom =
          consentScrollBody.scrollTop + consentScrollBody.clientHeight >=
          consentScrollBody.scrollHeight - 24;
        if (atBottom) {
          hasScrolledToBottom = true;
          updateConsentSubmitState();
        }
      });
    }

    if (consentCheckbox) {
      consentCheckbox.addEventListener('change', () => {
        if (consentCheckbox.checked) {
          hasScrolledToBottom = true;
        }
        updateConsentSubmitState();
      });
    }

    if (form) {
      form.addEventListener('submit', submitCaseForm);
    }
  });

  function openConsentModal() {
    const modal = document.getElementById('consent-modal');
    const scrollBody = document.getElementById('consent-scroll-body');
    const checkbox = document.getElementById('consent-agree-checkbox');
    if (!modal) return;

    hasScrolledToBottom = false;
    if (checkbox) checkbox.checked = false;
    updateConsentSubmitState();

    modal.classList.remove('hidden');

    if (scrollBody) {
      scrollBody.scrollTop = 0;
    }
    if (window.lucide) window.lucide.createIcons({ root: modal });

    setTimeout(() => {
      modal.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 60);
  }

  function closeConsentModal() {
    const modal = document.getElementById('consent-modal');
    if (!modal) return;
    modal.classList.add('hidden');
  }

  function updateConsentSubmitState() {
    const submitBtn = document.getElementById('submit-new-case-btn');
    const checkbox = document.getElementById('consent-agree-checkbox');
    const hint = document.getElementById('consent-scroll-hint');
    const jumpBtn = document.getElementById('consent-scroll-down-btn');

    const isUnlocked = Boolean(hasScrolledToBottom && checkbox && checkbox.checked);

    if (submitBtn) {
      submitBtn.disabled = !isUnlocked;
    }

    if (hint) {
      if (isUnlocked) {
        hint.innerHTML = `<i data-lucide="check-circle-2" class="w-3.5 h-3.5 shrink-0 text-emerald-600 dark:text-emerald-400"></i><span class="text-emerald-700 dark:text-emerald-300">Consent verified! You may now click "Submit Application &amp; Run Compliance Checks" below.</span>`;
        if (window.lucide) window.lucide.createIcons({ root: hint });
      } else if (hasScrolledToBottom) {
        hint.innerHTML = `<i data-lucide="check-square" class="w-3.5 h-3.5 shrink-0"></i><span>Reached the bottom — check the confirmation box below to unlock final submission.</span>`;
        if (window.lucide) window.lucide.createIcons({ root: hint });
      } else {
        hint.innerHTML = `<i data-lucide="info" class="w-3.5 h-3.5 shrink-0"></i><span>Please read the complete undertaking to the bottom to unlock final submission.</span>`;
        if (window.lucide) window.lucide.createIcons({ root: hint });
      }
    }

    if (jumpBtn) {
      if (hasScrolledToBottom) {
        jumpBtn.classList.add('opacity-60');
      } else {
        jumpBtn.classList.remove('opacity-60');
      }
    }
  }

  function setVal(id, val) {
    const el = document.getElementById(id);
    if (el && val !== undefined && val !== null) el.value = val;
  }

  function populateFromPack(pack) {
    setVal('f-description', pack.description);
    setVal('f-applicant-type', pack.applicant_type || 'residential');
    if (pack.cnic) {
      setVal('f-cnic-name', pack.cnic.name);
      setVal('f-cnic-father', pack.cnic.father_name);
      setVal('f-cnic-no', pack.cnic.cnic_no);
      setVal('f-cnic-expiry', pack.cnic.expiry);
      setVal('f-cnic-address', pack.cnic.address);
    }
    if (pack.bill) {
      setVal('f-bill-name', pack.bill.consumer_name);
      setVal('f-bill-ref', pack.bill.reference_no);
      setVal('f-bill-tariff', pack.bill.tariff || 'A-1');
      setVal('f-sanctioned-kw', pack.bill.sanctioned_load_kw);
      setVal('f-connected-kw', pack.bill.connected_load_kw);
      setVal('f-phase', (pack.bill.connection_phase || '3-phase').toLowerCase());
      setVal('f-bill-address', pack.bill.address);
    }
    if (pack.ownership) {
      setVal('f-ownership-type', pack.ownership.type || 'sale_deed');
      setVal('f-owner-name', pack.ownership.owner_name);
      setVal('f-property-address', pack.ownership.property_address);
    }
    const tenantBox = document.getElementById('f-is-tenant');
    if (tenantBox) tenantBox.checked = Boolean(pack.is_tenant);

    if (pack.system) {
      setVal('f-proposed-kw', pack.system.proposed_kw);
      setVal('f-inverter-kw', pack.system.inverter_kw);
      setVal('f-panel-count', pack.system.panel_count);
      setVal('f-panel-watt', pack.system.panel_watt);
    }

    const docsSet = new Set(pack.docs_present || []);
    document.querySelectorAll('.doc-checkbox').forEach(cb => {
      cb.checked = docsSet.has(cb.value);
    });
  }

  function fillCleanSample() {
    setVal('f-description', 'Custom residential 9.9 kW net-billing application (DHA Phase 6)');
    setVal('f-applicant-type', 'residential');
    setVal('f-cnic-name', 'Muhammad Tariq Khan');
    setVal('f-cnic-father', 'Abdul Majeed Khan');
    setVal('f-cnic-no', '42301-7654321-3');
    setVal('f-cnic-expiry', '2031-08-15');
    setVal('f-cnic-address', 'House 42-C, Khayaban-e-Ittehad, Phase 6, DHA, Karachi');

    setVal('f-bill-name', 'M. Tariq Khan');
    setVal('f-bill-ref', '0400012398765');
    setVal('f-bill-tariff', 'A-1');
    setVal('f-sanctioned-kw', '10.0');
    setVal('f-connected-kw', '9.0');
    setVal('f-phase', '3-phase');
    setVal('f-bill-address', 'H.No 42-C, Kh-e-Ittehad, DHA Ph-VI, Karachi');

    setVal('f-ownership-type', 'sale_deed');
    setVal('f-owner-name', 'Muhammad Tariq Khan');
    const tenantBox = document.getElementById('f-is-tenant');
    if (tenantBox) tenantBox.checked = false;
    setVal('f-property-address', 'Plot No. 42-C, Khayaban-e-Ittehad, Phase VI, DHA, Karachi');

    setVal('f-proposed-kw', '9.9');
    setVal('f-inverter-kw', '10.0');
    setVal('f-panel-count', '18');
    setVal('f-panel-watt', '550');

    const baseDocs = new Set([
      'cnic', 'bill', 'ownership', 'single_line_diagram',
      'affidavit', 'vendor_checklist', 'inverter_datasheet', 'inverter_settings_letter'
    ]);
    document.querySelectorAll('.doc-checkbox').forEach(cb => {
      cb.checked = baseDocs.has(cb.value);
    });
  }

  function fillTrapSample() {
    setVal('f-description', 'Custom trap application: 15 kW system on 10 kW sanctioned load + different bill consumer');
    setVal('f-applicant-type', 'residential');
    setVal('f-cnic-name', 'Salman Ahmed Siddiqui');
    setVal('f-cnic-father', 'Riaz Ahmed Siddiqui');
    setVal('f-cnic-no', '42101-9988776-1');
    setVal('f-cnic-expiry', '2025-11-01');
    setVal('f-cnic-address', 'Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi');

    setVal('f-bill-name', 'Kamran Qureshi');
    setVal('f-bill-ref', '0400099887766');
    setVal('f-bill-tariff', 'A-1');
    setVal('f-sanctioned-kw', '10.0');
    setVal('f-connected-kw', '11.5');
    setVal('f-phase', '3-phase');
    setVal('f-bill-address', 'B-19, Blk 13-D, Gulshan-e-Iqbal, Karachi');

    setVal('f-ownership-type', 'sale_deed');
    setVal('f-owner-name', 'Salman Ahmed Siddiqui');
    const tenantBox = document.getElementById('f-is-tenant');
    if (tenantBox) tenantBox.checked = false;
    setVal('f-property-address', 'Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi');

    setVal('f-proposed-kw', '14.85');
    setVal('f-inverter-kw', '15.0');
    setVal('f-panel-count', '27');
    setVal('f-panel-watt', '550');

    const trapDocs = new Set([
      'cnic', 'bill', 'ownership',
      'affidavit', 'vendor_checklist', 'inverter_datasheet', 'inverter_settings_letter'
    ]);
    document.querySelectorAll('.doc-checkbox').forEach(cb => {
      cb.checked = trapDocs.has(cb.value);
    });
  }

  function renderSelectedFiles() {
    const listBox = document.getElementById('selected-files-list');
    if (!listBox) return;

    if (selectedFilesBuffer.length === 0) {
      listBox.innerHTML = '';
      return;
    }

    listBox.innerHTML = selectedFilesBuffer.map((f, idx) => `
      <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-medium">
        <i data-lucide="paperclip" class="w-3 h-3"></i>
        <span>${f.name} (${(f.size / 1024).toFixed(1)} KB)</span>
        <button type="button" data-remove-pending="${idx}" class="text-rose-500 hover:text-rose-700 ml-0.5" title="Remove from queue">
          <i data-lucide="x" class="w-3.5 h-3.5"></i>
        </button>
      </span>
    `).join('');

    listBox.querySelectorAll('[data-remove-pending]').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.getAttribute('data-remove-pending'), 10);
        selectedFilesBuffer.splice(i, 1);
        renderSelectedFiles();
      });
    });

    if (window.lucide) window.lucide.createIcons({ root: listBox });
  }

  function bindExistingFileDeleteButtons() {
    const box = document.getElementById('existing-files-container');
    if (!box) return;

    box.querySelectorAll('[data-del-file]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const filename = btn.getAttribute('data-del-file');
        if (!filename || !editCaseId) return;

        try {
          const res = await fetch(`/api/cases/${editCaseId}/files/${encodeURIComponent(filename)}`, {
            method: 'DELETE',
          });
          if (!res.ok) throw new Error('Failed to delete file');
          btn.closest('span')?.remove();
          if (window.NetBill?.Toast) {
            window.NetBill.Toast.show('File Removed', `Deleted ${filename}`, 'success');
          }
        } catch (err) {
          if (window.NetBill?.Toast) {
            window.NetBill.Toast.show('Error', err.message, 'error');
          }
        }
      });
    });
  }

  function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  async function runAutoOcrOnFiles(filesToScan) {
    const banner = document.getElementById('ocr-status-banner');
    if (banner) {
      banner.className = 'p-3 rounded-xl border border-amber-300 dark:border-amber-700 bg-amber-50/80 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200 text-xs font-semibold flex items-center justify-between gap-3';
      banner.innerHTML = `
        <div class="flex items-center gap-2">
          <span class="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin shrink-0"></span>
          <span>Running Backend OCR on ${filesToScan.length} uploaded file(s) &amp; auto-filling form fields…</span>
        </div>
      `;
    }

    try {
      const filesPayload = [];
      for (const f of filesToScan) {
        const b64 = await readFileAsBase64(f);
        filesPayload.push({
          name: f.name,
          size: f.size,
          type: f.type,
          content_base64: b64,
        });
      }

      const res = await fetch('/api/ocr/extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: filesPayload }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'OCR extraction failed');
      }

      const fields = data.fields || {};
      const docsDetected = data.docs_detected || [];

      const fieldIdMap = {
        description: 'f-description',
        applicant_type: 'f-applicant-type',
        cnic_name: 'f-cnic-name',
        cnic_father: 'f-cnic-father',
        cnic_no: 'f-cnic-no',
        cnic_expiry: 'f-cnic-expiry',
        cnic_address: 'f-cnic-address',
        bill_name: 'f-bill-name',
        bill_ref: 'f-bill-ref',
        bill_tariff: 'f-bill-tariff',
        sanctioned_kw: 'f-sanctioned-kw',
        connected_kw: 'f-connected-kw',
        phase: 'f-phase',
        bill_address: 'f-bill-address',
        ownership_type: 'f-ownership-type',
        owner_name: 'f-owner-name',
        property_address: 'f-property-address',
        proposed_kw: 'f-proposed-kw',
        inverter_kw: 'f-inverter-kw',
        panel_count: 'f-panel-count',
        panel_watt: 'f-panel-watt',
      };

      let filledCount = 0;
      Object.entries(fieldIdMap).forEach(([key, domId]) => {
        if (fields[key] !== undefined && fields[key] !== null && fields[key] !== '') {
          const el = document.getElementById(domId);
          if (el) {
            el.value = String(fields[key]);
            el.classList.add('ring-2', 'ring-emerald-500', 'bg-emerald-50/40');
            setTimeout(() => {
              el.classList.remove('ring-emerald-500', 'bg-emerald-50/40');
            }, 3000);
            filledCount++;
          }
        }
      });

      if (typeof fields.is_tenant === 'boolean') {
        const tenantBox = document.getElementById('f-is-tenant');
        if (tenantBox) {
          tenantBox.checked = fields.is_tenant;
          filledCount++;
        }
      }

      // Check detected document checkboxes in Step 4
      if (docsDetected.length > 0) {
        const docSet = new Set(docsDetected);
        document.querySelectorAll('.doc-checkbox').forEach(cb => {
          if (docSet.has(cb.value)) {
            cb.checked = true;
          }
        });
      }

      if (banner) {
        const warnHtml = (data.warnings && data.warnings.length > 0)
          ? `<div class="mt-1 text-[11px] text-amber-700 dark:text-amber-300 font-medium">⚠ ${data.warnings.join(' · ')}</div>`
          : '';
        banner.className = 'p-3 rounded-xl border border-emerald-300 dark:border-emerald-800 bg-emerald-50/90 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-200 text-xs font-semibold flex flex-col gap-1';
        banner.innerHTML = `
          <div class="flex items-center justify-between gap-2">
            <span class="flex items-center gap-1.5">
              <i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0"></i>
              <span>${data.summary || `Auto-filled ${filledCount} field(s) via Backend OCR.`}</span>
            </span>
            <span class="font-mono text-[10px] px-2 py-0.5 rounded bg-emerald-500/20">${data.elapsed_ms || 1} ms</span>
          </div>
          ${warnHtml}
        `;
        if (window.lucide) window.lucide.createIcons({ root: banner });
      }

      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show(
          'OCR Auto-Fill Complete',
          `Populated ${filledCount} form field(s) and ${docsDetected.length} document checkbox(es).`,
          'success'
        );
      }

      // Trigger AI Copilot background inspection on the newly OCR-populated fields
      if (window.AssistantCopilot?.silentBackgroundCheck) {
        window.AssistantCopilot.silentBackgroundCheck();
      }
    } catch (err) {
      if (banner) {
        banner.className = 'p-3 rounded-xl border border-rose-300 dark:border-rose-800 bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 text-xs font-semibold';
        banner.textContent = `OCR Error: ${err.message}`;
      }
    }
  }

  async function submitCaseForm(e) {
    e.preventDefault();

    // Enforce consent gate before allowing submission
    const consentCheckbox = document.getElementById('consent-agree-checkbox');
    if (!hasScrolledToBottom || (consentCheckbox && !consentCheckbox.checked)) {
      openConsentModal();
      return;
    }

    const btn = document.getElementById('submit-new-case-btn');
    const spinner = document.getElementById('submit-spinner');
    const btnText = document.getElementById('submit-btn-text');

    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');
    if (btnText) btnText.textContent = isEditMode ? 'Saving Changes & Re-Running Checks…' : 'Creating Pack & Running Checks…';

    const docsPresent = Array.from(document.querySelectorAll('.doc-checkbox:checked')).map(cb => cb.value);

    const payload = {
      description: document.getElementById('f-description')?.value.trim() || 'Custom net-billing application',
      applicant_type: document.getElementById('f-applicant-type')?.value || 'residential',
      is_tenant: Boolean(document.getElementById('f-is-tenant')?.checked),
      docs_present: docsPresent,
      cnic: {
        name: document.getElementById('f-cnic-name')?.value.trim(),
        father_name: document.getElementById('f-cnic-father')?.value.trim(),
        cnic_no: document.getElementById('f-cnic-no')?.value.trim(),
        expiry: document.getElementById('f-cnic-expiry')?.value.trim(),
        address: document.getElementById('f-cnic-address')?.value.trim(),
      },
      bill: {
        consumer_name: document.getElementById('f-bill-name')?.value.trim(),
        reference_no: document.getElementById('f-bill-ref')?.value.trim(),
        sanctioned_load_kw: parseFloat(document.getElementById('f-sanctioned-kw')?.value || '10'),
        connected_load_kw: parseFloat(document.getElementById('f-connected-kw')?.value || '8'),
        tariff: document.getElementById('f-bill-tariff')?.value || 'A-1',
        connection_phase: document.getElementById('f-phase')?.value || '3-phase',
        address: document.getElementById('f-bill-address')?.value.trim(),
      },
      ownership: {
        type: document.getElementById('f-ownership-type')?.value || 'sale_deed',
        owner_name: document.getElementById('f-owner-name')?.value.trim(),
        property_address: document.getElementById('f-property-address')?.value.trim(),
      },
      system: {
        proposed_kw: parseFloat(document.getElementById('f-proposed-kw')?.value || '10'),
        inverter_kw: parseFloat(document.getElementById('f-inverter-kw')?.value || '10'),
        panel_count: parseInt(document.getElementById('f-panel-count')?.value || '18', 10),
        panel_watt: parseInt(document.getElementById('f-panel-watt')?.value || '550', 10),
      },
    };

    try {
      const endpoint = isEditMode ? `/api/cases/${editCaseId}` : '/api/cases';
      const method = isEditMode ? 'PUT' : 'POST';

      const res = await fetch(endpoint, {
        method: method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to save application pack');
      }

      const caseId = data.case_id;

      // Upload attached files with real binary content if user selected files
      if (selectedFilesBuffer.length > 0) {
        const filesPayload = [];
        for (const f of selectedFilesBuffer) {
          const b64 = await readFileAsBase64(f);
          filesPayload.push({
            name: f.name,
            size: f.size,
            type: f.type,
            content_base64: b64,
          });
        }
        await fetch(`/api/cases/${caseId}/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ files: filesPayload }),
        });
      }

      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show(
          isEditMode ? 'Application Updated' : 'Application Created',
          `Case ${caseId} saved and checked! Redirecting…`,
          'success'
        );
      }

      setTimeout(() => {
        window.location.href = `/case/${caseId}`;
      }, 400);

    } catch (err) {
      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Submission Error', err.message, 'error');
      }
      if (btn) btn.disabled = false;
      if (spinner) spinner.classList.add('hidden');
      if (btnText) {
        btnText.textContent = isEditMode
          ? 'Save Changes & Re-Run Compliance Checks'
          : 'Create Application & Run Compliance Checks';
      }
    }
  }
})();
