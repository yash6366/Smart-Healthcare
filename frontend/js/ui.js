/**
 * VakCare UI Helper Utilities
 * Toast alerts, modal dialogs, status badges, SVG icon definitions, formatting.
 */

export const ICONS = {
  logo: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M2 12h20M7 7l10 10M17 7 7 17"/></svg>`,
  dashboard: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>`,
  calendar: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>`,
  doctors: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/><path d="M12 11v4M10 13h4"/></svg>`,
  patients: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
  records: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" x2="8" y1="13" y2="13"/><line x1="16" x2="8" y1="17" y2="17"/><line x1="10" x2="8" y1="9" y2="9"/></svg>`,
  prescriptions: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m10.5 20.5 10-10a4.95 4.95 0 1 0-7-7l-10 10a4.95 4.95 0 1 0 7 7Z"/><path d="m8.5 8.5 7 7"/></svg>`,
  ai: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>`,
  notifications: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>`,
  audit: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>`,
  reports: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>`,
  user: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>`,
  logout: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>`,
  search: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" x2="16.65" y1="21" y2="16.65"/></svg>`,
  plus: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="5" y2="19"/><line x1="5" x2="19" y1="12" y2="12"/></svg>`,
  check: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>`,
  x: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>`,
  menu: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>`,
  alert: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>`,
};

/**
 * Toast Notifications
 */
let toastContainer = null;

export function showToast(message, type = 'info', duration = 4000) {
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.setAttribute('role', 'alert');

  let iconSvg = ICONS.records;
  if (type === 'success') iconSvg = ICONS.check;
  if (type === 'error') iconSvg = ICONS.alert;

  toast.innerHTML = `
    <span style="flex-shrink:0;">${iconSvg}</span>
    <span style="flex:1;">${escapeHtml(message)}</span>
  `;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 200ms ease';
    setTimeout(() => toast.remove(), 250);
  }, duration);
}

/**
 * Confirmation Dialog
 */
export function showConfirmDialog({
  title = 'Please Confirm',
  message = 'Are you sure you want to proceed?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDanger = false,
}) {
  return new Promise((resolve) => {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop active';

    backdrop.innerHTML = `
      <div class="modal-dialog" role="dialog" aria-modal="true" style="max-width: 440px;">
        <div class="modal-header">
          <h3 class="card-title">${escapeHtml(title)}</h3>
          <button class="btn-icon modal-close" aria-label="Close dialog">${ICONS.x}</button>
        </div>
        <div class="modal-body">
          <p style="color: var(--color-text-muted); line-height: 1.5;">${escapeHtml(message)}</p>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline modal-cancel">${escapeHtml(cancelText)}</button>
          <button class="btn ${isDanger ? 'btn-danger' : 'btn-primary'} modal-confirm">${escapeHtml(confirmText)}</button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);

    const close = (result) => {
      backdrop.classList.remove('active');
      setTimeout(() => backdrop.remove(), 200);
      resolve(result);
    };

    backdrop.querySelector('.modal-close').onclick = () => close(false);
    backdrop.querySelector('.modal-cancel').onclick = () => close(false);
    backdrop.querySelector('.modal-confirm').onclick = () => close(true);
    backdrop.onclick = (e) => {
      if (e.target === backdrop) close(false);
    };
  });
}

/**
 * Prompt Dialog (Accessible replacement for window.prompt)
 */
export function showPromptDialog({
  title = 'Input Required',
  message = 'Please provide details:',
  placeholder = 'Enter value...',
  defaultValue = '',
  confirmText = 'Submit',
  cancelText = 'Cancel',
  isDanger = false,
  required = false,
  inputType = 'textarea',
}) {
  return new Promise((resolve) => {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop active';

    const inputHtml = inputType === 'textarea'
      ? `<textarea id="promptDialogInput" class="form-control" rows="3" placeholder="${escapeHtml(placeholder)}" style="width:100%; resize:vertical; font-family: inherit;">${escapeHtml(defaultValue)}</textarea>`
      : `<input id="promptDialogInput" class="form-control" type="text" placeholder="${escapeHtml(placeholder)}" value="${escapeHtml(defaultValue)}" style="width:100%;" />`;

    backdrop.innerHTML = `
      <div class="modal-dialog" role="dialog" aria-modal="true" style="max-width: 480px;">
        <div class="modal-header">
          <h3 class="card-title">${escapeHtml(title)}</h3>
          <button class="btn-icon modal-close" aria-label="Close dialog">${ICONS.x}</button>
        </div>
        <div class="modal-body" style="display:flex; flex-direction:column; gap: var(--space-3);">
          <p style="color: var(--color-text-muted); line-height: 1.5; margin-bottom: 0;">${escapeHtml(message)}</p>
          ${inputHtml}
          <div id="promptDialogError" style="display:none; color: var(--color-danger); font-size: var(--text-xs); font-weight: 500;"></div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-outline modal-cancel">${escapeHtml(cancelText)}</button>
          <button class="btn ${isDanger ? 'btn-danger' : 'btn-primary'} modal-confirm">${escapeHtml(confirmText)}</button>
        </div>
      </div>
    `;

    document.body.appendChild(backdrop);
    const inputEl = backdrop.querySelector('#promptDialogInput');
    const errEl = backdrop.querySelector('#promptDialogError');
    setTimeout(() => inputEl?.focus(), 50);

    const close = (result) => {
      backdrop.classList.remove('active');
      setTimeout(() => backdrop.remove(), 200);
      resolve(result);
    };

    const handleConfirm = () => {
      const val = inputEl ? inputEl.value.trim() : '';
      if (required && !val) {
        if (errEl) {
          errEl.textContent = 'This field is required.';
          errEl.style.display = 'block';
        }
        inputEl?.focus();
        return;
      }
      close(val);
    };

    backdrop.querySelector('.modal-close').onclick = () => close(null);
    backdrop.querySelector('.modal-cancel').onclick = () => close(null);
    backdrop.querySelector('.modal-confirm').onclick = handleConfirm;
    backdrop.onclick = (e) => {
      if (e.target === backdrop) close(null);
    };

    inputEl?.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey || inputType !== 'textarea')) {
        e.preventDefault();
        handleConfirm();
      } else if (e.key === 'Escape') {
        close(null);
      }
    });
  });
}


/**
 * Status Badge Renderer
 */
export function renderStatusBadge(status) {
  const s = String(status || '').toUpperCase();
  let badgeClass = 'badge-neutral';
  let label = status;

  if (s === 'PENDING') {
    badgeClass = 'badge-pending';
    label = 'Pending Confirmation';
  } else if (s === 'CONFIRMED' || s === 'ACTIVE' || s === 'VERIFIED') {
    badgeClass = 'badge-confirmed';
    label = s === 'CONFIRMED' ? 'Confirmed' : s === 'ACTIVE' ? 'Active' : 'Verified';
  } else if (s === 'COMPLETED') {
    badgeClass = 'badge-completed';
    label = 'Completed';
  } else if (s === 'REJECTED' || s === 'CANCELLED') {
    badgeClass = 'badge-rejected';
    label = s === 'REJECTED' ? 'Rejected' : 'Cancelled';
  }

  return `<span class="badge ${badgeClass}">${escapeHtml(label)}</span>`;
}

/**
 * Empty State Component
 */
export function renderEmptyState({
  icon = ICONS.records,
  title = 'No Records Found',
  message = 'There are no items to display at this time.',
  actionText = null,
  actionId = null,
}) {
  return `
    <div class="empty-state">
      <div class="empty-icon">${icon}</div>
      <h3 class="empty-title">${escapeHtml(title)}</h3>
      <p class="empty-text">${escapeHtml(message)}</p>
      ${actionText && actionId ? `<button id="${actionId}" class="btn btn-primary btn-sm">${escapeHtml(actionText)}</button>` : ''}
    </div>
  `;
}

/**
 * Sanitization
 */
export function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  const div = document.createElement('div');
  div.textContent = String(str);
  return div.innerHTML;
}

/**
 * Date & Time formatters
 */
export function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

export function formatTime(timeStr) {
  if (!timeStr) return '—';
  try {
    const parts = timeStr.split(':');
    let hours = parseInt(parts[0], 10);
    const minutes = parts[1] || '00';
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    return `${hours}:${minutes} ${ampm}`;
  } catch {
    return timeStr;
  }
}

export function formatCurrency(amount) {
  if (amount === undefined || amount === null) return '—';
  return `₹${parseFloat(amount).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
}
