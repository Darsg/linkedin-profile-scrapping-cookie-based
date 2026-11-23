import re
from dataclasses import dataclass
from urllib.parse import quote, unquote, urlsplit


class InvalidProfileUrl(ValueError):
    pass


@dataclass(frozen=True)
class ProfileRef:
    public_id: str  # the slug after /in/, lower-cased and percent-decoded
    url: str  # canonical https://www.linkedin.com/in/<slug>/


_HOST = re.compile(r"^([a-z]{2,3}\.)?linkedin\.com$")
_SLUG = re.compile(r"^[\w\-.%]{2,200}$", re.UNICODE)


def parse_profile_url(raw: str) -> ProfileRef:
    """Validate a LinkedIn *personal profile* URL and reduce it to its canonical form.

    Accepts missing scheme, country sub-domains, trailing paths and query strings.
    Rejects anything that is not linkedin.com/in/<slug>.
    """
    value = raw.strip()
    if not value:
        raise InvalidProfileUrl("URL is empty")
    if "://" not in value:
        value = "https://" + value

    parts = urlsplit(value)
    if parts.scheme not in ("http", "https"):
        raise InvalidProfileUrl("URL must start with http:// or https://")
    host = (parts.hostname or "").lower()
    if not _HOST.match(host):
        raise InvalidProfileUrl("Not a linkedin.com URL")

    segments = [s for s in parts.path.split("/") if s]
    if len(segments) < 2 or segments[0].lower() != "in":
        raise InvalidProfileUrl("Expected a profile URL like https://www.linkedin.com/in/<name>")

    slug = unquote(segments[1]).strip().lower()
    if not _SLUG.match(slug):
        raise InvalidProfileUrl("Profile name in the URL looks invalid")

    return ProfileRef(public_id=slug, url=f"https://www.linkedin.com/in/{quote(slug)}/")
