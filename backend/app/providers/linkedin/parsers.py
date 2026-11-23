"""Pure HTML -> data functions for LinkedIn profile pages.

No browser, no network: each function takes page HTML and returns normalized
objects, so they are unit-tested against saved fixtures.

LinkedIn serves two front ends. The current one (checked against a live profile
in Nov 2026) has hashed, meaningless class names, so the `_sdui_*` parsers rely
on the few stable hooks it has: `data-testid`, `componentkey` prefixes, headings
and the order of `<p>` lines. The older one has semantic class names and is
handled by the `_legacy_*` parsers. Each public function tries the current
markup first and falls back to the legacy one.

Every selector lives in this file; when a field comes back empty, save the page
HTML as a fixture, adjust the selector here and add a test.
"""

import base64
import binascii
import re
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from app.providers.base import (
    ScrapedActivity,
    ScrapedContact,
    ScrapedEducation,
    ScrapedExperience,
)
from app.utils.dates import (
    looks_like_date_range,
    parse_date_range,
    parse_relative_time,
    parse_year_range,
)

_WS = re.compile(r"\s+")
_COUNT = re.compile(r"([\d,.]+)\s*([KkMm])?")
_COMMENTS = re.compile(r"([\d,.]+\s*[KkMm]?)\s+comments?", re.IGNORECASE)
_EMPLOYMENT_TYPES = {
    "full-time", "part-time", "self-employed", "freelance", "contract",
    "internship", "apprenticeship", "seasonal", "trainee",
}  # fmt: skip
_CONTACT_TYPES = [
    ("email", "email"),
    ("phone", "phone"),
    ("website", "website"),
    ("twitter", "twitter"),
    ("birthday", "birthday"),
    ("address", "address"),
    ("im", "im"),
]


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _text(node: Tag | None) -> str | None:
    if node is None:
        return None
    text = _WS.sub(" ", node.get_text(" ", strip=True)).strip()
    return text or None


def _count(text: str | None) -> int | None:
    """'1,234' -> 1234, '2.5K' -> 2500."""
    match = _COUNT.search(text or "")
    if not match:
        return None
    try:
        number = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    scale = {"k": 1_000, "m": 1_000_000}.get((match.group(2) or "").lower(), 1)
    return int(number * scale)


# --- main profile page ------------------------------------------------------


def _legacy_top_card(soup: BeautifulSoup) -> dict[str, str | None]:
    main = soup.find("main") or soup
    assert isinstance(main, Tag)

    photo = main.select_one(
        "img.pv-top-card-profile-picture__image--show, img.pv-top-card-profile-picture__image, "
        "img.profile-photo-edit__preview"
    )
    photo_url = photo.get("src") if photo else None

    about = None
    anchor = main.select_one("#about")
    section = anchor.find_parent("section") if anchor else None
    if section:
        about = _text(
            section.select_one('.inline-show-more-text span[aria-hidden="true"]')
            or section.select_one(".inline-show-more-text")
            or section.select_one(".display-flex.full-width")
        )

    return {
        "full_name": _text(main.select_one("h1")),
        "headline": _text(main.select_one("div.text-body-medium")),
        "location": _text(main.select_one("span.text-body-small.inline.t-black--light")),
        "photo_url": photo_url
        if isinstance(photo_url, str) and photo_url.startswith("http")
        else None,
        "about": about,
    }


# --- contact info overlay ---------------------------------------------------


def _legacy_contact_info(soup: BeautifulSoup) -> list[ScrapedContact]:
    contacts: list[ScrapedContact] = []
    for section in soup.select("section.pv-contact-info__contact-type"):
        header = (_text(section.select_one("h3")) or "").lower()
        kind = next((k for needle, k in _CONTACT_TYPES if needle in header), None)
        if kind is None:
            continue  # e.g. "Your Profile" / "<name>'s Profile" — the URL we already have

        values: list[str] = []
        for link in section.select("a[href]"):
            href = str(link.get("href", ""))
            if href.startswith("mailto:"):
                values.append(href.removeprefix("mailto:"))
            elif href.startswith("tel:"):
                values.append(href.removeprefix("tel:"))
            elif href.startswith("http"):
                values.append(href)
        if not values:
            for node in section.select("li span.t-14, span.t-14.t-black.t-normal, div.t-14 span"):
                value = _text(node)
                # Skip label-only spans such as "(Mobile)" or "(Portfolio)".
                if value and not (value.startswith("(") and value.endswith(")")):
                    values.append(value)
        contacts.extend(ScrapedContact(type=kind, value=v.strip()) for v in values if v.strip())
    return contacts


# --- /details/experience and /details/education ------------------------------


def _visible_lines(node: Tag, exclude: list[Tag] | None = None) -> list[str]:
    """LinkedIn renders each visible line as span[aria-hidden=true] next to a
    screen-reader duplicate. Returns those lines, skipping anything inside `exclude`."""
    lines: list[str] = []
    for span in node.select('span[aria-hidden="true"]'):
        if exclude and any(parent in exclude for parent in span.parents):
            continue
        text = _text(span)
        if text:
            lines.append(text)
    return lines


def _top_level_items(soup: BeautifulSoup) -> list[Tag]:
    items = soup.select("li.pvs-list__paged-list-item")
    if not items:
        items = soup.select("li.artdeco-list__item")
    return [li for li in items if li.find_parent("li") is None]


def _split_company(line: str | None) -> tuple[str | None, str | None]:
    """'Acme · Full-time' -> ('Acme', 'Full-time')."""
    if not line:
        return None, None
    parts = [p.strip() for p in line.split("·")]
    if len(parts) > 1 and parts[-1].lower() in _EMPLOYMENT_TYPES:
        return " · ".join(parts[:-1]) or None, parts[-1]
    return line, None


def _role_from_lines(lines: list[str], company: str | None = None) -> ScrapedExperience | None:
    if not lines:
        return None
    title, rest = lines[0], lines[1:]
    employment_type = None

    date_index = next((i for i, line in enumerate(rest) if looks_like_date_range(line)), None)
    before = rest[:date_index] if date_index is not None else rest[:1]
    after = rest[date_index + 1 :] if date_index is not None else rest[1:]

    for line in before:
        name, kind = _split_company(line)
        if line.lower() in _EMPLOYMENT_TYPES:
            employment_type = line
        elif company is None:
            company, employment_type = name, kind or employment_type
        else:
            employment_type = kind or employment_type

    start, end, current = parse_date_range(rest[date_index]) if date_index is not None else (
        None, None, False,
    )  # fmt: skip
    location = None
    description_lines = after
    if after and len(after[0]) < 80 and not after[0].endswith("."):
        location, description_lines = after[0], after[1:]

    return ScrapedExperience(
        title=title,
        company=company,
        employment_type=employment_type,
        location=location,
        start_date=start,
        end_date=end,
        is_current=current,
        description="\n".join(description_lines) or None,
    )


def _legacy_experiences(soup: BeautifulSoup) -> list[ScrapedExperience]:
    experiences: list[ScrapedExperience] = []
    for item in _top_level_items(soup):
        nested = [
            li for li in item.select("li") if _visible_lines(li) and li.select_one("li") is None
        ]
        own_lines = _visible_lines(item, exclude=nested)
        nested_roles = [li for li in nested if any(map(looks_like_date_range, _visible_lines(li)))]
        own_has_dates = any(looks_like_date_range(line) for line in own_lines[1:3])

        if nested_roles and not own_has_dates:
            # Several roles at one company: outer item is the company, nested items are roles.
            company, _ = _split_company(own_lines[0] if own_lines else None)
            for li in nested_roles:
                role = _role_from_lines(_visible_lines(li), company=company)
                if role:
                    experiences.append(role)
        else:
            role = _role_from_lines(_visible_lines(item))
            if role:
                experiences.append(role)
    return experiences


def _legacy_educations(soup: BeautifulSoup) -> list[ScrapedEducation]:
    educations: list[ScrapedEducation] = []
    for item in _top_level_items(soup):
        lines = _visible_lines(item)
        if not lines:
            continue
        school, rest = lines[0], lines[1:]
        degree = field = None
        start_year = end_year = None
        description: list[str] = []
        for line in rest:
            if start_year is None and looks_like_date_range(line):
                start_year, end_year = parse_year_range(line)
            elif degree is None and start_year is None:
                parts = [p.strip() for p in line.split(",", 1)]
                degree = parts[0] or None
                field = parts[1] if len(parts) > 1 else None
            else:
                description.append(line)
        educations.append(
            ScrapedEducation(
                school=school,
                degree=degree,
                field_of_study=field,
                start_year=start_year,
                end_year=end_year,
                description="\n".join(description) or None,
            )
        )
    return educations


# --- /recent-activity/all ----------------------------------------------------


def _legacy_activities(
    soup: BeautifulSoup, limit: int, now: datetime | None
) -> list[ScrapedActivity]:
    activities: list[ScrapedActivity] = []
    for post in soup.select("div.feed-shared-update-v2"):
        urn = post.get("data-urn")
        header = (_text(post.select_one(".update-components-header")) or "").lower()
        if "reposted" in header:
            kind = "repost"
        elif "commented" in header or "replied" in header:
            kind = "comment"
        elif post.select_one(".update-components-article"):
            kind = "article"
        else:
            kind = "post"

        counts = post.select_one(".social-details-social-counts")
        comments_match = _COMMENTS.search(_text(counts) or "")
        activities.append(
            ScrapedActivity(
                kind=kind,
                text=_text(
                    post.select_one(".update-components-text")
                    or post.select_one(".feed-shared-inline-show-more-text")
                ),
                url=f"https://www.linkedin.com/feed/update/{urn}/" if urn else None,
                posted_at=parse_relative_time(
                    _text(post.select_one(".update-components-actor__sub-description")), now
                ),
                reactions_count=_count(
                    _text(post.select_one(".social-details-social-counts__reactions-count"))
                ),
                comments_count=_count(comments_match.group(1)) if comments_match else None,
            )
        )
        if len(activities) >= limit:
            break
    return activities


# --- current markup (server-driven UI, hashed class names) --------------------

_ITEM = '[componentkey^="entity-collection-item"]'
_EXPANDABLE = '[data-testid="expandable-text-box"]'
# "4d", "• 2w", "with 3 others • 4d", "2w • Edited"
_AGE = re.compile(r"(?:^|•\s*)(\d+\s?(?:mo|yr|s|m|h|d|w)s?)(?=\s|•|$)")
_REACTIONS = re.compile(r"([\d,.]+\s*[KkMm]?)\s+reactions?", re.IGNORECASE)


def _multiline(node: Tag | None) -> str | None:
    """Text of a node with <br> kept as line breaks (descriptions, about, posts)."""
    if node is None:
        return None
    parts: list[str] = []
    for child in node.descendants:
        if isinstance(child, Tag):
            if child.name == "br":
                parts.append("\n")
            elif child.name == "button":  # the "… more" toggle
                break
        elif not any(p.name == "button" for p in child.parents if p is not node):
            parts.append(str(child))
    lines = [_WS.sub(" ", line).strip() for line in "".join(parts).split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return text or None


def _unwrap_link(href: str) -> str:
    """LinkedIn routes outbound links through /safety/go/?url=<real url>."""
    if "/safety/go" in href:
        target = parse_qs(urlparse(href).query).get("url")
        if target:
            return target[0]
    return href


def _item_lines(item: Tag) -> tuple[list[str], str | None]:
    """Header lines of one experience/education entry, plus its free-text description.
    Lines inside overlay links (attached media, the trailing "skills" line) are dropped."""
    lines: list[str] = []
    description = None
    for p in item.select("p"):
        box = p.select_one(_EXPANDABLE)
        if box is not None:
            description = _multiline(box)
            continue
        text = _text(p)
        if not text or text.startswith("Skills:") or p.select_one('a[href*="skill"]'):
            continue
        if p.find_parent("a", href=_OVERLAY):
            continue
        lines.append(text)
    return lines, description


def _sdui_items(soup: BeautifulSoup, section_testid: str) -> list[Tag]:
    section = soup.select_one(f'[data-testid^="{section_testid}"]')
    if section is None:
        return []
    return [
        i for i in section.select(_ITEM) if i.find_parent(attrs={"componentkey": _ITEM_KEY}) is None
    ]


_ITEM_KEY = re.compile(r"^entity-collection-item")
_OVERLAY = re.compile(r"/overlay/")


# Lines that can sit between the name and the headline: connection degree
# ("· 3rd"), pronouns ("He/Him"), bare separators.
_NAME_BADGE = re.compile(r"^(?:[·•]\s*)?(?:1st|2nd|3rd\+?|\w+/\w+(?:/\w+)?)?$", re.IGNORECASE)


def _sdui_top_card(soup: BeautifulSoup) -> dict[str, str | None] | None:
    main = soup.find("main")
    if not isinstance(main, Tag) or soup.select_one("[data-sdui-screen]") is None:
        return None
    name = main.select_one('[componentkey^="ProfileVerificationTriggerRef"] h2, h2')
    card = name.find_parent("section") if name else None
    if name is None or card is None:
        return None

    lines = [
        text
        for p in name.find_all_next("p")
        if isinstance(p, Tag)
        and card in p.parents
        and (text := _text(p))
        and not _NAME_BADGE.match(text)
    ]
    location = None
    if "Contact info" in lines:
        before = lines[: lines.index("Contact info")]
        location = before[-1] if len(before) > 1 else None

    photo = card.select_one('[aria-label="Profile photo"] img')
    photo_url = photo.get("src") if photo else None

    about = None
    for section in main.select("section"):
        if _text(section.select_one("h2")) == "About":
            about = _multiline(section.select_one(_EXPANDABLE))
            break

    return {
        "full_name": _text(name),
        "headline": lines[0] if lines else None,
        "location": location,
        "photo_url": photo_url
        if isinstance(photo_url, str) and photo_url.startswith("http")
        else None,
        "about": about,
    }


def _sdui_contact_info(soup: BeautifulSoup) -> list[ScrapedContact]:
    # The page holds other dialogs too (ad options, ...): take the "Contact info" one.
    # LinkedIn redirects to the plain profile when the viewer may not see contact info.
    dialog = next(
        (
            d
            for d in soup.select("dialog, [data-testid='dialog']")
            if _text(d.select_one("h2")) == "Contact info"
        ),
        None,
    )
    if dialog is None:
        return []
    contacts: list[ScrapedContact] = []
    for label in dialog.select("p"):
        header = (_text(label) or "").lower()
        if len(header) > 30 or label.find("a"):
            continue
        kind = next((k for needle, k in _CONTACT_TYPES if header.startswith(needle)), None)
        if kind is None:
            continue
        for value_node in label.find_next_siblings("p") or [label.find_next("p")]:
            if not isinstance(value_node, Tag):
                continue
            link = value_node.select_one("a[href]")
            href = str(link.get("href", "")) if link else ""
            if href.startswith(("mailto:", "tel:")):
                value = href.split(":", 1)[1]
            elif href.startswith("http"):
                value = _unwrap_link(href)
            else:
                # First text that is not a "(Home)" / "(Personal)" style label.
                value = next((s for s in value_node.stripped_strings if not s.startswith("(")), "")
            if value.strip():
                contacts.append(ScrapedContact(type=kind, value=value.strip()))
    return contacts


_DURATION = re.compile(r"^(?:\d+\s+(?:yrs?|mos?)\s*)+$")


def _sdui_role(node: Tag, company: str | None = None) -> ScrapedExperience | None:
    lines, description = _item_lines(node)
    # An ongoing role repeats a bare "Present" line after its date range.
    lines = [line for i, line in enumerate(lines) if i == 0 or line != "Present"]
    role = _role_from_lines(lines, company=company)
    if role is not None and description:
        role.description = description
    return role


def _sdui_experiences(soup: BeautifulSoup) -> list[ScrapedExperience]:
    experiences: list[ScrapedExperience] = []
    for item in _sdui_items(soup, "profile_ExperienceDetailsSection"):
        roles = [li for li in item.select("ul > li") if li.find_parent("li") is None]
        if roles:
            # Several roles at one company: a header (company, total duration, maybe a
            # shared location) followed by one <li> per role.
            header = [
                text
                for p in item.select("p")
                if p.find_parent("li") is None and p.find_parent("a") and (text := _text(p))
            ]
            company = header[0] if header else None
            shared_location = next((line for line in header[1:] if not _DURATION.match(line)), None)
            for li in roles:
                role = _sdui_role(li, company)
                if role is not None:
                    role.location = role.location or shared_location
                    experiences.append(role)
        else:
            role = _sdui_role(item)
            if role is not None:
                experiences.append(role)
    return experiences


def _sdui_educations(soup: BeautifulSoup) -> list[ScrapedEducation]:
    educations: list[ScrapedEducation] = []
    for item in _sdui_items(soup, "profile_EducationDetailsSection"):
        lines, description = _item_lines(item)
        if not lines:
            continue
        school, rest = lines[0], lines[1:]
        degree = field = None
        start_year = end_year = None
        extra: list[str] = []
        for line in rest:
            if start_year is None and looks_like_date_range(line):
                start_year, end_year = parse_year_range(line)
            elif degree is None and start_year is None:
                parts = [p.strip() for p in line.split(",", 1)]
                degree = parts[0] or None
                field = parts[1] if len(parts) > 1 else None
            else:
                extra.append(line)
        if description:
            extra.append(description)
        educations.append(
            ScrapedEducation(
                school=school,
                degree=degree,
                field_of_study=field,
                start_year=start_year,
                end_year=end_year,
                description="\n".join(extra) or None,
            )
        )
    return educations


_POST_KEY = re.compile(r"^update-card-focus(.+)$")
_UPDATE_LINK = re.compile(r"/feed/update/(urn:li:\w+:(\d+))")
_ID_EPOCH_SHIFT = 22  # LinkedIn ids carry their creation time (ms) above bit 22


def _post_created_ms(soup: BeautifulSoup, post: Tag) -> int | None:
    """Creation time of a post, read from the id LinkedIn encodes next to it.

    Each post has a sibling element whose id is `<token>-replaceableCommentTools<key>`.
    The token is base64 of a tiny protobuf holding one zigzag-encoded id, and LinkedIn
    ids start with a millisecond timestamp."""
    key = _POST_KEY.match(str(post.get("componentkey", "")))
    if not key:
        return None
    marker = "-replaceableCommentTools" + key.group(1)
    holder = soup.find(id=lambda value: bool(value) and marker in value)
    if not isinstance(holder, Tag):
        return None
    token = str(holder["id"]).split(marker, 1)[0].replace("-", "+").replace("_", "/")
    try:
        data = base64.b64decode(token + "=" * (-len(token) % 4))
    except (binascii.Error, ValueError):
        return None
    value = shift = 0
    for byte in data[3:]:  # skip the two field headers and the length byte
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            break
    created_ms = (value >> 1) >> _ID_EPOCH_SHIFT
    # Sanity range (2010..2100) so a format change yields None, not a wrong date.
    return created_ms if 1_262_304_000_000 < created_ms < 4_102_444_800_000 else None


def _post_permalink(post: Tag, created_ms: int | None) -> str | None:
    """The post's own /feed/update/ link, if the markup has one.

    A card can also link to the post it reshares, so a link is only accepted when its
    id was created within ten minutes of the post itself (on the profiles checked, a
    post's own link was 20-90 s away and a reshared post's was days away)."""
    for link in post.select('a[href*="/feed/update/"]'):
        match = _UPDATE_LINK.search(str(link.get("href", "")))
        if not match:
            continue
        link_ms = int(match.group(2)) >> _ID_EPOCH_SHIFT
        if created_ms is not None and abs(link_ms - created_ms) <= 600_000:
            return f"https://www.linkedin.com/feed/update/{match.group(1)}/"
    return None


def _sdui_activities(
    soup: BeautifulSoup, limit: int, now: datetime | None
) -> list[ScrapedActivity]:
    feed = soup.select_one('[data-testid^="ProfileRecentActivityAll"]')
    if feed is None:
        return []
    activities: list[ScrapedActivity] = []
    for post in feed.select('[role="listitem"][componentkey^="update-card"]'):
        header = ""
        age = None
        for p in post.select("p"):
            text = _text(p) or ""
            if p.select_one(_EXPANDABLE):
                break  # header lines come before the post body
            lowered = text.lower()
            if not header and any(w in lowered for w in ("reposted", "commented", "replied")):
                header = lowered
            if age is None and (match := _AGE.search(text)):
                age = match.group(1)
        if "reposted" in header:
            kind = "repost"
        elif "commented" in header or "replied" in header:
            kind = "comment"
        else:
            kind = "post"

        created_ms = _post_created_ms(soup, post)
        posted_at = (
            datetime.fromtimestamp(created_ms / 1000, tz=UTC)
            if created_ms is not None
            else parse_relative_time(age, now)  # "4d" style, approximate
        )

        whole = _text(post) or ""
        reactions = _REACTIONS.search(whole)
        # Comment count: the number on the Comment button, else "N comments" text.
        comment_button = _count(_text(post.select_one('button[aria-label="Comment"]')))
        comments = _COMMENTS.search(whole)
        activities.append(
            ScrapedActivity(
                kind=kind,
                text=_multiline(post.select_one(_EXPANDABLE)),
                url=_post_permalink(post, created_ms),
                posted_at=posted_at,
                reactions_count=_count(reactions.group(1)) if reactions else None,
                comments_count=comment_button
                if comment_button is not None
                else (_count(comments.group(1)) if comments else None),
            )
        )
        if len(activities) >= limit:
            break
    return activities


# --- public API ----------------------------------------------------------------


def _clean_soup(html: str) -> BeautifulSoup:
    soup = _soup(html)
    for node in soup(["script", "style", "svg", "code"]):
        node.decompose()
    return soup


def parse_top_card(html: str) -> dict[str, str | None]:
    soup = _clean_soup(html)
    return _sdui_top_card(soup) or _legacy_top_card(soup)


def parse_contact_info(html: str) -> list[ScrapedContact]:
    soup = _clean_soup(html)
    return _sdui_contact_info(soup) or _legacy_contact_info(soup)


def parse_experiences(html: str) -> list[ScrapedExperience]:
    soup = _clean_soup(html)
    return _sdui_experiences(soup) or _legacy_experiences(soup)


def parse_educations(html: str) -> list[ScrapedEducation]:
    soup = _clean_soup(html)
    return _sdui_educations(soup) or _legacy_educations(soup)


def parse_activities(
    html: str, limit: int = 10, now: datetime | None = None
) -> list[ScrapedActivity]:
    soup = _clean_soup(html)
    return _sdui_activities(soup, limit, now) or _legacy_activities(soup, limit, now)
