/**
 * VakCare Authentication & Session Manager
 * Handles login, registration, logout, role determination, and route protection.
 */

import { api } from './api-client.js';
import { CONFIG, getAppPath } from './config.js';

export const Auth = {
  /**
   * Log in user with email/username and password
   */
  async login(emailOrUsername, password) {
    const response = await api.post('/auth/login/', {
      email_or_username: emailOrUsername,
      password: password,
    });

    if (response.tokens && response.user) {
      api.setTokens(response.tokens.access, response.tokens.refresh);
      localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(response.user));
    }

    return response;
  },

  /**
   * Register a new patient account
   */
  async register(registrationData) {
    return await api.post('/auth/register/', registrationData);
  },

  /**
   * Blacklist refresh token and log out
   */
  async logout() {
    const refreshToken = api.getRefreshToken();
    try {
      if (refreshToken) {
        await api.post('/auth/logout/', { refresh: refreshToken });
      }
    } catch (err) {
      console.warn('Backend logout notification failed, clearing local session:', err);
    } finally {
      api.clearTokens();
      window.location.href = getAppPath('/login.html');
    }
  },

  /**
   * Retrieve cached user details
   */
  getUser() {
    try {
      const data = localStorage.getItem(CONFIG.STORAGE_KEYS.USER_DATA);
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  },

  /**
   * Sync and verify authenticated user profile with backend
   */
  async fetchCurrentUser() {
    try {
      const user = await api.get('/auth/me/');
      localStorage.setItem(CONFIG.STORAGE_KEYS.USER_DATA, JSON.stringify(user));
      return user;
    } catch (err) {
      if (err.status === 401) {
        api.clearTokens();
      }
      throw err;
    }
  },

  /**
   * Check if user is currently authenticated
   */
  isAuthenticated() {
    return Boolean(api.getAccessToken() && this.getUser());
  },

  /**
   * Retrieve current user role
   */
  getRole() {
    const user = this.getUser();
    return user ? user.role : null;
  },

  /**
   * Navigate to role-specific dashboard
   */
  redirectByRole(role = null) {
    const targetRole = role || this.getRole();
    if (targetRole === CONFIG.ROLES.PATIENT) {
      window.location.href = getAppPath('/pages/patient/dashboard.html');
    } else if (targetRole === CONFIG.ROLES.DOCTOR) {
      window.location.href = getAppPath('/pages/doctor/dashboard.html');
    } else if (targetRole === CONFIG.ROLES.ADMIN) {
      window.location.href = getAppPath('/pages/admin/dashboard.html');
    } else {
      window.location.href = getAppPath('/login.html');
    }
  },

  /**
   * Guards a page to enforce authentication and allowed roles.
   * If unauthorized, redirects to login or unauthorized page.
   */
  async guardRoute(allowedRoles = []) {
    if (!this.isAuthenticated()) {
      const currentPath = window.location.pathname;
      window.location.href = `${getAppPath('/login.html')}?redirect=${encodeURIComponent(currentPath)}`;
      return false;
    }

    try {
      // Re-verify with backend to ensure token is valid and role hasn't changed
      const verifiedUser = await this.fetchCurrentUser();
      if (allowedRoles.length > 0 && !allowedRoles.includes(verifiedUser.role)) {
        window.location.href = getAppPath('/unauthorized.html');
        return false;
      }
      return verifiedUser;
    } catch (err) {
      // If redirection to login with session_expired is already pending or active, preserve it
      const onLogin = window.location.pathname.endsWith('login.html');
      const hasExpiry = window.location.search.includes('session_expired');
      if (!onLogin && !hasExpiry) {
        window.location.href = `${getAppPath('/login.html')}?session_expired=true`;
      }
      return false;
    }
  },
};
