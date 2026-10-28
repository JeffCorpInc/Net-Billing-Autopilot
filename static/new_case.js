/**
 * NetBill Assist - Guided New Application Intake Script
 * Handles sample preset population, file attachment preview, and POST /api/cases submission.
 */

(function () {
  'use strict';

  document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('new-case-form');
    const cleanBtn = document.getElementById('fill-clean-btn');
    const trapBtn = document.getElementById('fill-trap-btn');
    const fileInput = document.getElementById('f-file-upload');

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

    if (fileInput) {
      fileInput.addEventListener('change', renderSelectedFiles);
    }

    if (form) {
      form.addEventListener('submit', submitNewCase);
    }
  });

  function setVal(id, val) {
    const el = document.getElementById(id);
    if (el) el.value = val;
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
    setVal('f-cnic-expiry', '2025-11-01'); // Expired CNIC
    setVal('f-cnic-address', 'Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi');

    setVal('f-bill-name', 'Kamran Qureshi'); // Different person (L1 FAIL)
    setVal('f-bill-ref', '0400099887766');
    setVal('f-bill-tariff', 'A-1');
    setVal('f-sanctioned-kw', '10.0');
    setVal('f-connected-kw', '11.5'); // Connected > Sanctioned (R5 FAIL)
    setVal('f-phase', '3-phase');
    setVal('f-bill-address', 'B-19, Blk 13-D, Gulshan-e-Iqbal, Karachi');

    setVal('f-ownership-type', 'sale_deed');
    setVal('f-owner-name', 'Salman Ahmed Siddiqui');
    const tenantBox = document.getElementById('f-is-tenant');
    if (tenantBox) tenantBox.checked = false;
    setVal('f-property-address', 'Bungalow B-19, Block 13-D, Gulshan-e-Iqbal, Karachi');

    setVal('f-proposed-kw', '14.85'); // Exceeds 10 kW sanctioned load (R3 FAIL)
    setVal('f-inverter-kw', '15.0');
    setVal('f-panel-count', '27');
    setVal('f-panel-watt', '550');

    const trapDocs = new Set([
      'cnic', 'bill', 'ownership',
      'affidavit', 'vendor_checklist', 'inverter_datasheet', 'inverter_settings_letter'
      // Missing single_line_diagram (R7 FAIL)
    ]);
    document.querySelectorAll('.doc-checkbox').forEach(cb => {
      cb.checked = trapDocs.has(cb.value);
    });
  }

  function renderSelectedFiles() {
    const fileInput = document.getElementById('f-file-upload');
    const listBox = document.getElementById('selected-files-list');
    if (!fileInput || !listBox) return;

    const files = Array.from(fileInput.files || []);
    if (files.length === 0) {
      listBox.innerHTML = '';
      return;
    }

    listBox.innerHTML = files.map(f => `
      <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 font-medium">
        <i data-lucide="paperclip" class="w-3 h-3"></i>
        <span>${f.name} (${(f.size / 1024).toFixed(1)} KB)</span>
      </span>
    `).join('');

    if (window.lucide) window.lucide.createIcons({ root: listBox });
  }

  async function submitNewCase(e) {
    e.preventDefault();

    const btn = document.getElementById('submit-new-case-btn');
    const spinner = document.getElementById('submit-spinner');
    const btnText = document.getElementById('submit-btn-text');

    if (btn) btn.disabled = true;
    if (spinner) spinner.classList.remove('hidden');
    if (btnText) btnText.textContent = 'Creating Pack & Running Checks…';

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
      const res = await fetch('/api/cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create application pack');
      }

      const caseId = data.case_id;

      // Upload attached file metadata if user selected files
      const fileInput = document.getElementById('f-file-upload');
      const files = Array.from(fileInput?.files || []);
      if (files.length > 0) {
        await fetch(`/api/cases/${caseId}/upload`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            files: files.map(f => ({ name: f.name, size: f.size, type: f.type }))
          }),
        });
      }

      if (window.NetBill?.Toast) {
        window.NetBill.Toast.show('Application Created', `Case ${caseId} created and checked! Redirecting…`, 'success');
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
      if (btnText) btnText.textContent = 'Create Application & Run Compliance Checks';
    }
  }
})();

