# Launch Master Plan

## Purpose
This is the command-center document for the first live tracking and measurement install on nalawtx.com.
Use this file as the single entry point for launch prep, deployment, QA, and sign-off.

## Current state
The site now has:
- form submission and thank-you-state tracking hooks
- dataLayer-ready custom events
- GTM-friendly form and page selectors
- CallRail-friendly phone annotations
- implementation maps for GTM, Meta Pixel, and CallRail
- deployment and QA runbooks

## Live inputs still needed
Before live installation, gather:
- GTM container ID
- GA4 measurement ID
- Meta Pixel ID
- CallRail account and number plan
- destination intake phone number confirmation

## Launch sequence
### phase 1: pre-push review
Use:
- `DEPLOYMENT-CHECKLIST.md`

Goal:
- confirm the repo is safe and ready for live install

### phase 2: tracking foundation install
Use:
- `TRACKING-INSTALL-CHECKLIST.md`
- `GTM-GA4-IMPLEMENTATION-MAP.md`

Goal:
- install GTM
- configure GA4
- map custom events and conversions correctly

### phase 3: Meta install
Use:
- `META-PIXEL-IMPLEMENTATION-MAP.md`

Goal:
- install Pixel cleanly
- fire Lead only from the real consultation success state

### phase 4: CallRail install
Use:
- `CALLRAIL-INSTALL-MAP.md`

Goal:
- swap numbers cleanly
- preserve source attribution
- avoid duplicate optimization logic

### phase 5: post-deploy QA
Use:
- `POST-DEPLOY-QA-RUNBOOK.md`

Goal:
- verify everything works on desktop and mobile before paid traffic goes live

## Event hierarchy for optimization
### primary first-party form signal
- `thank_you_view`

### primary call signal later
- qualified tracked calls from CallRail

### secondary and diagnostic only
- `form_submit`
- `form_start`
- `phone_click`
- `sms_click`
- `guide_download`

## Guardrails
Do not launch paid traffic if any of these are true:
- duplicate pageviews in GA4
- duplicate Lead events in Meta
- thank-you event not firing
- form submission path broken
- CallRail number swapping breaks call routing
- weak events are marked as primary conversions

## Minimum sign-off before traffic
You are ready for first paid traffic only when:
1. forms submit successfully
2. thank-you tracking is clean
3. GA4 receives the intended events once
4. Meta Lead fires only on real consultation success
5. CallRail attribution works on live test calls
6. Google Ads import plan is limited to strong conversions

## Recommended first live install order
1. push or deploy the prepared website code
2. add GTM container
3. verify `dataLayer` events in GTM preview
4. connect GA4 and publish event tags
5. install Meta Pixel through GTM
6. install CallRail and test number swap
7. run the full post-deploy QA
8. only then connect or import conversions into ad platforms

## Document map
### general launch path
- `TRACKING-INSTALL-CHECKLIST.md`
- `DEPLOYMENT-CHECKLIST.md`
- `POST-DEPLOY-QA-RUNBOOK.md`

### implementation detail docs
- `GTM-GA4-IMPLEMENTATION-MAP.md`
- `META-PIXEL-IMPLEMENTATION-MAP.md`
- `CALLRAIL-INSTALL-MAP.md`

## Recommended next decision
Once Vu is ready, the next clean move is:
- push the local website repo changes
- then perform the live install using this master plan in order
