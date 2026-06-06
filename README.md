# Nguyen & Associates — Win With Nguyen
## Complete static website build

This is a production-ready static HTML site for **Nguyen & Associates Injury Law Firm**, built around the "Win With Nguyen" brand direction we agreed on.

Pure HTML/CSS/JS — no build step, no framework, no dependencies. You can deploy to any static host (Netlify, Vercel, Cloudflare Pages, GitHub Pages, AWS S3, or any traditional web host) by uploading the files as-is.

---

## 📂 What's in this package

```
nalaw/
├── index.html                 ← Homepage
├── consultation.html          ← Primary conversion landing page
├── results.html               ← Case results (PLACEHOLDERS — see below)
├── about.html                 ← About the firm
├── contact.html               ← Contact page
├── faqs.html                  ← FAQ with schema.org markup
├── css/main.css               ← All styles (one file)
├── js/main.js                 ← Mobile nav + form validation
├── practice/
│   ├── index.html             ← Practice areas hub
│   └── [20 practice pages]    ← Each with full schema.org markup
├── attorneys/
│   ├── index.html             ← Team hub
│   └── [5 attorney bios]      ← Vu, Harrison, Kenneth, Lantz, Ellis
├── blog/
│   └── index.html             ← Blog landing (stub — ready for articles)
├── es/
│   └── index.html             ← Spanish homepage
├── vi/
│   └── index.html             ← Vietnamese homepage
└── assets/                    ← Empty — drop your images here
```

Total: **35 HTML pages** + design system + generator scripts (for easy updates).

---

## ✅ What's already built in

- **Brand system** — Fraunces + Manrope typography, Verdict Red signature color, editorial design language. Completely different from generic Houston PI firm templates.
- **Schema.org markup** on every key page: `LegalService`, `Attorney`, `Service`, `FAQPage`, `BreadcrumbList`, `WebSite`, `LocalBusiness`. This is the GEO / AI-search optimization layer — it helps Claude, Google AI Overviews, and ChatGPT cite you as a source.
- **Sticky mobile call bar** — tap-to-call / tap-to-text on every page for mobile users.
- **Real trilingual site** — English, Spanish, Vietnamese. `hreflang` tags set. Language toggle in every header.
- **Proper consultation landing page** — stripped nav, qualifying form fields (not one giant textarea), TCPA consent checkbox, reCAPTCHA-ready.
- **All 20 practice areas** have: Quick-Answer GEO block, Texas statute references, injuries list, compensation list, our process, 2–4 FAQs each with structured data.
- **Attorney bios** with Attorney schema and placeholders for headshots + credentials.
- **Full internal linking** — footer, nav, cross-links between practice areas and attorneys.

---

## 🛑 Things YOU need to provide before launch

### 1. **Real case results** (currently placeholders on `results.html`)
Open `results.html`. The table has 8 rows of `[$TBD]` and `[Placeholder...]` markers. Replace each with actual verdicts and settlements from firm files. **Do not skip this** — the stat "over a $1,000,000 combined total" on your current live site is undercutting your brand vs. competitors who show billions. Real numbers, even if more modest, presented honestly will perform better than that current line.

### 2. **Firm logo + brand lockup**
Drop a PNG or SVG into `/assets/logo.png` (or `.svg`). The headers currently use a text-based wordmark ("Nguyen & Associates" in Fraunces serif). If you have a custom logo file, I can swap it in — or we can stick with the text lockup, which is actually more distinctive than most law firm logos.

### 3. **Attorney headshots** → `/assets/`
Each of the 5 attorney pages and the attorneys hub show a dark placeholder block labeled "Photo placeholder." Drop each headshot as:
- `/assets/vu-nguyen.jpg`
- `/assets/harrison-nguyen.jpg`
- `/assets/kenneth-nguyen.jpg`
- `/assets/lantz-clinton.jpg`
- `/assets/ellis-munoz.jpg`

Tell me when you've dropped them and I'll swap the CSS placeholders for real `<img>` tags. **Target:** professional portrait, 4:5 aspect ratio, consistent background/lighting across all five.

### 4. **Attorney credentials** (search for `TO CONFIRM` in attorney files)
Each bio has placeholders like `J.D. · [Law school — TO CONFIRM]`. Send me:
- Law school (JD) for each attorney
- Undergraduate institution + degree
- Bar admission years
- Federal court admissions
- Super Lawyers / Rising Stars years (if any)
- Martindale or AVVO ratings (if any)
- Board certifications
- Notable trial experience or speaking engagements

### 5. **Intake form backend**
All four intake forms (homepage hero, English/Spanish/Vietnamese consultation pages) now POST to **Formspree** (`https://formspree.io/f/xqenarze`) via AJAX. Submissions include a `source_form` field plus auto-captured attribution (UTMs, gclid/fbclid, landing page, referrer, submit timestamp). If the Formspree request fails for any reason, the handler falls back to a `mailto:` to `info@nalawtx.com` so the lead is not lost.

To swap backends later, change the `action="..."` on each `<form data-intake>` to your CRM webhook (Lawmatics, Clio Grow, Litify, MyCase, Zapier/Make, etc.). No JS change required — the handler uses whatever URL is on the form.

I recommend **CallRail** for phone tracking (swap `(713) 842-9442` with a tracking number in the header and footer, and set CallRail to forward to your real line — you'll then see ad source for every call).

### 6. **Google reCAPTCHA v3**
Get keys from `google.com/recaptcha`. Add the site key to `consultation.html` just before `</body>`:
```html
<script src="https://www.google.com/recaptcha/api.js?render=YOUR_SITE_KEY"></script>
```

### 7. **Google Analytics 4 / Google Tag Manager**
Paste your GTM or GA4 snippet in the `<head>` of every page (or, better, replace the individual snippets with GTM and manage from there).

The site already primes `window.dataLayer` and pushes these custom events whether or not GTM/GA4 is installed — once you add the snippet, the events flow with no code change:

| Event | Fired when | Useful params |
|---|---|---|
| `phone_click` | Any `tel:` link is clicked | `phone_number`, `phone_role`, `callrail_target`, `link_location` |
| `sms_click` | Any `sms:` link is clicked | `phone_number`, `phone_role`, `link_location` |
| `form_start` | First focus inside an intake form | `form_name`, `form_location` |
| `generate_lead` | Form submission succeeds (AJAX or mailto fallback) | `form_name`, `preferred_language`, `source_form`, `transport` |
| `thank_you_view` | The thank-you state is shown after a successful form submit | `form_name`, `thank_you_url`, `transport`, `page_type` |
| `guide_download` | A PDF or download CTA is clicked | `asset_name`, `asset_url`, `asset_type`, `link_location` |
| `form_submit_error` | Validation or network failure | `form_name`, `reason` |

If a `gtag()` function is also present, the same events are forwarded to GA4. For GTM targeting, every intake form has a stable `id` and `data-form-name` attribute (`consultation-form`, `consultation-form-es`, `consultation-form-vi`, `hero-intake-form`). The `<body>` on key conversion pages also carries `data-page-type`, `data-page-lang`, and where useful `data-case-type` so GTM/Meta/CallRail rules can target without brittle CSS selectors. Clickable phone and SMS links are also annotated at runtime with `data-phone-role` and `data-callrail-target="primary"`.

For the live wiring plan, use:
- `TRACKING-INSTALL-CHECKLIST.md`
- `GTM-GA4-IMPLEMENTATION-MAP.md`
- `META-PIXEL-IMPLEMENTATION-MAP.md`
- `CALLRAIL-INSTALL-MAP.md`
- `DEPLOYMENT-CHECKLIST.md`
- `POST-DEPLOY-QA-RUNBOOK.md`

### 8. **Open Graph image**
Create a `1200×630px` social-share image and save as `/assets/og-image.jpg`. This is what shows up when your site is shared on Facebook, LinkedIn, iMessage, etc.

### 9. **Favicon set**
`/assets/favicon.ico` + `/assets/apple-touch-icon.png` (180×180).

### 10. **Review the Vietnamese translation**
You confirmed you speak Vietnamese, so read through `vi/index.html` and flag anything that sounds stiff or overly literal. Vietnamese legal/business writing has its own cadence — your ear will catch things I can't.

---

## 🚀 How to deploy (the fast path)

### Option 1: Netlify (recommended — free, easy)
1. Zip the `nalaw/` folder
2. Go to [netlify.com/drop](https://app.netlify.com/drop)
3. Drag the zip in — it's live in 30 seconds at a `*.netlify.app` URL
4. In Netlify settings, point `nalawtx.com` DNS to Netlify

### Option 2: Replace existing site
If your current site is on Wix, Squarespace, or a custom Next.js host — upload the `nalaw/` folder to any static web host and change DNS at your registrar to point to the new host.

### Option 3: Handoff to a developer
Send them the `nalaw/` folder and this README. Any developer can deploy this in under an hour — it's pure HTML, no build step.

---

## 🔧 How to update content later

Two Python generator scripts are included so you don't have to edit 20 practice pages by hand:

- `build_practice_pages.py` — all 20 practice area pages
- `build_attorneys.py` — all 5 attorney pages + team hub
- `build_toplevel.py` — results, about, contact, FAQs, blog

To update any of those, edit the data at the top of the script and re-run:
```bash
python3 build_practice_pages.py
```

Content-only changes to homepage, consultation, Spanish, or Vietnamese pages: edit the HTML directly.

---

## 📈 Ongoing SEO / GEO checklist (post-launch)

- Submit `sitemap.xml` to Google Search Console and Bing Webmaster Tools (I'll generate this if you want — ask).
- Set up Google Business Profile at `10050 Northwest Fwy #200, Houston, TX 77092` with 25+ photos, hours "24/7," attributes for "online consultations," "identifies as veteran-owned" (if applicable), and service list matching your practice areas.
- Build `sameAs` citations — Yelp, Avvo, Justia, Super Lawyers, Martindale, FindLaw, Chambers.
- Start publishing blog articles (I wrote 5 working titles — see `blog/index.html`).
- Build neighborhood landing pages (Spring Branch, Memorial, Bellaire, Sharpstown, Pasadena, Alief) — I can build these fast if you want.
- Run a monthly "Google Screened / Local Service Ads" check to maintain LSA eligibility.
- Upload client video testimonials (with written releases) — signed, grounded, Houston-accented testimonials crush generic text ones.

---

## 📞 Current contact points wired in

- Phone: **(713) 842-9442**
- Email: **info@nalawtx.com**
- Address: **10050 Northwest Freeway, Suite 200, Houston, TX 77092**
- Social links (in footer):
  - Facebook: facebook.com/nalawtx
  - Instagram: @vuwins
  - TikTok: @winwithnguyen
  - YouTube: thenguyenwithnguyen

**Brand unification recommendation:** Consolidate to one handle across all platforms — `@winwithnguyen` is the strongest because it matches the tagline and is already claimed on TikTok. Rename Instagram, YouTube, and Facebook to match once you have the bandwidth. This compounds over 2–3 years into real brand equity.

---

## ⚠️ Texas attorney-advertising compliance notes

- Every page footer already says "Attorney advertising" and "Past results do not guarantee future outcomes."
- Case results on `results.html` should (a) use real numbers from actual files and (b) clarify confidential settlements as "confidential" rather than invented dollar figures. Texas Disciplinary Rule 7.04 prohibits misleading advertising.
- The "99% client satisfaction" and "1,000+ cases handled" stats should be verifiable if challenged by the State Bar. If these numbers are estimates, consider softening to "hundreds of cases" or removing the specific number.
- Attorney bios must be accurate — that's the purpose of the `TO CONFIRM` markers.

---

## Questions? Adjustments?

Send me:
1. Your headshots + logo (drop them in this conversation)
2. Actual case results from firm files
3. Attorney credentials
4. Any content you want softened, sharpened, or rewritten

And I'll finalize everything.
