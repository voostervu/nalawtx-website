# Tracking Install Checklist

## Purpose
This repo is now prepared for GTM, GA4, Meta Pixel, and CallRail without hardcoding any account IDs.

## Current hooks already in the site
- `window.dataLayer` is primed on every page load
- intake forms have stable IDs and `data-form-name` attributes
- conversion pages include `data-page-type` and `data-page-lang` on `<body>`
- consultation pages also include `data-case-type`
- phone and SMS links are annotated at runtime with:
  - `data-phone-role`
  - `data-callrail-target="primary"`
  - `data-page-type`
  - `data-page-lang`

## Events already emitted
- `form_start`
- `generate_lead`
- `thank_you_view`
- `form_submit_error`
- `phone_click`
- `sms_click`
- `guide_download`

## GTM install notes
### Recommended trigger targets
- consultation form: `#consultation-form`
- Spanish consultation form: `#consultation-form-es`
- Vietnamese consultation form: `#consultation-form-vi`
- homepage hero form: `#hero-intake-form`

### Recommended variables to capture
- form name from `data-form-name`
- page type from `document.body.dataset.pageType`
- page language from `document.body.dataset.pageLang`
- case type from `document.body.dataset.caseType`
- phone role from clicked element dataset

## CallRail install notes
### Recommended swap targets
Use the default site phone number instances as the primary swap set.
All clickable phone and SMS links are now marked with:
- `data-callrail-target="primary"`

### QA after install
- header phone swaps
- sticky call bar swaps
- thank-you-state call button swaps
- footer phone swaps
- mobile and desktop both checked

## Meta Pixel notes
### Strongest conversion moment
Use the `thank_you_view` event as the first candidate for a real Lead event.

### Softer signals
- `form_start`
- `phone_click`
- `guide_download`

## Repo maps created for live install
- `GTM-GA4-IMPLEMENTATION-MAP.md`
- `META-PIXEL-IMPLEMENTATION-MAP.md`
- `CALLRAIL-INSTALL-MAP.md`
- `DEPLOYMENT-CHECKLIST.md`
- `POST-DEPLOY-QA-RUNBOOK.md`
- `LAUNCH-MASTER-PLAN.md`

## Recommended next live setup order
1. add GTM container
2. verify `dataLayer` events in preview mode
3. connect GA4 and map conversions
4. install Meta Pixel through GTM
5. install CallRail and confirm number swap / attribution
6. import only strong conversions into Google Ads
