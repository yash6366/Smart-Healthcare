/**
 * VakCare Client Validation Utility
 * Client-side format checks and server-side validation error mapping onto form fields.
 */

export const Validation = {
  isEmail(val) {
    if (!val || typeof val !== 'string') return false;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(val.trim());
  },

  isStrongPassword(val) {
    // Django MinimumLengthValidator enforces >= 8 characters
    return typeof val === 'string' && val.length >= 8;
  },

  isFutureDate(dateStr) {
    if (!dateStr) return false;
    const selected = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return selected >= today;
  },

  clearFieldErrors(formElement) {
    if (!formElement) return;
    formElement.querySelectorAll('.is-invalid').forEach((el) => {
      el.classList.remove('is-invalid');
      el.removeAttribute('aria-invalid');
      const describedBy = el.getAttribute('aria-describedby') || '';
      if (describedBy.includes('-feedback')) {
        el.removeAttribute('aria-describedby');
      }
    });
    formElement.querySelectorAll('.invalid-feedback').forEach((el) => {
      el.remove();
    });
  },

  setFieldError(inputElement, errorMessage) {
    if (!inputElement) return;
    inputElement.classList.add('is-invalid');
    inputElement.setAttribute('aria-invalid', 'true');

    const feedbackId = `${inputElement.id || inputElement.name || 'field'}-feedback`;
    inputElement.setAttribute('aria-describedby', feedbackId);

    // Remove existing feedback if any
    const parent = inputElement.closest('.form-group') || inputElement.parentElement;
    const existingFeedback = parent.querySelector('.invalid-feedback');
    if (existingFeedback) {
      existingFeedback.textContent = errorMessage;
      existingFeedback.id = feedbackId;
    } else {
      const feedback = document.createElement('div');
      feedback.className = 'invalid-feedback';
      feedback.id = feedbackId;
      feedback.setAttribute('role', 'alert');
      feedback.textContent = errorMessage;
      parent.appendChild(feedback);
    }

    const clearThis = () => {
      inputElement.classList.remove('is-invalid');
      inputElement.removeAttribute('aria-invalid');
      inputElement.removeAttribute('aria-describedby');
      const p = inputElement.closest('.form-group') || inputElement.parentElement;
      if (p) {
        const fb = p.querySelector('.invalid-feedback');
        if (fb) fb.remove();
      }
    };
    inputElement.addEventListener('input', clearThis, { once: true });
  },

  /**
   * Maps server-side DRF validation error dict onto form elements
   * @param {HTMLFormElement} formElement
   * @param {Object} errorDetails
   */
  applyServerErrors(formElement, errorDetails) {
    if (!formElement || !errorDetails || typeof errorDetails !== 'object') return;

    this.clearFieldErrors(formElement);

    Object.entries(errorDetails).forEach(([field, messages]) => {
      const message = Array.isArray(messages) ? messages[0] : String(messages);
      const input = formElement.querySelector(`[name="${field}"]`) || formElement.querySelector(`#${field}`);
      if (input) {
        this.setFieldError(input, message);
      }
    });
  },
};
