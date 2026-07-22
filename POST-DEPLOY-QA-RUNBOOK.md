# Post-Deploy QA Runbook

## Purpose
Use this runbook immediately after GTM, GA4, Meta Pixel, and CallRail are installed.

## Test devices
Run checks on:
- desktop browser
- mobile browser

## Pages to test first
- homepage
- consultation page
- Spanish consultation page
- Vietnamese consultation page

## GTM QA
### preview mode
- confirm container loads on homepage
- confirm container loads on consultation pages
- confirm no duplicate container firing

### custom events
Verify these appear when expected:
- `form_start`
- `generate_lead`
- `thank_you_view`
- `form_submit_error`
- `phone_click`
- `sms_click`
- `guide_download`

### parameter checks
Inspect that these populate where relevant:
- `form_name`
- `source_form`
- `preferred_language`
- `phone_role`
- `callrail_target`
- `page_type`
- `page_lang`
- `thank_you_url`

## GA4 QA
### realtime
- pageviews appear once
- consultation page view appears correctly
- `form_submit` appears on successful submit
- `thank_you_view` appears on successful submit
- `phone_click` appears when call links are tapped
- `guide_download` appears on PDF click

### conversion checks
- only the intended primary conversions are marked primary
- no weak engagement event is marked primary by mistake

## Meta Pixel QA
### test events tool
- PageView fires on all pages
- ViewContent fires on consultation page load only
- Lead fires on thank-you state only
- Lead does not fire on consultation page view alone
- Lead does not fire on phone click alone

## CallRail QA
### number swap
Check these placements:
- homepage header
- homepage hero phone CTA
- consultation header
- consultation sticky call bar
- consultation support phone
- thank-you-state call button
- footer phone
- Spanish consultation phones
- Vietnamese consultation phones

### attribution
- tracked number shows expected source
- destination routing still works
- call can be tagged in CallRail

## Form QA
### submit success
Test all forms:
- homepage hero form
- English consultation form
- Spanish consultation form
- Vietnamese consultation form

Confirm:
- submission completes
- thank-you state appears
- thank-you URL state restores on refresh
- fallback path is not unexpectedly triggered if live endpoint works

## Download QA
- crash playbook PDF opens or downloads correctly
- `guide_download` event appears

## Failure rules
If any of these happen, pause launch work and fix before traffic goes live:
- duplicate GA4 pageviews
- duplicate Lead events
- thank-you event not firing
- form success broken
- CallRail number swap breaking click-to-call
- Meta firing Lead on weak actions

## Sign-off condition
The stack is ready for paid traffic only when:
- form success is clean
- thank-you tracking is clean
- Meta Lead is clean
- CallRail attribution works
- GA4 and GTM match the documented plan
