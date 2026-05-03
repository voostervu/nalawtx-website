// Win With Nguyen — front-end JS
// Handles mobile nav, form submission (mailto fallback), and analytics hooks.
// To upgrade to a real backend: set window.INTAKE_ENDPOINT to a Formspree/Zapier/custom URL
// and the form will POST JSON there instead of opening a mail client.

(function () {
  'use strict';

  // =========================================================================
  // Config — change these to upgrade from mailto fallback to a real backend
  // =========================================================================
  const INTAKE_EMAIL = 'info@nalawtx.com';
  // When you're ready, set one of these:
  //   INTAKE_ENDPOINT = 'https://formspree.io/f/YOUR_FORM_ID';
  //   INTAKE_ENDPOINT = 'https://hooks.zapier.com/hooks/catch/XXXX/YYYY';
  //   INTAKE_ENDPOINT = 'https://your-lawmatics-webhook-url';
  // Then deploy — no other change needed.
  const INTAKE_ENDPOINT = null;

  document.addEventListener('DOMContentLoaded', function () {

    // -------------------------------------------------------------
    // Mobile nav toggle
    // -------------------------------------------------------------
    const burger = document.querySelector('.hdr__burger');
    const mnav = document.querySelector('.mnav');
    const mnavClose = document.querySelector('.mnav__close');
    if (burger && mnav) {
      burger.addEventListener('click', function () {
        mnav.classList.add('open');
        document.body.style.overflow = 'hidden';
      });
    }
    if (mnavClose && mnav) {
      mnavClose.addEventListener('click', function () {
        mnav.classList.remove('open');
        document.body.style.overflow = '';
      });
    }

    // -------------------------------------------------------------
    // Intake form handler
    // -------------------------------------------------------------
    const form = document.querySelector('form[data-intake]');
    if (form) {
      form.addEventListener('submit', handleIntakeSubmit);
    }

    // -------------------------------------------------------------
    // Phone-click tracking (GA4 hook)
    // -------------------------------------------------------------
    document.querySelectorAll('a[href^="tel:"]').forEach(function (a) {
      a.addEventListener('click', function () {
        if (window.gtag) {
          window.gtag('event', 'phone_click', {
            event_category: 'engagement',
            event_label: a.href.replace('tel:', '')
          });
        }
      });
    });
  });

  // =========================================================================
  // Form submission — tries JSON endpoint first, falls back to mailto.
  // =========================================================================
  function handleIntakeSubmit(e) {
    e.preventDefault();
    const form = e.target;

    // Light validation — visually flag empty required fields
    const required = form.querySelectorAll('[required]');
    let valid = true;
    required.forEach(function (f) {
      if (!f.value || (f.type === 'checkbox' ? !f.checked : !f.value.trim())) {
        valid = false;
        f.style.borderColor = 'var(--verdict)';
        f.setAttribute('aria-invalid', 'true');
      } else {
        f.style.borderColor = '';
        f.removeAttribute('aria-invalid');
      }
    });
    if (!valid) {
      // Scroll to first invalid field and show a friendly message
      const firstInvalid = form.querySelector('[aria-invalid="true"]');
      if (firstInvalid) firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      showBanner(form, 'Please complete all required fields so we can respond faster.', 'error');
      return;
    }

    // Collect form data
    const data = {};
    const fd = new FormData(form);
    for (const [key, value] of fd.entries()) {
      data[key] = value;
    }
    data.source_url = window.location.href;
    data.submitted_at = new Date().toISOString();

    // Track in GA4 if present
    if (window.gtag) {
      window.gtag('event', 'generate_lead', {
        event_category: 'conversion',
        event_label: data.language || 'English'
      });
    }

    // Disable submit button while processing
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Sending…';
    }

    // Path 1: If an endpoint is configured, POST JSON to it
    if (INTAKE_ENDPOINT) {
      fetch(INTAKE_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(data)
      })
        .then(function (r) {
          if (!r.ok) throw new Error('Submission failed');
          showSuccessScreen(form);
        })
        .catch(function () {
          // Backend failed — fall back to mailto so the lead isn't lost
          fallbackMailto(data);
          showSuccessScreen(form);
        })
        .finally(function () {
          if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = originalText; }
        });
      return;
    }

    // Path 2: No endpoint — use mailto fallback immediately
    fallbackMailto(data);
    showSuccessScreen(form);
    if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = originalText; }
  }

  function fallbackMailto(data) {
    const subject = 'Case Review Request — ' + (data.first_name || 'New inquiry');
    const bodyLines = [
      'New case review request from nalawtx.com:',
      '',
      'Name: ' + (data.first_name || ''),
      'Phone: ' + (data.phone || ''),
      'Preferred language: ' + (data.language || 'English'),
      '',
      '--- What happened ---',
      (data.details || '(none provided)'),
      '',
      '--- Meta ---',
      'Submitted: ' + data.submitted_at,
      'Page: ' + data.source_url
    ].join('\n');

    const mailto = 'mailto:' + INTAKE_EMAIL +
      '?subject=' + encodeURIComponent(subject) +
      '&body=' + encodeURIComponent(bodyLines);

    // Open user's email client (this is the fallback path)
    window.location.href = mailto;
  }

  function showSuccessScreen(form) {
    // Replace form with a confirmation message
    const container = form.parentElement;
    const name = (form.querySelector('[name="first_name"]') || {}).value || 'you';

    container.innerHTML =
      '<div style="text-align: center; padding: var(--s-lg) 0;">' +
        '<div style="font-family: var(--f-display); font-size: 2.25rem; font-weight: 360; letter-spacing: -0.02em; color: var(--navy); margin-bottom: var(--s-sm); line-height: 1.1;">Thanks, ' + escapeHtml(name) + '.</div>' +
        '<p style="color: var(--navy-2); font-size: 1.05rem; max-width: 40ch; margin: 0 auto var(--s-md);">Your request has been sent. Expect a call or text from our team within 15 minutes during business hours — or first thing tomorrow morning if you submitted overnight.</p>' +
        '<p style="color: var(--muted); font-size: 0.88rem; margin-bottom: var(--s-md);">Need to reach us now? Call <a href="tel:+17138429442" style="color: var(--navy); border-bottom: 1px dotted var(--muted);">(713) 842-9442</a>.</p>' +
        '<a href="index.html" class="btn btn--ghost">Back to home</a>' +
      '</div>';

    // Scroll the success message into view
    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function showBanner(form, message, kind) {
    // Remove any prior banner
    const existing = form.querySelector('.form-banner');
    if (existing) existing.remove();
    const banner = document.createElement('div');
    banner.className = 'form-banner';
    banner.style.cssText =
      'padding: 0.75rem 1rem; border-radius: 4px; margin-bottom: var(--s-sm); font-size: 0.92rem; ' +
      (kind === 'error'
        ? 'background: rgba(30, 58, 138, 0.08); color: var(--verdict); border-left: 3px solid var(--verdict);'
        : 'background: rgba(239, 211, 114, 0.15); color: var(--navy); border-left: 3px solid var(--gold-deep);');
    banner.textContent = message;
    form.insertBefore(banner, form.firstChild);
    banner.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

})();


// ============================================================
// Cookie consent banner
// ============================================================
(function () {
  const KEY = 'nalaw_cookie_consent';
  if (localStorage.getItem(KEY)) return;  // already chose

  const banner = document.createElement('div');
  banner.className = 'cookie-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Cookie consent');
  banner.innerHTML = `
    <div class="cookie-banner__inner">
      <p class="cookie-banner__text">
        We use cookies to operate this site and understand how visitors use it.
        See our <a href="/privacy.html">Privacy Policy</a>.
      </p>
      <div class="cookie-banner__actions">
        <button type="button" class="cookie-banner__btn cookie-banner__btn--decline" data-action="decline">Decline</button>
        <button type="button" class="cookie-banner__btn cookie-banner__btn--accept" data-action="accept">Accept</button>
      </div>
    </div>
  `;
  document.body.appendChild(banner);

  banner.addEventListener('click', function (e) {
    const action = e.target.getAttribute('data-action');
    if (!action) return;
    localStorage.setItem(KEY, action);
    banner.classList.add('cookie-banner--gone');
    setTimeout(function () { banner.remove(); }, 350);
  });

  setTimeout(function () { banner.classList.add('cookie-banner--show'); }, 800);
})();
