/**
 * VakCare Client Configuration
 * Base API URL, token keys, role definitions, and route mappings.
 */

const isLocalDev = Boolean(
  typeof window !== 'undefined' &&
  (window.location.hostname === '127.0.0.1' ||
   window.location.hostname === 'localhost' ||
   window.location.hostname === '[::1]')
);

export const CONFIG = {
  // Uses local Django server (port 8000) when running locally; uses deployed Vercel domain in production
  API_BASE_URL: (typeof window !== 'undefined' && window.__VAKCARE_API_URL__) 
    || (isLocalDev ? 'http://127.0.0.1:8000/api/v1' : `${window.location.origin}/api/v1`),
  APP_NAME: 'VakCare',
  STORAGE_KEYS: {
    ACCESS_TOKEN: 'vakcare_access_token',
    REFRESH_TOKEN: 'vakcare_refresh_token',
    USER_DATA: 'vakcare_user',
  },
  ROLES: {
    PATIENT: 'PATIENT',
    DOCTOR: 'DOCTOR',
    ADMIN: 'ADMIN',
  },
  SPECIALIZATIONS: [
    { value: 'GENERAL_MEDICINE', label: 'General Medicine' },
    { value: 'CARDIOLOGY', label: 'Cardiology' },
    { value: 'DERMATOLOGY', label: 'Dermatology' },
    { value: 'PEDIATRICS', label: 'Pediatrics' },
    { value: 'ORTHOPEDICS', label: 'Orthopedics' },
    { value: 'NEUROLOGY', label: 'Neurology' },
    { value: 'PSYCHIATRY', label: 'Psychiatry' },
    { value: 'GYNECOLOGY', label: 'Gynecology & Obstetrics' },
    { value: 'OPHTHALMOLOGY', label: 'Ophthalmology' },
    { value: 'ENT', label: 'Ear, Nose & Throat' },
    { value: 'ONCOLOGY', label: 'Oncology' },
    { value: 'OTHER', label: 'Other Specialization' },
  ],
};

/**
 * Returns root-relative or relative path safely based on current location
 */
export function getAppPath(path) {
  // If the path starts with '/', calculate depth from current window.location
  if (path.startsWith('/')) {
    const depth = window.location.pathname.split('/').filter(Boolean).length;
    // Find where 'frontend' or root is
    const pathParts = window.location.pathname.split('/');
    const frontendIndex = pathParts.indexOf('frontend');
    if (frontendIndex !== -1) {
      const prefix = pathParts.slice(0, frontendIndex + 1).join('/') || '';
      return prefix + path;
    }
    // When served from root of frontend
    return path;
  }
  return path;
}
