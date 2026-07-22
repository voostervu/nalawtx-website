# CallRail Install Map

## Purpose
Map the current site structure to a clean first CallRail install on nalawtx.com.

## Install recommendation
Use one primary dynamic number insertion pool first.
Install through GTM if practical.

## Current site readiness
Clickable phone and SMS links are annotated at runtime with:
- `data-phone-role`
- `data-callrail-target="primary"`
- `data-page-type`
- `data-page-lang`

This makes QA and future targeting easier even if CallRail itself swaps numbers by script rules.

## Primary swap target set
Treat all primary consumer-facing phone instances as part of the first swap set.

### pages in immediate scope
- homepage
- consultation page
- Spanish consultation page
- Vietnamese consultation page

### phone roles already distinguishable in tracking
- `header`
- `sticky_call_bar`
- `sticky_text_bar`
- `hero_cta`
- `form_support`
- `thank_you`
- `footer`
- `general`

## Recommended CallRail starter configuration
### number pool
- `paid-search-dni-main`

### destination
- current firm intake line

### sources to enable first
- Google Ads
- Google organic
- direct
- referral
- paid social if CallRail routing allows source separation cleanly

## Recommended QA sequence
### desktop
1. homepage header phone
2. homepage hero CTA phone
3. consultation page header phone
4. consultation page sticky call bar
5. consultation page body support phone
6. footer phone

### mobile
1. sticky call bar
2. header phone
3. thank-you-state call button after form submit
4. footer phone

### language pages
1. Spanish consultation page phone instances
2. Vietnamese consultation page phone instances

## Tracking coordination rules
### keep as diagnostic
- site `phone_click` event
- site `sms_click` event

### keep as primary optimization only after qualification
- qualified tracked calls from CallRail

### avoid duplication
Do not import both raw phone clicks and raw CallRail calls as primary Google Ads bidding conversions.

## Intake labeling plan inside CallRail
Create labels:
- qualified PI lead
- unqualified
- property damage only
- no injury
- wrong number
- spam
- existing client
- referral
- signed case

## QA checklist after live install
- number swap occurs on first landing page load from tagged source
- swapped number still routes correctly
- call source attribution appears in CallRail
- Google Ads attribution appears where supported
- phone-click event still fires without breaking CallRail
- thank-you-state call button also shows the correct tracked number if swap logic applies there

## Recommendation
Use CallRail for real call attribution and qualification.
Keep site click events as supporting signals only, not the main truth source.
