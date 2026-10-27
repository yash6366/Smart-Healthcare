/**
 * VakCare Shared Layout & Navigation Component
 * Injects responsive sidebar, topbar, notification badge, and profile drawer.
 */

import { Auth } from './auth.js';
import { api } from './api-client.js';
import { CONFIG, getAppPath } from './config.js';
import { ICONS, escapeHtml, showConfirmDialog } from './ui.js';

export const NAV_ITEMS = {
  PATIENT: [
    { label: 'Overview', path: '/pages/patient/dashboard.html', icon: ICONS.dashboard },
    { label: 'Find Doctors', path: '/pages/patient/doctors.html', icon: ICONS.doctors },
    { label: 'My Appointments', path: '/pages/patient/appointments.html', icon: ICONS.calendar },
    { label: 'Medical Records', path: '/pages/patient/medical-records.html', icon: ICONS.records },
    { label: 'Prescriptions', path: '/pages/patient/prescriptions.html', icon: ICONS.prescriptions },
    { label: 'AI Health Assistant', path: '/pages/patient/ai-assistant.html', icon: ICONS.ai },
    { label: 'Notifications', path: '/pages/patient/notifications.html', icon: ICONS.notifications, counterId: 'nav-notif-counter' },
    { label: 'My Profile', path: '/pages/patient/profile.html', icon: ICONS.user },
  ],
  DOCTOR: [
    { label: 'Overview', path: '/pages/doctor/dashboard.html', icon: ICONS.dashboard },
    { label: 'Consultations', path: '/pages/doctor/appointments.html', icon: ICONS.calendar },
    { label: 'My Patients', path: '/pages/doctor/patients.html', icon: ICONS.patients },
    { label: 'Medical Records', path: '/pages/doctor/medical-records.html', icon: ICONS.records },
    { label: 'Issue Prescription', path: '/pages/doctor/prescriptions.html', icon: ICONS.prescriptions },
    { label: 'Notifications', path: '/pages/patient/notifications.html', icon: ICONS.notifications, counterId: 'nav-notif-counter' },
    { label: 'Doctor Profile', path: '/pages/doctor/profile.html', icon: ICONS.user },
  ],
  ADMIN: [
    { label: 'Dashboard', path: '/pages/admin/dashboard.html', icon: ICONS.dashboard },
    { label: 'User Directory', path: '/pages/admin/users.html', icon: ICONS.patients },
    { label: 'Manage Doctors', path: '/pages/admin/doctors.html', icon: ICONS.doctors },
    { label: 'Patient Registry', path: '/pages/admin/patients.html', icon: ICONS.records },
    { label: 'All Appointments', path: '/pages/admin/appointments.html', icon: ICONS.calendar },
    { label: 'Compliance Audit', path: '/pages/admin/audit-logs.html', icon: ICONS.audit },
    { label: 'System Reports', path: '/pages/admin/reports.html', icon: ICONS.reports },
  ],
};

/**
 * Initializes and mounts shared application layout
 */
export async function initAppLayout({ title = 'Dashboard', subtitle = '', breadcrumbs = [] }) {
  const user = Auth.getUser();
  if (!user) return;

  const role = user.role;
  const navList = NAV_ITEMS[role] || [];
  const currentPath = window.location.pathname;

  // 1. Sidebar HTML
  const sidebarHtml = `
    <aside class="app-sidebar" id="appSidebar" role="navigation" aria-label="Main Navigation">
      <div class="sidebar-brand">
        <div class="brand-logo">${ICONS.logo}</div>
        <div class="brand-text">
          <span class="brand-name">${CONFIG.APP_NAME}</span>
          <span class="brand-role-tag">${escapeHtml(role)} PORTAL</span>
        </div>
      </div>

      <div class="sidebar-content">
        <div>
          <div class="nav-section-title">Navigation</div>
          <ul class="nav-list">
            ${navList
              .map((item) => {
                const itemPath = getAppPath(item.path);
                const isActive = currentPath.endsWith(item.path.replace(/^\//, '')) || currentPath === itemPath;
                return `
                  <li>
                    <a href="${itemPath}" class="nav-item-link ${isActive ? 'active' : ''}">
                      <span class="nav-icon">${item.icon}</span>
                      <span>${escapeHtml(item.label)}</span>
                      ${item.counterId ? `<span id="${item.counterId}" class="nav-counter hidden">0</span>` : ''}
                    </a>
                  </li>
                `;
              })
              .join('')}
          </ul>
        </div>
      </div>

      <div class="sidebar-footer">
        <div class="user-profile-preview">
          <div class="avatar">${escapeHtml((user.first_name?.[0] || user.username?.[0] || 'U').toUpperCase())}</div>
          <div class="user-profile-info">
            <span class="user-profile-name">${escapeHtml(user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user.username)}</span>
            <span class="user-profile-email">${escapeHtml(user.email)}</span>
          </div>
        </div>
        <button id="logoutBtn" class="btn-icon" title="Log Out" aria-label="Log Out">
          ${ICONS.logout}
        </button>
      </div>
    </aside>
  `;

  // Construct breadcrumbs
  const homeDashboard = role === 'PATIENT' ? '/pages/patient/dashboard.html' : role === 'DOCTOR' ? '/pages/doctor/dashboard.html' : '/pages/admin/dashboard.html';
  const breadcrumbHtml = Array.isArray(breadcrumbs) && breadcrumbs.length > 0
    ? `<nav class="breadcrumb" aria-label="Breadcrumb">
        ${breadcrumbs.map((b, idx) => {
          const isLast = idx === breadcrumbs.length - 1;
          if (isLast || !b.path) {
            return `<span class="breadcrumb-current">${escapeHtml(b.label)}</span>`;
          }
          return `<a href="${getAppPath(b.path)}">${escapeHtml(b.label)}</a><span class="breadcrumb-separator">/</span>`;
        }).join('')}
       </nav>`
    : `<nav class="breadcrumb" aria-label="Breadcrumb">
        <a href="${getAppPath(homeDashboard)}">${escapeHtml(role)} Portal</a>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">${escapeHtml(title)}</span>
       </nav>`;

  const profileUrl = role === 'DOCTOR' ? '/pages/doctor/profile.html' : role === 'PATIENT' ? '/pages/patient/profile.html' : '/pages/admin/dashboard.html';

  // 2. Topbar HTML
  const topbarHtml = `
    <header class="app-topbar" role="banner">
      <div class="topbar-left">
        <button id="mobileMenuToggle" class="mobile-menu-btn" aria-label="Toggle navigation menu" aria-controls="appSidebar" aria-expanded="false">
          ${ICONS.menu}
        </button>
        <div class="topbar-page-header">
          ${breadcrumbHtml}
          <h1 class="page-title">${escapeHtml(title)}</h1>
          ${subtitle ? `<span class="page-subtitle">${escapeHtml(subtitle)}</span>` : ''}
        </div>
      </div>

      <div class="topbar-right">
        <a href="${getAppPath('/pages/patient/notifications.html')}" class="notification-btn" id="topbarNotifBtn" aria-label="Notifications" title="Notifications">
          ${ICONS.notifications}
          <span class="notification-badge hidden" id="topbarNotifBadge">0</span>
        </a>

        <a href="${getAppPath(profileUrl)}" class="topbar-user-chip" title="View Profile">
          <div class="topbar-user-avatar">${escapeHtml((user.first_name?.[0] || user.username?.[0] || 'U').toUpperCase())}</div>
          <div class="topbar-user-details">
            <span class="topbar-user-name">${escapeHtml(user.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user.username)}</span>
            <span class="topbar-user-role">${escapeHtml(role)}</span>
          </div>
        </a>
      </div>
    </header>
  `;

  // Inject or wrap existing shell
  const shell = document.querySelector('.app-shell');
  if (shell) {
    shell.insertAdjacentHTML('afterbegin', sidebarHtml);

    const main = shell.querySelector('.app-main');
    if (main) {
      main.insertAdjacentHTML('afterbegin', topbarHtml);
    }
  }

  // 3. Setup event listeners
  setupLayoutEvents();

  // 4. Load unread notifications count if role is PATIENT or recipient
  loadUnreadNotificationsCount();
}

function setupLayoutEvents() {
  // Logout handler with confirmation
  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', async () => {
      const confirmed = await showConfirmDialog({
        title: 'Sign Out',
        message: 'Are you sure you want to end your current session?',
        confirmText: 'Sign Out',
        cancelText: 'Stay',
        isDanger: false,
      });
      if (confirmed) {
        await Auth.logout();
      }
    });
  }

  // Mobile drawer toggle & backdrop
  const mobileToggle = document.getElementById('mobileMenuToggle');
  const sidebar = document.getElementById('appSidebar');

  // Ensure backdrop exists
  let backdrop = document.getElementById('sidebarBackdrop');
  if (!backdrop) {
    backdrop = document.createElement('div');
    backdrop.id = 'sidebarBackdrop';
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);
  }

  const closeSidebar = () => {
    sidebar?.classList.remove('mobile-open');
    backdrop?.classList.remove('active');
    mobileToggle?.setAttribute('aria-expanded', 'false');
  };

  const openSidebar = () => {
    sidebar?.classList.add('mobile-open');
    backdrop?.classList.add('active');
    mobileToggle?.setAttribute('aria-expanded', 'true');
  };

  if (mobileToggle && sidebar) {
    mobileToggle.addEventListener('click', (e) => {
      e.stopPropagation();
      if (sidebar.classList.contains('mobile-open')) {
        closeSidebar();
      } else {
        openSidebar();
      }
    });

    backdrop.addEventListener('click', closeSidebar);

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && sidebar.classList.contains('mobile-open')) {
        closeSidebar();
      }
    });
  }
}

async function loadUnreadNotificationsCount() {
  try {
    const res = await api.get('/notifications/', { unread: 'true', page_size: 1 });
    const count = res.count || 0;

    const topBadge = document.getElementById('topbarNotifBadge');
    if (topBadge) {
      if (count > 0) {
        topBadge.textContent = count > 99 ? '99+' : count;
        topBadge.classList.remove('hidden');
      } else {
        topBadge.classList.add('hidden');
      }
    }

    const navBadge = document.getElementById('nav-notif-counter');
    if (navBadge) {
      if (count > 0) {
        navBadge.textContent = count;
        navBadge.classList.remove('hidden');
      } else {
        navBadge.classList.add('hidden');
      }
    }
  } catch (err) {
    // Graceful silent ignore if notifications check fails
  }
}
