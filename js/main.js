// Win With Nguyen — front-end JS
// Mobile nav, intake form submission, analytics hooks (GTM/GA4-ready).
//
// Tracking foundation:
//   - All custom events are pushed to window.dataLayer (GTM-friendly) and also
//     forwarded to gtag() if a GA4 tag is present on the page. No GTM/GA4 ID
//     is required for this file to work — it just primes the pipeline.
//   - Attribution context (UTMs, gclid/fbclid, referrer, landing page) is
//     captured on the first page of the session and injected as hidden fields
//     when an intake form is submitted, so it reaches Formspree / the CRM.
//
// Form submission:
//   - If the form has a real http(s) action (e.g. Formspree), the handler
//     POSTs FormData via fetch with `Accept: application/json`. On success it
//     shows the inline thank-you screen.
//   - If the action is missing or the fetch fails, it falls back to a mailto
//     so the lead is never lost.

(function () {
  'use strict';

  const INTAKE_EMAIL = 'info@nalawtx.com';
  const ATTRIBUTION_KEY = 'nalaw_attribution';
  const SUCCESS_KEY = 'nalaw_last_success';
  const ATTRIBUTION_PARAMS = [
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'gclid', 'fbclid', 'msclkid'
  ];

  // Prime dataLayer so dataLayer.push() works whether or not GTM is loaded.
  window.dataLayer = window.dataLayer || [];

  function track(eventName, payload) {
    const data = Object.assign({ event: eventName }, payload || {});
    window.dataLayer.push(data);
    if (typeof window.gtag === 'function') {
      const gtagPayload = Object.assign({}, payload || {});
      delete gtagPayload.event;
      window.gtag('event', eventName, gtagPayload);
    }
  }

  function captureAttribution() {
    let stored = {};
    try {
      stored = JSON.parse(sessionStorage.getItem(ATTRIBUTION_KEY) || '{}');
    } catch (_) { stored = {}; }

    const url = new URL(window.location.href);
    let dirty = false;
    ATTRIBUTION_PARAMS.forEach(function (key) {
      const v = url.searchParams.get(key);
      // First-touch within the session wins; don't overwrite.
      if (v && !stored[key]) { stored[key] = v; dirty = true; }
    });
    if (!stored.landing_page) {
      stored.landing_page = window.location.pathname + window.location.search;
      dirty = true;
    }
    if (!('referrer' in stored)) {
      stored.referrer = document.referrer || '';
      dirty = true;
    }
    if (dirty) {
      try { sessionStorage.setItem(ATTRIBUTION_KEY, JSON.stringify(stored)); } catch (_) {}
    }
    return stored;
  }

  function injectHidden(form, name, value) {
    if (form.querySelector('input[type="hidden"][name="' + name.replace(/"/g, '\\"') + '"]')) return;
    const el = document.createElement('input');
    el.type = 'hidden';
    el.name = name;
    el.value = value == null ? '' : String(value);
    form.appendChild(el);
  }

  function attachAttribution(form) {
    const attribution = captureAttribution();
    Object.keys(attribution).forEach(function (k) {
      if (attribution[k] != null && attribution[k] !== '') {
        injectHidden(form, k, attribution[k]);
      }
    });
    injectHidden(form, 'page_url', window.location.href);
    injectHidden(form, 'submitted_at', new Date().toISOString());
  }

  function formName(form) {
    return form.dataset.formName || form.id || 'intake';
  }

  function currentPath() {
    return window.location.pathname.replace(/\/index\.html$/, '/') || '/';
  }

  function buildSuccessUrl(form) {
    const url = new URL(window.location.href);
    url.searchParams.set('submitted', '1');
    url.searchParams.set('form', formName(form));
    url.searchParams.set('thank_you', '1');
    url.hash = 'thank-you';
    return url.toString();
  }

  function rememberSuccess(form, transport) {
    const payload = {
      form_name: formName(form),
      path: currentPath(),
      thank_you_url: buildSuccessUrl(form),
      transport: transport,
      at: new Date().toISOString()
    };
    try {
      sessionStorage.setItem(SUCCESS_KEY, JSON.stringify(payload));
    } catch (_) {}
    return payload;
  }

  function readSuccessMemory() {
    try {
      return JSON.parse(sessionStorage.getItem(SUCCESS_KEY) || 'null');
    } catch (_) {
      return null;
    }
  }

  function shouldRestoreSuccess(form) {
    const url = new URL(window.location.href);
    if (url.searchParams.get('submitted') !== '1') return false;
    if (url.searchParams.get('form') !== formName(form)) return false;
    const memory = readSuccessMemory();
    if (!memory) return false;
    return memory.form_name === formName(form) && memory.path === currentPath();
  }

  function detectPhoneRole(link) {
    if (link.closest('[data-thank-you="true"]')) return 'thank_you';
    if (link.classList.contains('lp-hdr__phone')) return 'header';
    if (link.classList.contains('call')) return 'sticky_call_bar';
    if (link.classList.contains('text')) return 'sticky_text_bar';
    if (link.closest('form[data-intake]')) return 'form_support';
    if (link.closest('.hero__actions')) return 'hero_cta';
    if (link.closest('footer')) return 'footer';
    return 'general';
  }

  function annotatePhoneLinks() {
    document.querySelectorAll('a[href^="tel:"], a[href^="sms:"]').forEach(function (link) {
      if (!link.dataset.phoneRole) {
        link.dataset.phoneRole = detectPhoneRole(link);
      }
      link.dataset.callrailTarget = 'primary';
      link.dataset.pageType = document.body.dataset.pageType || '';
      link.dataset.pageLang = document.body.dataset.pageLang || '';
    });
  }

  function wireDownloadTracking() {
    document.querySelectorAll('a[href$=".pdf"], a[download]').forEach(function (link) {
      link.dataset.assetType = link.dataset.assetType || 'download';
      link.addEventListener('click', function () {
        track('guide_download', {
          asset_name: link.getAttribute('download') || link.pathname.split('/').pop() || '',
          asset_url: link.href,
          asset_type: link.dataset.assetType || 'download',
          link_location: currentPath(),
          page_type: document.body.dataset.pageType || ''
        });
      });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Capture attribution as early as possible, on every page.
    captureAttribution();

    // Mobile nav toggle
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

    annotatePhoneLinks();
    wireDownloadTracking();

    // Intake forms
    document.querySelectorAll('form[data-intake]').forEach(function (form) {
      if (shouldRestoreSuccess(form)) {
        track('thank_you_view', thankYouPayload(form, collect(form), 'restore', true));
        showSuccessScreen(form, { restored: true });
        annotatePhoneLinks();
        return;
      }

      let started = false;
      form.addEventListener('focusin', function () {
        if (started) return;
        started = true;
        track('form_start', {
          form_name: formName(form),
          form_location: currentPath(),
          page_type: document.body.dataset.pageType || ''
        });
      });
      form.addEventListener('submit', handleIntakeSubmit);
    });

    // Phone and SMS click tracking
    document.querySelectorAll('a[href^="tel:"], a[href^="sms:"]').forEach(function (a) {
      a.addEventListener('click', function () {
        const protocol = a.href.indexOf('sms:') === 0 ? 'sms' : 'tel';
        track(protocol === 'sms' ? 'sms_click' : 'phone_click', {
          phone_number: a.href.replace(/^tel:|^sms:/, ''),
          link_location: currentPath(),
          link_text: (a.textContent || '').trim().slice(0, 80),
          link_classes: a.className || '',
          phone_role: a.dataset.phoneRole || detectPhoneRole(a),
          callrail_target: a.dataset.callrailTarget || '',
          page_type: document.body.dataset.pageType || '',
          page_lang: document.body.dataset.pageLang || ''
        });
      });
    });
  });

  function handleIntakeSubmit(e) {
    const form = e.target;

    // Validation
    const required = form.querySelectorAll('[required]');
    let valid = true;
    required.forEach(function (f) {
      const empty = f.type === 'checkbox' ? !f.checked : !(f.value && f.value.trim());
      if (empty) {
        valid = false;
        f.style.borderColor = 'var(--verdict)';
        f.setAttribute('aria-invalid', 'true');
      } else {
        f.style.borderColor = '';
        f.removeAttribute('aria-invalid');
      }
    });
    if (!valid) {
      e.preventDefault();
      const firstInvalid = form.querySelector('[aria-invalid="true"]');
      if (firstInvalid) firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
      showBanner(form, 'Please complete all required fields so we can respond faster.', 'error');
      track('form_submit_error', { form_name: formName(form), reason: 'validation' });
      return;
    }

    // Attribution + meta as hidden fields so the lead email/CRM captures them.
    attachAttribution(form);

    const action = form.getAttribute('action');
    const useAjax = action && /^https?:\/\//i.test(action);

    if (!useAjax) {
      // No backend wired — mailto fallback so the lead isn't lost.
      e.preventDefault();
      const data = collect(form);
      track('generate_lead', leadPayload(form, data, 'mailto'));
      fallbackMailto(data);
      renderSuccessfulSubmit(form, data, 'mailto');
      return;
    }

    // AJAX path: post FormData with Accept: application/json (Formspree-friendly).
    e.preventDefault();
    const data = collect(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn ? submitBtn.innerHTML : '';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = 'Sending…';
    }

    fetch(action, {
      method: (form.getAttribute('method') || 'POST').toUpperCase(),
      headers: { 'Accept': 'application/json' },
      body: new FormData(form)
    })
      .then(function (r) {
        if (!r.ok) throw new Error('Submission failed: ' + r.status);
        track('generate_lead', leadPayload(form, data, 'ajax'));
        renderSuccessfulSubmit(form, data, 'ajax');
      })
      .catch(function () {
        track('form_submit_error', { form_name: formName(form), reason: 'network' });
        // Last-resort safety net so the lead reaches us even if the endpoint is down.
        fallbackMailto(data);
        renderSuccessfulSubmit(form, data, 'mailto_fallback');
      })
      .finally(function () {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = originalText; }
      });
  }

  function collect(form) {
    const data = {};
    const fd = new FormData(form);
    for (const [k, v] of fd.entries()) data[k] = v;
    return data;
  }

  function leadPayload(form, data, transport) {
    return {
      form_name: formName(form),
      form_location: currentPath(),
      preferred_language: data.language || data.source_lang || '',
      source_form: data.source_form || '',
      transport: transport,
      page_type: document.body.dataset.pageType || ''
    };
  }

  function thankYouPayload(form, data, transport, restored) {
    return {
      form_name: formName(form),
      form_location: currentPath(),
      preferred_language: data.language || data.source_lang || '',
      source_form: data.source_form || '',
      transport: transport,
      restored: restored ? 'true' : 'false',
      thank_you_url: buildSuccessUrl(form),
      page_type: document.body.dataset.pageType || ''
    };
  }

  function fallbackMailto(data) {
    const subject = 'Case Review Request — ' + (data.first_name || 'New inquiry');
    const bodyLines = [
      'New case review request from nalawtx.com:',
      '',
      'Name: ' + (data.first_name || ''),
      'Phone: ' + (data.phone || ''),
      'Email: ' + (data.email || ''),
      'Preferred language: ' + (data.language || 'English'),
      '',
      '--- What happened ---',
      (data.details || '(none provided)'),
      '',
      '--- Meta ---',
      'Submitted: ' + (data.submitted_at || new Date().toISOString()),
      'Page: ' + (data.page_url || window.location.href),
      'Landing: ' + (data.landing_page || ''),
      'Referrer: ' + (data.referrer || ''),
      'UTM source: ' + (data.utm_source || ''),
      'UTM medium: ' + (data.utm_medium || ''),
      'UTM campaign: ' + (data.utm_campaign || ''),
      'gclid: ' + (data.gclid || ''),
      'fbclid: ' + (data.fbclid || '')
    ].join('\n');

    const mailto = 'mailto:' + INTAKE_EMAIL +
      '?subject=' + encodeURIComponent(subject) +
      '&body=' + encodeURIComponent(bodyLines);

    window.location.href = mailto;
  }

  function renderSuccessfulSubmit(form, data, transport) {
    rememberSuccess(form, transport);
    const successUrl = buildSuccessUrl(form);
    try {
      window.history.replaceState({}, '', successUrl);
    } catch (_) {}
    track('thank_you_view', thankYouPayload(form, data, transport, false));
    showSuccessScreen(form, { transport: transport });
    annotatePhoneLinks();
  }

  function showSuccessScreen(form, options) {
    const opts = options || {};
    const container = form.parentElement;
    const name = (form.querySelector('[name="first_name"]') || {}).value || 'there';
    const isHero = formName(form) === 'hero';
    const returnHref = isHero ? 'consultation.html' : 'index.html';
    const returnLabel = isHero ? 'Continue to full case review' : 'Back to home';
    const responseCopy = opts.restored
      ? 'Your request was already sent. If you need us faster, call or text now and our team will jump on it.'
      : 'Your request has been sent. Expect a call or text from our team within 15 minutes during business hours, or first thing tomorrow morning if you submitted overnight.';

    container.innerHTML =
      '<div id="thank-you" data-thank-you="true" style="text-align: center; padding: var(--s-lg) 0;">' +
        '<div style="font-family: var(--f-display); font-size: 2.25rem; font-weight: 360; letter-spacing: -0.02em; color: var(--navy); margin-bottom: var(--s-sm); line-height: 1.1;">Thanks, ' + escapeHtml(name) + '.</div>' +
        '<p style="color: var(--navy-2); font-size: 1.05rem; max-width: 40ch; margin: 0 auto var(--s-md);">' + escapeHtml(responseCopy) + '</p>' +
        '<p style="color: var(--muted); font-size: 0.88rem; margin-bottom: var(--s-md);">Need to reach us now? Call <a href="tel:+17138429442" style="color: var(--navy); border-bottom: 1px dotted var(--muted);">(713) 842-9442</a>.</p>' +
        '<div style="display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap;">' +
          '<a href="tel:+17138429442" class="btn btn--primary">Call now</a>' +
          '<a href="' + returnHref + '" class="btn btn--ghost">' + returnLabel + '</a>' +
        '</div>' +
      '</div>';

    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function showBanner(form, message, kind) {
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
