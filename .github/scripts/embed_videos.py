#!/usr/bin/env python3
"""Embed the firm's own YouTube videos on matching blog posts, with video schema.
Safe to run any number of times. Add a line to VIDEOS to embed another one."""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

# post slug -> (YouTube id, title, upload date, ISO 8601 duration)
VIDEOS = {
    "texas-eggshell-plaintiff-rule-pre-existing-conditions": ("mbhZHjQVd_E", "How Pre-Existing Conditions Affect Your Injury Settlement", "2024-07-30", "PT23S"),
    "texas-uninsured-motorist-coverage-what-houston-drivers-need": ("QV9hYKdiSNM", "Uninsured Driver Hit You? What to Do Next", "2024-08-13", "PT53S"),
    "houston-hit-and-run-victims-how-to-get-compensated": ("QFfZqvOQyqA", "Uninsured Driver Hit You? Here's What to Do", "2024-08-13", "PT53S"),
    "texas-personal-injury-deadlines-the-clock-is-already-running": ("f_rEkAxJ5wM", "Your Accident Claim Has an Expiration Date", "2024-08-20", "PT46S"),
    "recorded-statement-insurance-adjuster-what-to-say": ("TxDr4uYg3zc", "Insurance Company Calling After an Accident? Don't Say This", "2024-07-09", "PT1M6S"),
    "what-insurance-adjuster-recorded-statement-trap": ("vGwzXEMdCWg", "Insurance Company Calling After an Accident? How to Handle It", "2024-07-09", "PT1M6S"),
    "the-first-48-hours-after-a-texas-car-wreck-what-you-do-now": ("HDGikOGK0zs", "Just Had an Accident? Why Talking to Witnesses Is Crucial", "2024-08-17", "PT49S"),
    "do-i-need-a-lawyer-for-minor-car-accident": ("yG8uwRZFqQs", "Hurt in an Accident? When You Need Legal Representation", "2024-06-14", "PT47S"),
}


def embed(slug, vid, title, date, duration):
    path = ROOT / "blog" / f"{slug}.html"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if f"<!-- video:{vid} -->" in text:
        return False
    safe = html.escape(title, quote=True)
    block = (
        f"    <!-- video:{vid} -->\n"
        f"    <h2>Watch: {html.escape(title, quote=False)}</h2>\n"
        '    <div style="position: relative; padding-bottom: 56.25%; height: 0; margin-top: var(--s-md); border-radius: 8px; overflow: hidden;">\n'
        f'      <iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="{safe}" loading="lazy" '
        'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture" allowfullscreen '
        'style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"></iframe>\n'
        "    </div>\n\n"
    )
    m = re.search(r"\n[ \t]*<h2>Common questions</h2>", text)
    if m:
        text = text[:m.start() + 1] + block + text[m.start() + 1:]
    else:
        anchor = "<!-- related-links -->" if "<!-- related-links -->" in text else '<section class="cta-band">'
        wrapped = '<section class="section section--tight">\n  <div class="wrap" style="max-width: 820px;">\n' + block + "  </div>\n</section>\n\n"
        text = text.replace(anchor, wrapped + anchor, 1)
    schema = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": title,
        "description": f"{title}. A short video from Nguyen & Associates Injury Law Firm in Houston, Texas.",
        "thumbnailUrl": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
        "uploadDate": date,
        "duration": duration,
        "embedUrl": f"https://www.youtube-nocookie.com/embed/{vid}",
        "contentUrl": f"https://www.youtube.com/watch?v={vid}",
    }
    script = '<script type="application/ld+json">\n' + json.dumps(schema, indent=2, ensure_ascii=False) + "\n</script>\n"
    text = re.sub(r"</head>", lambda m: script + m.group(0), text, count=1, flags=re.I)
    path.write_text(text, encoding="utf-8")
    return True


if __name__ == "__main__":
    done = sum(embed(slug, *v) for slug, v in VIDEOS.items())
    print(f"Embedded {done} video(s).")
