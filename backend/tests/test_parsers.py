from datetime import UTC, date, datetime
from pathlib import Path

from app.providers.linkedin import parsers

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_top_card() -> None:
    top = parsers.parse_top_card(load("profile_main.html"))
    assert top == {
        "full_name": "Asha Verma",
        "headline": "Staff Engineer at Northwind Labs",
        "location": "Pune, Maharashtra, India",
        "photo_url": "https://media.example.com/photo.jpg",
        "about": "I build data platforms. Previously search infrastructure.",
    }


def test_top_card_on_empty_page_returns_nones() -> None:
    assert set(parsers.parse_top_card("<html><body></body></html>").values()) == {None}


def test_contact_info() -> None:
    contacts = {(c.type, c.value) for c in parsers.parse_contact_info(load("contact_info.html"))}
    assert contacts == {
        ("website", "https://asha.example.dev"),
        ("website", "https://blog.example.dev"),
        ("phone", "+91 98000 00000"),
        ("email", "asha@example.com"),
        ("birthday", "March 4"),
    }


def test_experiences_single_and_grouped_roles() -> None:
    roles = parsers.parse_experiences(load("experience.html"))
    assert [(r.title, r.company) for r in roles] == [
        ("Staff Engineer", "Northwind Labs"),
        ("Senior Software Engineer", "Acme Robotics"),
        ("Software Engineer", "Acme Robotics"),
    ]
    current = roles[0]
    assert current.employment_type == "Full-time"
    assert (current.start_date, current.end_date, current.is_current) == (
        date(2022, 1, 1), None, True,
    )  # fmt: skip
    assert current.location == "Pune, Maharashtra, India · Hybrid"
    assert current.description and current.description.startswith("Leading the ingestion")

    assert (roles[1].start_date, roles[1].end_date) == (date(2019, 7, 1), date(2021, 12, 1))
    assert roles[2].description == "Worked on the fleet scheduling service."
    assert roles[2].location is None


def test_educations() -> None:
    first, second = parsers.parse_educations(load("education.html"))
    assert first.school == "Example Institute of Technology"
    assert first.degree == "Bachelor of Technology - BTech"
    assert first.field_of_study == "Computer Science"
    assert (first.start_year, first.end_year) == (2012, 2016)
    assert first.description == "Activities and societies: Robotics club"
    assert (second.school, second.degree, second.start_year) == ("Demo Public School", None, 2010)


def test_activities() -> None:
    now = datetime(2026, 11, 15, tzinfo=UTC)
    posts = parsers.parse_activities(load("activity.html"), limit=2, now=now)
    assert len(posts) == 2  # limit respected

    first, second = posts
    assert first.kind == "post"
    assert first.text == "We just open-sourced our queue library!"
    assert first.url == "https://www.linkedin.com/feed/update/urn:li:activity:7000000000000000001/"
    assert (first.reactions_count, first.comments_count) == (1234, 56)
    assert first.posted_at == datetime(2026, 11, 1, tzinfo=UTC)

    assert second.kind == "repost"
    assert (second.reactions_count, second.comments_count) == (2500, None)


# --- current LinkedIn markup (hashed classes; data-testid / componentkey hooks) ---


def test_sdui_top_card() -> None:
    top = parsers.parse_top_card(load("sdui_profile.html"))
    assert top == {
        "full_name": "Sam Lee",
        "headline": "Staff Engineer at Initech",
        "location": "Pune, Maharashtra, India",
        "photo_url": "https://media.example.com/photo.jpg",
        "about": "Builds payment systems.\n\nLikes small teams.",
    }


def test_sdui_contact_info() -> None:
    contacts = [(c.type, c.value) for c in parsers.parse_contact_info(load("sdui_contact.html"))]
    assert contacts == [
        ("website", "https://sam.example.dev/about"),
        ("phone", "+91 55501 00123"),
        ("email", "sam@example.com"),
        ("birthday", "March 4"),
    ]


def test_sdui_experiences() -> None:
    first, second, *_ = parsers.parse_experiences(load("sdui_experience.html"))
    assert (first.title, first.company, first.employment_type) == (
        "Staff Engineer", "Initech", "Full-time",
    )  # fmt: skip
    assert first.start_date == date(2022, 3, 1)
    assert first.end_date is None and first.is_current
    assert first.location == "Pune, Maharashtra, India · Hybrid"
    assert first.description == "Led the payments team.\n\nCut costs by 20%."
    assert (second.title, second.company, second.description) == ("Engineer", "Globex", None)
    assert second.end_date == date(2022, 2, 1)


def test_sdui_educations() -> None:
    (edu,) = parsers.parse_educations(load("sdui_education.html"))
    assert (edu.school, edu.degree, edu.field_of_study) == (
        "State University", "Bachelor of Engineering - BE", "Computer Science",
    )  # fmt: skip
    assert (edu.start_year, edu.end_year) == (2014, 2018)
    assert edu.description == "Grade: 8.1\nRobotics club."


def test_sdui_activities() -> None:
    now = datetime(2026, 11, 15, tzinfo=UTC)
    repost, post = parsers.parse_activities(load("sdui_activity.html"), now=now)
    assert repost.kind == "repost"
    assert repost.text == "We are hiring.\nApply now."
    assert repost.posted_at == datetime(2026, 11, 11, tzinfo=UTC)
    assert (repost.reactions_count, repost.comments_count) == (1204, 12)
    assert (post.kind, post.text, post.reactions_count) == ("post", "Shipped a thing.", None)
    # Exact time and permalink come from the id encoded next to the post; the link to
    # the reshared original (created days earlier) is not taken for the post's own.
    assert repost.url == "https://www.linkedin.com/feed/update/urn:li:activity:7526071318609920001/"
    assert post.url is None and post.posted_at == datetime(2026, 11, 1, tzinfo=UTC)


def test_sdui_grouped_roles_share_company_and_location() -> None:
    *_, director, manager = parsers.parse_experiences(load("sdui_experience.html"))
    assert (director.title, director.company, director.location) == (
        "Director", "Umbrella Corp", "Remote",
    )  # fmt: skip
    assert (director.start_date, director.end_date) == (date(2016, 6, 1), date(2018, 12, 1))
    assert director.description == "Ran the platform group."
    assert (manager.title, manager.company, manager.location) == (
        "Manager", "Umbrella Corp", "Berlin, Germany",
    )  # fmt: skip


def test_sdui_contact_info_ignores_other_dialogs() -> None:
    html = (
        "<dialog><header><h2>Ad Options</h2></header><div data-testid='dialog-content'>"
        "<div data-testid='lazy-column'><p>Email</p><p>ads@example.com</p></div></div></dialog>"
    )
    assert parsers.parse_contact_info(html) == []
