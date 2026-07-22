# GTM and GA4 Implementation Map

## Purpose
Translate the current site hooks into an exact GTM container build for nalawtx.com.

## Install scope
Install one GTM container sitewide on all production pages.

## Existing site hooks available now
### page-level data
Available on key pages through `<body>` dataset values:
- `data-page-type`
- `data-page-lang`
- `data-case-type` on consultation pages

### form-level hooks
- `#consultation-form`
- `#consultation-form-es`
- `#consultation-form-vi`
- `#hero-intake-form`
- `data-form-name`
- qualification fields on consultation forms now include:
  - `case_type`
  - `incident_timing`
  - `contact_method`

### runtime click annotations
Phone and SMS links are annotated with:
- `data-phone-role`
- `data-callrail-target="primary"`
- `data-page-type`
- `data-page-lang`

### dataLayer events already emitted by site JS
- `form_start`
- `generate_lead`
- `thank_you_view`
- `form_submit_error`
- `phone_click`
- `sms_click`
- `guide_download`

## GTM variable plan
Create these variables first.

### built-in variables
Enable:
- Page URL
- Page Path
- Page Hostname
- Click URL
- Click Text
- Click Classes
- Click Element
- Form ID if needed

### data layer variables
Create:
- `dlv_form_name`
- `dlv_form_location`
- `dlv_preferred_language`
- `dlv_source_form`
- `dlv_transport`
- `dlv_case_type`
- `dlv_incident_timing`
- `dlv_contact_method`
- `dlv_page_type`
- `dlv_page_lang`
- `dlv_phone_number`
- `dlv_phone_role`
- `dlv_callrail_target`
- `dlv_thank_you_url`
- `dlv_asset_name`
- `dlv_asset_url`
- `dlv_asset_type`
- `dlv_reason`

### DOM variables if needed later
- body `data-page-type`
- body `data-page-lang`
- body `data-case-type`

## GTM trigger plan
### 1. all pages
Use for:
- GA4 config
- baseline pixels

### 2. consultation page view
Trigger type:
- Page View

Rule:
- Page Path contains `consultation`

### 3. form_start
Trigger type:
- Custom Event

Event name:
- `form_start`

### 4. generate_lead
Trigger type:
- Custom Event

Event name:
- `generate_lead`

### 5. thank_you_view
Trigger type:
- Custom Event

Event name:
- `thank_you_view`

Recommendation:
- use this as the main first-party form conversion trigger

### 6. form_submit_error
Trigger type:
- Custom Event

Event name:
- `form_submit_error`

### 7. phone_click
Trigger type:
- Custom Event

Event name:
- `phone_click`

### 8. sms_click
Trigger type:
- Custom Event

Event name:
- `sms_click`

### 9. guide_download
Trigger type:
- Custom Event

Event name:
- `guide_download`

## GA4 tag plan
### tag 1: GA4 configuration
Trigger:
- all pages

### tag 2: consultation_page_view
Event name:
- `consultation_page_view`

Trigger:
- consultation page view

Parameters:
- `page_type` = body or data layer value
- `page_lang`
- `case_type`
- `landing_page_name` = `consultation`

### tag 3: form_start
Event name:
- `consultation_form_start`

Trigger:
- `form_start`

Parameters:
- `form_name`
- `form_location`
- `page_type`

### tag 4: form_submit
Event name:
- `form_submit`

Trigger:
- `generate_lead`

Parameters:
- `form_name`
- `form_location`
- `preferred_language`
- `source_form`
- `transport`
- `case_type`
- `incident_timing`
- `contact_method`
- `page_type`

### tag 5: thank_you_view
Event name:
- `thank_you_view`

Trigger:
- `thank_you_view`

Parameters:
- `form_name`
- `preferred_language`
- `source_form`
- `transport`
- `case_type`
- `incident_timing`
- `contact_method`
- `thank_you_url`
- `page_type`

### tag 6: phone_click
Event name:
- `phone_click`

Trigger:
- `phone_click`

Parameters:
- `phone_number`
- `phone_role`
- `callrail_target`
- `page_type`
- `page_lang`

### tag 7: sms_click
Event name:
- `sms_click`

Trigger:
- `sms_click`

Parameters:
- `phone_number`
- `phone_role`
- `page_type`
- `page_lang`

### tag 8: guide_download
Event name:
- `guide_download`

Trigger:
- `guide_download`

Parameters:
- `asset_name`
- `asset_url`
- `asset_type`
- `page_type`

### tag 9: form_submit_error
Event name:
- `form_submit_error`

Trigger:
- `form_submit_error`

Parameters:
- `form_name`
- `reason`
- `page_type`

## GA4 conversion recommendations
### primary
- `thank_you_view`
- qualified call conversion from CallRail after setup

### secondary
- `form_submit`
- `phone_click`
- `consultation_page_view`
- `guide_download`

## Google Ads import recommendation
Import only:
- `thank_you_view` as the first form conversion candidate
- qualified tracked calls from CallRail once ready

Do not import:
- `form_start`
- `guide_download`
- `sms_click`
as bidding conversions.

## GTM QA checklist
1. preview mode on homepage and consultation page
2. confirm GA4 config fires once
3. confirm `consultation_page_view` fires only on consultation pages
4. confirm `form_start` fires once per form interaction start
5. confirm `generate_lead` and `thank_you_view` both fire on successful form submit
6. confirm `phone_click` includes `phone_role`
7. confirm `guide_download` fires on crash playbook click
8. verify no duplicate pageviews or duplicate form conversion events
