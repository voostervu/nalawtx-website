# Deployment Checklist

## Purpose
Use this checklist right before pushing or deploying the first tracking-enabled marketing build.

## Pre-push code check
- confirm working branch is `main`
- review git diff one more time
- confirm no secret IDs were hardcoded into repo files
- confirm `js/main.js` passes syntax check
- confirm tracking docs exist:
  - `TRACKING-INSTALL-CHECKLIST.md`
  - `GTM-GA4-IMPLEMENTATION-MAP.md`
  - `META-PIXEL-IMPLEMENTATION-MAP.md`
  - `CALLRAIL-INSTALL-MAP.md`

## Pre-deploy owner inputs
Have these ready before live install:
- GTM container ID
- GA4 measurement ID
- Meta Pixel ID
- CallRail account and tracking number plan
- confirmation of destination intake phone number

## GTM install step
- add GTM head snippet sitewide
- add GTM noscript snippet immediately after opening `<body>` where appropriate
- publish to a preview or draft environment first if possible

## GA4 setup step
- add GA4 config through GTM, not hardcoded in page files
- create the event tags from `GTM-GA4-IMPLEMENTATION-MAP.md`
- mark only strong conversions as primary

## Meta Pixel setup step
- install Meta Pixel through GTM
- fire PageView on all pages
- fire ViewContent on consultation pages
- fire Lead from `thank_you_view` only

## CallRail setup step
- install CallRail through GTM if practical
- confirm primary DNI pool settings
- verify number swap coverage against `CALLRAIL-INSTALL-MAP.md`

## Site behavior check before deploy
- homepage hero form still submits successfully
- consultation form still submits successfully
- Spanish consultation form still submits successfully
- Vietnamese consultation form still submits successfully
- thank-you state still appears after submit
- thank-you URL state still restores correctly on refresh
- click-to-call links still work
- SMS links still work
- crash playbook download still works

## Publish gate
Do not push/deploy until these are true:
- form path works
- tracking plan is documented
- GTM preview plan is ready
- no duplicate conversion strategy is planned
- CallRail and Meta are not configured to optimize on weak signals

## Immediate post-deploy order
1. GTM preview
2. GA4 realtime verification
3. Meta test events
4. CallRail swap test
5. one real form submission test
6. one tracked test call
