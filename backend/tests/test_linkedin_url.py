import pytest

from app.utils.linkedin_url import InvalidProfileUrl, parse_profile_url


@pytest.mark.parametrize(
    "raw",
    [
        "https://www.linkedin.com/in/jane-doe-123/",
        "linkedin.com/in/Jane-Doe-123",
        "http://in.linkedin.com/in/jane-doe-123/details/experience/?utm=x#top",
        "  https://linkedin.com/in/JANE-DOE-123?trk=abc  ",
    ],
)
def test_normalizes_to_one_canonical_form(raw: str) -> None:
    ref = parse_profile_url(raw)
    assert ref.public_id == "jane-doe-123"
    assert ref.url == "https://www.linkedin.com/in/jane-doe-123/"


def test_percent_encoded_slug_round_trips() -> None:
    ref = parse_profile_url("https://www.linkedin.com/in/jos%C3%A9-garc%C3%ADa/")
    assert ref.public_id == "josé-garcía"
    assert ref.url == "https://www.linkedin.com/in/jos%C3%A9-garc%C3%ADa/"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "https://example.com/in/jane",
        "https://linkedin.com.evil.io/in/jane",
        "https://www.linkedin.com/company/acme/",
        "https://www.linkedin.com/in/",
        "ftp://www.linkedin.com/in/jane",
        "https://www.linkedin.com/in/a b<script>",
    ],
)
def test_rejects_non_profile_urls(raw: str) -> None:
    with pytest.raises(InvalidProfileUrl):
        parse_profile_url(raw)
