# Blog Agent — Setup Guide (Phase 1)

This is the v1 of the blog automation system for nalawtx.com. Once set up, every other Monday morning a draft blog post appears as a PR in this repo, ready for your 5-minute review and merge.

**Phase 1 scope:** CEO + Writer agents. The other 8 agents (Editor, Compliance, Researcher, Topical Sensitivity, Analytics, Distribution, Internal Linker, Citation) will be layered on in subsequent phases. This Phase 1 already gives you a working autonomous blog pipeline.

---

## What you're setting up

```
[Google Sheet]         ← you add topics here
       ↓
[GitHub Action]        ← fires every other Monday at 9am CT
       ↓
[CEO orchestrator]     ← runs the pipeline
       ↓
[Writer agent]         ← calls Claude API to write the post
       ↓
[blog/{slug}.html]     ← new file committed to a PR branch
       ↓
[Pull Request]         ← you review, edit if needed, merge
       ↓
[Netlify auto-deploy]  ← post goes live at nalawtx.com/blog/{slug}.html
```

---

## One-time setup (estimated 30-45 min total)

### Step 1 — Create the Google Sheet

1. Go to [sheets.google.com](https://sheets.google.com) → create a new sheet
2. Name it: `NA Law — Blog Agent`
3. Create 5 tabs (rename `Sheet1` and add 4 more):

#### Tab 1: `Blog Topics`
Row 1 (headers, exactly these labels):

| Status | Topic | Target Keyword | Priority | Notes | Date Generated | Draft URL | Date Published | Published URL |

Seed the queue with 8-10 topics. Below are 8 strong starter topics — paste them in starting at row 2:

| Status | Topic | Target Keyword | Priority |
|--------|-------|----------------|----------|
| Queued | What to do in the first 48 hours after a Texas car wreck | what to do after car accident texas | High |
| Queued | How Texas's 51% modified comparative fault rule reduces your recovery | texas comparative fault rule | High |
| Queued | Statute of limitations for personal injury in Texas: the deadlines you can't miss | texas personal injury statute of limitations | High |
| Queued | The insurance adjuster recorded statement trap (and exactly what to say) | recorded statement insurance adjuster | High |
| Queued | Recoverable damages in a Texas personal injury claim: plain-English breakdown | texas personal injury damages | Medium |
| Queued | What to do if you get hit by an 18-wheeler on I-45 or I-10 in Houston | houston truck accident lawyer | Medium |
| Queued | When you actually need a lawyer for a Houston car accident (and when you don't) | when to hire car accident lawyer houston | Medium |
| Queued | Houston's most dangerous intersections in 2026: where injuries cluster | dangerous intersections houston | Medium |

#### Tab 2: `Generation Log`
Row 1 headers:

| Timestamp | Topic | Status | Tokens In | Tokens Out | Cost USD | Notes |

(Leave the rest blank — agent fills this in over time.)

#### Tab 3: `Published Index`
Row 1 headers:

| Title | Slug | Date Published | Target Keyword | Key Claims | Statutes Cited |

(Leave blank — agent appends here when posts go live. For now, you can manually add the 4 existing blog posts you have so the Writer doesn't accidentally duplicate them.)

#### Tab 4: `Brand Voice Bank`
Row 1 headers:

| Sample Text | Source | Notes |

Paste 3-5 paragraphs of YOUR firm's own writing in column A so the Writer has real examples to match. Good sources:
- Your consultation.html page hero copy
- Your about.html "story" section
- Snippets from attorney bios that sound like the firm voice
- Sections from existing blog posts you wrote yourself

The more authentic samples here, the less AI-sounding the output.

#### Tab 5: `Statute Reference`
Row 1 headers:

| Citation | Description | Common Topic Tags |

Pre-seeded reference list — paste these in:

| Citation | Description | Common Topic Tags |
|----------|-------------|-------------------|
| Texas Civil Practice & Remedies Code § 16.003 | Two-year statute of limitations for personal injury actions in Texas | statute of limitations, deadlines, filing |
| Texas Civil Practice & Remedies Code § 33.001 | Modified comparative fault — 51% bar; recovery reduced by plaintiff's percentage of responsibility | comparative fault, liability, fault |
| Texas Civil Practice & Remedies Code § 41.001 | Definitions and procedures for exemplary (punitive) damages | punitive damages, exemplary damages |
| Texas Civil Practice & Remedies Code § 41.008 | Caps on exemplary damages (typically greater of $200K or 2x economic damages + non-economic up to $750K) | damages caps, punitive damages |
| Texas Civil Practice & Remedies Code § 18.091 | Past medical expenses limited to amounts actually paid or incurred (collateral source) | medical bills, damages |
| Texas Transportation Code § 545.351 | General duty to drive at a reasonable and prudent speed under conditions | speeding, traffic violations |
| Texas Transportation Code § 545.062 | Following too closely (tailgating) | rear-end collision, following distance |
| Texas Transportation Code § 545.151 | Stop signs and yield signs — right of way | intersection collision, right of way |
| Texas Alcoholic Beverage Code § 2.02 | Dram Shop Act — liability for serving alcohol to obviously intoxicated person | drunk driving, dram shop, bar liability |
| Texas Family Code § 71.004 | Definition of "family violence" (for related premises liability and assault cases) | premises liability, assault |

4. **Copy the Sheet's ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/[THIS_IS_THE_SHEET_ID]/edit
   ```
   You'll need this for Step 4.

---

### Step 2 — Create a Google Cloud service account

This is the "robot" that the agent uses to read/write your Sheet. ~10 min, completely free.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → sign in
2. Top bar → project dropdown → **New Project**
3. Name: `nalaw-blog-agent` → Create
4. Wait ~30 sec for the project to provision, then select it from the project dropdown
5. Left sidebar → **APIs & Services** → **Library**
6. Search **"Google Sheets API"** → click → **Enable**
7. Left sidebar → **APIs & Services** → **Credentials**
8. Top bar → **+ Create Credentials** → **Service account**
9. Service account name: `blog-agent`
10. ID: `blog-agent` (auto-fills)
11. Click **Create and Continue**
12. Role: skip (just click **Continue**)
13. Click **Done**
14. You're back on the Credentials page. Click on the new service account row (`blog-agent@nalaw-blog-agent.iam.gserviceaccount.com`)
15. Top tab: **Keys** → **Add Key** → **Create new key** → **JSON** → **Create**
16. A `.json` file downloads to your computer. **Keep this file secret** — it's the equivalent of a password.
17. **Copy the service account email address** (`blog-agent@nalaw-blog-agent.iam.gserviceaccount.com`)

### Step 3 — Share your Sheet with the service account

1. Go back to your Google Sheet
2. Click **Share** (top right)
3. Paste the service account email (`blog-agent@nalaw-blog-agent.iam.gserviceaccount.com`)
4. Change permission to **Editor**
5. **Uncheck "Notify people"** (the email is a robot, it doesn't read mail)
6. Click **Share**

### Step 4 — Add secrets to GitHub

1. Go to your repo: `https://github.com/voostervu/nalawtx-website`
2. Click **Settings** (top tab) → **Secrets and variables** → **Actions**
3. Add three repository secrets (**New repository secret** button each time):

   - **Name:** `ANTHROPIC_API_KEY`
     **Value:** your Anthropic API key (from console.anthropic.com → Settings → API Keys)

   - **Name:** `GOOGLE_CREDENTIALS_JSON`
     **Value:** the entire contents of the JSON file you downloaded in Step 2.16. Open it in a text editor, copy the whole thing (starting with `{` and ending with `}`), paste as the secret value.

   - **Name:** `BLOG_AGENT_SHEET_ID`
     **Value:** the Sheet ID you copied in Step 1.4

### Step 5 — Add the blog agent files to your repo

The blog agent lives in `.github/` so Netlify won't deploy it.

1. Download / receive the file package
2. Copy the files into your repo's `.github/` directory matching this structure:
   ```
   .github/
   ├── workflows/
   │   └── blog-agent.yml
   ├── scripts/
   │   ├── ceo.py
   │   ├── writer.py
   │   ├── sheets.py
   │   ├── utils.py
   │   └── requirements.txt
   └── prompts/
       └── writer.md
   ```
3. Commit and push to `main`:
   ```bash
   git add .github/
   git commit -m "Add blog agent (Phase 1)"
   git push origin main
   ```

### Step 6 — Test with a manual run

Before turning on the cron schedule, do a manual test fire:

1. Go to your repo → **Actions** tab
2. Click **Blog Agent** in the left sidebar
3. Click **Run workflow** (top right of the workflow run list)
4. Select branch `main` → **Run workflow**
5. Wait ~2-4 minutes
6. Refresh the page — you should see a new workflow run with green checkmarks
7. Click into the run to see the log
8. If successful, you'll see a new PR in your **Pull requests** tab

### Step 7 — Review the first PR

1. Open the PR — it'll be titled "Blog draft: [whatever the first topic was]"
2. Click the **Files changed** tab — you'll see:
   - A new `blog/{slug}.html` file
   - An update to `blog/index.html` adding the new post to the listing
3. Read the post. Edit anything you want directly in GitHub (pencil icon on the file).
4. Once happy, click **Merge pull request**
5. Netlify auto-deploys. Post is live at `https://nalawtx.com/blog/{slug}.html` in ~60 seconds.

### Step 8 — Verify Sheets logging

Check your Sheet:
- The topic row in `Blog Topics` should now show status "Drafted" with a Date Generated and Draft URL
- The `Generation Log` should have a new row with token counts and cost
- Add the post to `Published Index` (Phase 2 will auto-append this on merge)

---

## What happens going forward

Once the manual test succeeds, the cron schedule takes over. Every other Monday at 9am Central:

- Agent picks the next Queued topic (highest priority first)
- Generates a draft
- Opens a PR
- You get a GitHub email notification
- You review when you have 5 minutes (phone, desktop, whenever)
- Merge → published

**To pause:** disable the workflow in Actions tab. Anytime.
**To speed up:** add more topics with High priority, change the cron to weekly.
**To slow down:** add fewer topics; agent skips weeks gracefully if the queue is empty.

---

## Tuning the Writer

The Writer's behavior is entirely controlled by `.github/prompts/writer.md`. To improve output:

1. After a few posts, identify any patterns you want changed (too wordy? too formal? specific phrases keep appearing?)
2. Edit `prompts/writer.md` directly in GitHub
3. Commit changes
4. Next run uses the updated prompt

This is what we mean by **versioned prompts** (Upgrade C) — every prompt change is in git history, easy to roll back, easy to A/B test.

---

## Phase 2+ roadmap

After Phase 1 has been running for a few weeks and you've confirmed quality is on track, we'll layer in the other agents:

- **Phase 2:** Add Editor (humanize/voice polish)
- **Phase 3:** Add Compliance + Citation (Texas Bar audit + statute accuracy)
- **Phase 4:** Add Researcher (Search Console + web search for topic discovery)
- **Phase 5:** Add Topical Sensitivity (current events awareness)
- **Phase 6:** Add Internal Linker (auto-link to practice pages, attorneys, FAQ)
- **Phase 7:** Add Distribution (LinkedIn, IG, FB, Twitter, TikTok script repurposing)
- **Phase 8:** Add Analytics (GA4 + Search Console feedback loop)
- **Phase 9:** Add OG card auto-generation utility

Each phase is a smaller change once Phase 1 is stable.

---

## Troubleshooting

**Action fails with "GOOGLE_CREDENTIALS_JSON not found"**
You missed a secret in Step 4. Double-check Settings → Secrets and Variables → Actions.

**Action fails with "Spreadsheet not found"**
Either your `BLOG_AGENT_SHEET_ID` is wrong, or you forgot Step 3 (sharing the Sheet with the service account email).

**Action runs but generates no PR ("No Queued topics found")**
Your `Blog Topics` tab has no rows with Status = "Queued". Add some.

**Generated HTML looks malformed**
Check the prompt file (`.github/prompts/writer.md`). If you edited it, you may have broken the template structure. Roll back via git.

**Post looks visually different from the rest of the site**
The Writer template might have drifted from your actual site CSS. The prompt embeds the template directly — keep it in sync if you update the main site's nav/footer/styling.

**Costs higher than expected**
Check `Generation Log` for per-post token counts. If consistently high, the prompt may be allowing too-long outputs. Adjust the `max_tokens` parameter in `writer.py` (currently 8000).

---

## Questions

If anything breaks or you want to add features, open an issue or send context to the next Claude session. The system is designed to be iteratively improved.
