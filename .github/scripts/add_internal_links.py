#!/usr/bin/env python3
"""Internal links between practice pages and blog posts. Safe to run any time.

1. Adds a "From our blog" section to each practice page, linking related posts.
2. Adds a "Keep reading" section to each blog post, linking its practice
   page(s) and related posts.
3. Replaces page titles that were cut off with a literal "…".

Runs after every new post. Posts listed in POSTS use the hand-picked practice
pages; any newer post is matched to practice pages by the KEYWORDS below.
"""
import html
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "<!-- related-links -->"
ANCHOR = '<section class="cta-band">'

# post slug -> practice pages it belongs with (most relevant first)
POSTS = {
    "do-i-need-a-lawyer-for-minor-car-accident": ["car-accident"],
    "fmcsa-hours-of-service-violations-your-texas-truck-accident": ["truck-accident"],
    "houston-bicycle-accident-claims-what-texas-law-actually": ["pedestrian"],
    "houston-hit-and-run-victims-how-to-get-compensated": ["car-accident", "pedestrian"],
    "houston-motorcycle-accident-lawyer-why-rider-bias-changes": ["motorcycle"],
    "houston-nursing-home-abuse-what-texas-law-lets-families": ["nursing-home"],
    "houston-rideshare-accidents-how-uber-amp-lyft-insurance": ["rideshare"],
    "houston-traffic-deaths-2024-record": ["pedestrian", "drunk-driver"],
    "hurt-in-a-houston-construction-zone-who-can-be-liable": ["construction", "workplace-injury", "truck-accident"],
    "injured-as-a-passenger-in-a-houston-car-wreck-heres-how-to": ["car-accident", "rideshare"],
    "injured-at-work-in-texas-how-non-subscriber-claims-work": ["workplace-injury", "construction", "oilfield"],
    "new-texas-laws-affecting-injury-claims": ["spinal-cord", "burn-injury"],
    "pedestrian-accidents-outside-crosswalks-texas-fault-rules": ["pedestrian"],
    "recorded-statement-insurance-adjuster-what-to-say": ["truck-accident", "rideshare"],
    "slip-and-fall-at-heb-kroger-or-walmart-in-houston": ["slip-fall", "premises-liability"],
    "suing-the-government-after-a-pothole-accident-in-texas": ["motorcycle", "premises-liability"],
    "texas-distracted-driving-laws-your-injury-claim": ["car-accident"],
    "texas-dog-bite-law-houston-what-victims-can-recover": ["dog-bite", "premises-liability"],
    "texas-dram-shop-law-in-houston-after-2025-supreme-court": ["drunk-driver", "wrongful-death"],
    "texas-eggshell-plaintiff-rule-pre-existing-conditions": ["brain-injury", "spinal-cord", "slip-fall"],
    "texas-hb-4145-what-the-2026-medical-billing-law-means-for": ["brain-injury", "spinal-cord", "burn-injury"],
    "texas-insurance-bad-faith-what-houston-claimants-can-recover": ["motorcycle", "car-accident"],
    "texas-nonsubscriber-employer-lawsuit-2025-the-ruling-that": ["workplace-injury", "oilfield", "refinery-explosion", "construction"],
    "texas-personal-injury-deadlines-the-clock-is-already-running": ["truck-accident", "dog-bite", "maritime", "product-liability", "nursing-home"],
    "texas-tort-reform-2025-the-medical-billing-cap-that-could": ["wrongful-death", "burn-injury", "brain-injury"],
    "texas-uninsured-motorist-coverage-what-houston-drivers-need": ["car-accident", "motorcycle"],
    "texas-wrongful-death-claims-who-can-sue-and-when": ["wrongful-death", "nursing-home", "refinery-explosion", "maritime"],
    "texass-51-fault-rule-how-it-can-reduce-or-eliminate-your": ["car-accident", "truck-accident", "motorcycle"],
    "texass-new-2026-av-law-driverless-car-accident-liability": ["rideshare", "product-liability"],
    "the-first-48-hours-after-a-texas-car-wreck-what-you-do-now": ["car-accident", "truck-accident"],
    "what-insurance-adjuster-recorded-statement-trap": ["truck-accident", "slip-fall"],
}

PRACTICE = {
    "brain-injury": "Brain Injury Cases",
    "burn-injury": "Burn Injury Cases",
    "car-accident": "Car Accidents",
    "construction": "Construction Accidents",
    "dog-bite": "Dog Bites",
    "drunk-driver": "Drunk Driver Crashes",
    "maritime": "Maritime Injuries",
    "motorcycle": "Motorcycle Accidents",
    "nursing-home": "Nursing Home Abuse",
    "oilfield": "Oilfield Injuries",
    "pedestrian": "Pedestrian &amp; Bicycle Accidents",
    "premises-liability": "Premises Liability",
    "product-liability": "Defective Products",
    "refinery-explosion": "Refinery &amp; Plant Explosions",
    "rideshare": "Uber &amp; Lyft Accidents",
    "slip-fall": "Slip &amp; Fall",
    "spinal-cord": "Spinal Cord Injuries",
    "truck-accident": "18-Wheeler &amp; Truck Accidents",
    "workplace-injury": "Workplace Injuries",
    "wrongful-death": "Wrongful Death",
}

# For posts not listed in POSTS: first matching practice pages win (max 2).
KEYWORDS = [
    ("truck-accident", r"truck|18-wheeler|fmcsa|tractor-trailer"),
    ("motorcycle", r"motorcycle|biker"),
    ("rideshare", r"uber|lyft|rideshare|driverless|autonomous"),
    ("pedestrian", r"pedestrian|bicycle|cyclist|crosswalk|scooter"),
    ("drunk-driver", r"drunk|dwi|dram shop|intoxicated"),
    ("nursing-home", r"nursing home|elder abuse|assisted living"),
    ("dog-bite", r"dog bite|dog attack"),
    ("slip-fall", r"slip|trip and fall"),
    ("premises-liability", r"premises|negligent security|apartment|property owner"),
    ("construction", r"construction|scaffold|crane"),
    ("oilfield", r"oilfield|oil field|drilling|pipeline"),
    ("refinery-explosion", r"refinery|explosion|chemical plant"),
    ("maritime", r"maritime|jones act|offshore|longshore"),
    ("workplace-injury", r"workplace|at work|non-?subscriber|workers' comp|employer"),
    ("wrongful-death", r"wrongful death|fatal|survival claim"),
    ("brain-injury", r"brain|concussion|tbi"),
    ("spinal-cord", r"spinal|paralysis|herniated"),
    ("burn-injury", r"burn"),
    ("product-liability", r"defective|product liability|recall"),
    ("car-accident", r"car|crash|wreck|collision|driver|driving|insurance|adjuster"),
]

TITLES = {
    "intersections/capitol-milam-downtown.html": "Crashes at Capitol & Milam | Houston Injury Attorney",
    "intersections/bissonnet-beltway-8.html": "Crashes at Bissonnet & Beltway 8 | Houston Injury Attorney",
    "intersections/fm-1960-cutten-road.html": "Crashes at FM 1960 & Cutten Road | Houston Injury Attorney",
    "intersections/hardy-toll-sam-houston.html": "Crashes at Hardy Toll Road & Beltway 8 | Houston Injury Attorney",
    "intersections/westheimer-beltway-8.html": "Crashes at Westheimer & Beltway 8 | Houston Injury Attorney",
    "intersections/bellaire-beltway-8.html": "Crashes at Bellaire & Beltway 8 | Houston Injury Attorney",
    "intersections/i-10-at-grand-parkway.html": "Crashes at I-10 & Grand Parkway | Houston Injury Attorney",
    "intersections/beechnut-beltway-8.html": "Crashes at Beechnut & Beltway 8 | Houston Injury Attorney",
    "intersections/westheimer-south-gessner.html": "Crashes at Westheimer & Gessner | Houston Injury Attorney",
    "intersections/i-45-beltway-8.html": "Crashes at I-45 & Beltway 8 | Houston Injury Attorney",
    "intersections/fm-1960-west-lake-houston-parkway.html": "Crashes at FM 1960 & W. Lake Houston Pkwy | Houston Injury Attorney",
    "intersections/wilcrest-westheimer.html": "Crashes at Wilcrest & Westheimer | Houston Injury Attorney",
    "locations/clear-lake.html": "Clear Lake & League City Injury Lawyer | Nguyen & Associates",
    "es/practice/index.html": "Áreas de Práctica | Abogados de Lesiones Personales en Houston",
    "vi/practice/index.html": "Lĩnh Vực Hành Nghề | Luật Sư Thương Tích Cá Nhân Houston",
    "blog/what-insurance-adjuster-recorded-statement-trap.html": "Insurance Adjuster Recorded Statement Trap: How to Avoid It",
    "blog/do-i-need-a-lawyer-for-minor-car-accident.html": "Do I Need a Lawyer for a Minor Car Accident in Houston?",
    "blog/new-texas-laws-affecting-injury-claims.html": "Texas Laws to Know Before Filing an Injury Claim in 2026",
    "blog/houston-traffic-deaths-2024-record.html": "Houston's 2024 Traffic Death Record: What It Means for Drivers",
    "index.html": "Houston Personal Injury Lawyers | Nguyen & Associates",
    "guides/texas-statute-of-limitations.html": "Texas Personal Injury Statute of Limitations: Full Guide",
    "guides/how-to-read-texas-crash-report.html": "How to Read a Texas Crash Report (Form CR-3) | Nguyen & Associates",
    "guides/first-24-hours-after-accident.html": "First 24 Hours After a Houston Car Accident: What to Do",
    "guides/uber-lyft-insurance-explained.html": "How Uber and Lyft Insurance Works After a Houston Crash",
    "guides/texas-dram-shop-law.html": "Texas Dram Shop Law Guide: Suing Bars After Drunk Driver Crashes",
    "guides/texas-comparative-fault.html": "Texas Modified Comparative Fault: The 51% Bar Explained",
    "guides/insurance-adjuster-tactics.html": "Insurance Adjuster Tactics: What They Don't Want You to Know",
    "practice/truck-accident.html": "Houston 18-Wheeler & Truck Accident Lawyer | Nguyen & Associates",
    "practice/premises-liability.html": "Houston Premises Liability Lawyer | Nguyen & Associates",
    "practice/refinery-explosion.html": "Houston Refinery & Plant Explosion Lawyer | Nguyen & Associates",
    "practice/pedestrian.html": "Houston Pedestrian & Bicycle Accident Lawyer | Nguyen & Associates",
    "practice/slip-fall.html": "Houston Slip & Fall Lawyer | Nguyen & Associates",
    "practice/workplace-injury.html": "Houston Workplace Injury Lawyer | Nguyen & Associates",
    "practice/product-liability.html": "Houston Product Liability Lawyer | Nguyen & Associates",
    "practice/nursing-home.html": "Houston Nursing Home Abuse Lawyer | Nguyen & Associates",
    "practice/subtopics/delivery-truck-accident.html": "FedEx, UPS & Amazon Truck Accident Lawyer | Houston",
    "practice/subtopics/t-bone-intersection-collision.html": "T-Bone & Intersection Crash Lawyer | Houston | Nguyen & Associates",
}

CARD = (
    '      <a href="{href}" style="display:block; padding: var(--s-md); background: var(--cream); '
    "border: 1px solid var(--line-soft); border-radius: 8px; text-decoration: none; color: var(--ink); "
    'transition: border-color 0.2s, transform 0.2s;">\n'
    '        <strong style="display:block; font-family: var(--f-display); font-size: 1.1rem; '
    'font-weight: 500; color: var(--navy); margin-bottom: 0.25rem;">{title}</strong>\n'
    '        <span style="font-size: 0.88rem; color: var(--muted);">{sub} →</span>\n'
    "      </a>\n"
)


def section(eyebrow, heading, cards):
    return (
        f"{MARK}\n"
        '<section class="section section--tight" style="background: var(--cream-2); '
        'border-top: 1px solid var(--line-soft);">\n'
        '  <div class="wrap">\n'
        f'    <span class="t-eyebrow t-eyebrow--red">{eyebrow}</span>\n'
        '    <h2 class="t-display" style="font-size:1.6rem; font-weight:380; margin-top: 0.5rem; '
        f'margin-bottom: var(--s-md);">{heading}</h2>\n'
        '    <div class="related-grid" style="display: grid; grid-template-columns: '
        'repeat(auto-fit, minmax(240px, 1fr)); gap: var(--s-md);">\n'
        f"{''.join(cards)}"
        "    </div>\n"
        "  </div>\n"
        "</section>\n\n"
    )


def post_title(slug):
    text = (ROOT / "blog" / f"{slug}.html").read_text(encoding="utf-8")
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    title = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)).split())
    return title.replace(" .", ".").replace(" ,", ",").replace(" ?", "?")


def guess_areas(slug, title):
    text = f"{slug.replace('-', ' ')} {title}".lower()
    areas = [a for a, pattern in KEYWORDS if re.search(rf"\b(?:{pattern})", text)]
    return areas[:2] or ["car-accident"]


def append_cards(path, cards):
    """Add cards to a page's existing link section, skipping ones already there."""
    text = path.read_text(encoding="utf-8")
    start = text.index(MARK)
    end = text.index("    </div>\n  </div>\n</section>", start)
    new = [c for c in cards if re.search(r'href="[^"]*"', c).group(0) not in text[start:end]]
    if not new:
        return False
    path.write_text(text[:end] + "".join(new) + text[end:], encoding="utf-8")
    return True


def insert(path, block):
    text = path.read_text(encoding="utf-8")
    if MARK in text or ANCHOR not in text:
        return False
    path.write_text(text.replace(ANCHOR, block + ANCHOR, 1), encoding="utf-8")
    return True


def add_links():
    slugs = sorted(p.stem for p in (ROOT / "blog").glob("*.html") if p.name != "index.html")
    titles = {s: post_title(s) for s in slugs}
    posts = {s: POSTS.get(s) or guess_areas(s, titles[s]) for s in slugs}
    done = 0

    for area, name in PRACTICE.items():
        slugs = [s for s, areas in posts.items() if area in areas]
        slugs.sort(key=lambda s: posts[s].index(area))
        if not slugs:
            continue
        cards = [CARD.format(href=f"../blog/{s}.html", title=titles[s], sub="Read the article") for s in slugs]
        page = ROOT / "practice" / f"{area}.html"
        if MARK in page.read_text(encoding="utf-8"):
            done += append_cards(page, cards)
        else:
            done += insert(page, section("From our blog", "Answers to common questions.", cards))

    for slug, areas in posts.items():
        cards = [
            CARD.format(href=f"../practice/{a}.html", title=PRACTICE[a], sub="How we handle these cases")
            for a in areas[:2]
        ]
        related = sorted(
            (s for s in posts if s != slug and set(posts[s]) & set(areas)),
            key=lambda s: -len(set(posts[s]) & set(areas)),
        )[:3]
        cards += [CARD.format(href=f"{s}.html", title=titles[s], sub="Read the article") for s in related]
        done += insert(ROOT / "blog" / f"{slug}.html", section("Keep reading", "Related cases and articles.", cards))

    print(f"Added or updated link sections on {done} pages.")


def fix_titles():
    done = 0
    for rel, title in TITLES.items():
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        esc = html.escape(title, quote=False)
        new = re.sub(r"<title>[^<]*…[^<]*</title>", lambda m: f"<title>{esc}</title>", text)
        new = re.sub(
            r'(<meta\s+(?:property|name)="(?:og|twitter):title"\s+content=")[^"]*…[^"]*(")',
            lambda m: m.group(1) + html.escape(title, quote=True) + m.group(2),
            new,
        )
        if new != text:
            path.write_text(new, encoding="utf-8")
            done += 1
    print(f"Fixed {done} cut-off titles.")


if __name__ == "__main__":
    add_links()
    fix_titles()
