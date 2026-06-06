# GTM Live Install Steps

## What I verified
- The site is already **GTM-ready** from an event/dataLayer standpoint.
- The repo does **not** currently contain a live GTM container snippet.
- A helper script now exists at `scripts/install_gtm.py` to stamp the GTM snippet across all HTML files once the real container ID is known.

## What you need
- the production GTM container ID, like `GTM-ABC1234`
- access to the `nalawtx-website` repo and Netlify deploy flow

## Install command
Run this from the repo root:

```bash
python3 scripts/install_gtm.py GTM-ABC1234
```

Replace `GTM-ABC1234` with the real container ID.

## Safety check before install
To verify GTM is not already installed, run:

```bash
python3 scripts/install_gtm.py GTM-ABC1234 --check
```

If files are listed as missing GTM, that is expected right now.

## What the script does
It adds the standard Google Tag Manager snippets:
- the `<script>` block immediately after `<head>`
- the `<noscript>` iframe immediately after `<body>`

It is idempotent, so re-running it should not duplicate the markers.

## After installing the snippet
1. Commit the changes.
2. Deploy to Netlify.
3. Open GTM Preview mode.
4. Verify these events fire on the consultation flow:
   - `form_start`
   - `generate_lead`
   - `thank_you_view`
   - `phone_click`
   - `sms_click`
   - `guide_download`
5. Confirm the new qualification fields are available in the form payload and GTM variables:
   - `case_type`
   - `incident_timing`
   - `contact_method`
6. Publish the GTM container only after Preview confirms the flow.

## Recommended first GTM build
Use the existing map in:
- `GTM-GA4-IMPLEMENTATION-MAP.md`

Start with:
- GA4 configuration tag
- `thank_you_view` as the first primary form conversion
- `phone_click` as secondary

## Recommended post-install QA
- test one desktop form submission
- test one mobile form submission
- test one call click from header
- test one call click from sticky call bar
- verify GA4 Realtime receives events
- verify no duplicate pageview tags exist

## Suggested commit message
```bash
git commit -am "Install GTM container snippet sitewide"
```
