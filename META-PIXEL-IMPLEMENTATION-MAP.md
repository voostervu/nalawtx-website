# Meta Pixel Implementation Map

## Purpose
Define the cleanest first Meta Pixel setup for nalawtx.com using the hooks already present in the site.

## Core rule
Meta should optimize to real consultation intent, not weak clicks.

## Install method
Recommended:
- install Meta Pixel through GTM

Reason:
- easier governance
- easier QA
- easier event changes later

## Base pixel
### fire on
- all pages

### event
- `PageView`

## Recommended custom conditions from site hooks
Available data for GTM or pixel routing:
- `page_type`
- `page_lang`
- `case_type`
- `form_name`
- `source_form`
- `transport`
- `phone_role`
- `asset_name`

## Meta event map
### 1. PageView
Trigger:
- all pages

### 2. ViewContent
Trigger:
- consultation page view

When to fire:
- consultation page load only

Parameters to include if supported:
- `content_name=consultation_page`
- `content_category=personal_injury`
- `language`

### 3. Lead
Trigger:
- `thank_you_view`

Why:
- this is the strongest current first-party confirmation of a real consultation submission

Parameters to include if supported:
- `content_name=consultation_submission`
- `content_category=personal_injury`
- `form_name`
- `language`
- `source_form`

### 4. Contact
Optional later, not required now.
Could be tested on:
- `phone_click`

Recommendation:
- do not use this as a primary optimization event at launch

### 5. Custom events for diagnosis
Optional through GTM if useful:
- `form_start`
- `guide_download`
- `sms_click`

Use these for analysis, not optimization.

## Recommended launch event policy
### optimize for
- Lead only, and only if the `thank_you_view` event proves clean

### if lead volume is too low or event quality is uncertain
- optimize for landing page views first
- keep Lead event firing for future learning

## Retargeting audiences to build
### audience 1
- all website visitors 30 days

### audience 2
- all website visitors 180 days

### audience 3
- consultation page visitors 30 days

### audience 4
- consultation page visitors 180 days

### audience 5
- lead submitted exclude audience
Built from:
- Lead event

## Event exclusions
Exclude from Lead audiences:
- guide download only
- phone click only
- sms click only

## QA checklist
1. confirm PageView on all pages
2. confirm ViewContent on consultation pages only
3. submit a real test form and confirm Lead on thank-you state
4. verify only one Lead event fires per successful submit
5. reload the thank-you URL and verify event behavior stays intentional
6. verify no Lead event fires on phone click or button click alone

## Guardrails
- do not fire Lead on consultation page view
- do not fire Lead on form start
- do not fire Lead on click-to-call alone
- do not use guide downloads as optimization conversions

## Recommendation
The best first Meta conversion event here is still the consultation form thank-you state.
Calls can support diagnosis and retargeting, but do not let Meta chase raw call clicks unless intake quality proves they are strong.
