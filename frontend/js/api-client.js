/**
 * VakCare Shared API Client
 * Centralized fetch handler, token management, automatic JWT refresh,
 * unified error envelopes, and request abort control.
 */

import { CONFIG, getAppPath } from './config.js';

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

export class ApiClient {
  constructor(baseUrl = CONFIG.API_BASE_URL) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  getAccessToken() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN);
  }

  getRefreshToken() {
    return localStorage.getItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
  }

  setTokens(access, refresh) {
    if (access) localStorage.setItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN, access);
    if (refresh) localStorage.setItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN, refresh);
  }

  clearTokens() {
    localStorage.removeItem(CONFIG.STORAGE_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(CONFIG.STORAGE_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(CONFIG.STORAGE_KEYS.USER_DATA);
  }

  /**
   * Refreshes access token using the stored refresh token.
   */
  async refreshAccessToken() {
    const refreshToken = this.getRefreshToken();

    const response = await fetch(`${this.baseUrl}/auth/token/refresh/`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(refreshToken ? { refresh: refreshToken } : {}),
    });

    if (!response.ok) {
      this.clearTokens();
      throw new Error('Session expired. Please log in again.');
    }

    const data = await response.json();
    this.setTokens(data.access, data.refresh || refreshToken);
    return data.access;
  }

  /**
   * Primary HTTP request method
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http')
      ? endpoint
      : `${this.baseUrl}/${endpoint.replace(/^\/+/, '')}`;

    const headers = new Headers(options.headers || {});

    // Set JSON content-type if body is an object and not FormData
    if (options.body && !(options.body instanceof FormData) && typeof options.body === 'object') {
      headers.set('Content-Type', 'application/json');
      options.body = JSON.stringify(options.body);
    }

    // Attach Bearer token if not public
    const token = this.getAccessToken();
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    const fetchOptions = {
      credentials: 'include',
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, fetchOptions);

      // Handle HTTP 401 Unauthorized (attempt refresh once)
      if (response.status === 401 && !options._retry && !endpoint.includes('auth/login')) {
        if (isRefreshing) {
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((newToken) => {
              headers.set('Authorization', `Bearer ${newToken}`);
              return fetch(url, { ...fetchOptions, headers });
            })
            .then((res) => this.handleResponse(res));
        }

        options._retry = true;
        isRefreshing = true;

        try {
          const newAccessToken = await this.refreshAccessToken();
          processQueue(null, newAccessToken);
          headers.set('Authorization', `Bearer ${newAccessToken}`);
          const retryResponse = await fetch(url, { ...fetchOptions, headers });
          return await this.handleResponse(retryResponse);
        } catch (refreshErr) {
          processQueue(refreshErr, null);
          window.dispatchEvent(new CustomEvent('vakcare:session-expired'));
          const loginUrl = getAppPath('/login.html');
          if (!window.location.pathname.endsWith('login.html')) {
            window.location.href = `${loginUrl}?session_expired=true`;
          }
          throw refreshErr;
        } finally {
          isRefreshing = false;
        }
      }

      return await this.handleResponse(response);
    } catch (networkError) {
      if (networkError.name === 'AbortError') {
        throw networkError;
      }
      // If error already structured, throw it
      if (networkError.code && networkError.message) {
        throw networkError;
      }
      throw {
        status: 'error',
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to the healthcare server. Please verify your connection or ensure backend is running.',
        details: networkError.message,
      };
    }
  }

  /**
   * Normalize response from DRF
   */
  async handleResponse(response) {
    if (response.status === 204) {
      return { status: 'success', data: null };
    }

    let payload;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      try {
        payload = await response.json();
      } catch (err) {
        payload = null;
      }
    } else {
      payload = await response.text();
    }

    if (!response.ok) {
      let code = 'HTTP_' + response.status;
      let message = 'An error occurred while processing the request.';
      let details = null;

      if (payload && typeof payload === 'object') {
        if (payload.error) {
          code = payload.error.code || code;
          message = payload.error.message || message;
          details = payload.error.details || null;
        } else if (payload.detail) {
          message = payload.detail;
        } else if (payload.message) {
          message = payload.message;
        } else {
          // DRF validation errors map
          details = payload;
          const firstKey = Object.keys(payload)[0];
          if (firstKey) {
            const firstVal = payload[firstKey];
            message = Array.isArray(firstVal) ? `${firstKey}: ${firstVal[0]}` : `${firstKey}: ${firstVal}`;
          }
        }
      }

      const errorObj = new Error(message);
      errorObj.status = response.status;
      errorObj.code = code;
      errorObj.details = details;
      errorObj.payload = payload;
      throw errorObj;
    }

    return payload;
  }

  // Convenience HTTP methods
  get(endpoint, params = {}, options = {}) {
    const url = new URL(
      endpoint.startsWith('http') ? endpoint : `${this.baseUrl}/${endpoint.replace(/^\/+/, '')}`
    );
    Object.keys(params).forEach((key) => {
      if (params[key] !== undefined && params[key] !== null && params[key] !== '') {
        url.searchParams.append(key, params[key]);
      }
    });
    return this.request(url.toString(), { ...options, method: 'GET' });
  }

  post(endpoint, body = {}, options = {}) {
    return this.request(endpoint, { ...options, method: 'POST', body });
  }

  patch(endpoint, body = {}, options = {}) {
    return this.request(endpoint, { ...options, method: 'PATCH', body });
  }

  put(endpoint, body = {}, options = {}) {
    return this.request(endpoint, { ...options, method: 'PUT', body });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

export const api = new ApiClient();
