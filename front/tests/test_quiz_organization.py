from types import SimpleNamespace

from quiz.util.dto import (
    normalize_organization_domain,
    resolve_organization_logo_filename,
    to_test_dto_list,
)


def test_normalize_organization_domain_adds_https_without_scheme():
    assert normalize_organization_domain("spbu.miminet.com") == (
        "https://spbu.miminet.com"
    )


def test_normalize_organization_domain_keeps_existing_scheme():
    assert normalize_organization_domain("https://spbu.miminet.com") == (
        "https://spbu.miminet.com"
    )


def test_resolve_organization_logo_filename_returns_filename_for_existing_file(
    tmp_path, mocker
):
    logo_dir = tmp_path / "logo_organizations"
    logo_dir.mkdir()
    (logo_dir / "spbu.png").write_bytes(b"png")

    mocker.patch("quiz.util.dto.ORGANIZATION_LOGOS_DIR", logo_dir)
    resolve_organization_logo_filename.cache_clear()

    try:
        assert (
            resolve_organization_logo_filename("images/logo_organizations/spbu.png")
            == "spbu.png"
        )
    finally:
        resolve_organization_logo_filename.cache_clear()


def test_resolve_organization_logo_filename_returns_none_for_missing_file(
    tmp_path, mocker
):
    logo_dir = tmp_path / "logo_organizations"
    logo_dir.mkdir()

    mocker.patch("quiz.util.dto.ORGANIZATION_LOGOS_DIR", logo_dir)
    resolve_organization_logo_filename.cache_clear()

    try:
        assert resolve_organization_logo_filename("spbu.png") is None
    finally:
        resolve_organization_logo_filename.cache_clear()


def test_to_test_dto_list_uses_organization_lookup(mocker):
    organization = SimpleNamespace(
        id=3,
        name="spbu",
        logo_uri="spbu.png",
        domain="spbu.miminet.com",
    )
    test = SimpleNamespace(
        id=1,
        organization_id=3,
        name="Demo test",
        created_by_user=SimpleNamespace(nick="author"),
        description="desc",
        is_retakeable=False,
        is_ready=True,
        sections=[],
    )

    mocker.patch(
        "quiz.util.dto.get_organizations_by_id", return_value={3: organization}
    )
    mocker.patch(
        "quiz.util.dto.get_last_correct_question_count_by_section", return_value={}
    )
    mocker.patch(
        "quiz.util.dto.resolve_organization_logo_filename", return_value="spbu.png"
    )

    dto = to_test_dto_list([test])[0]

    assert dto.organization_name == "spbu"
    assert dto.organization_logo_uri == "spbu.png"
    assert dto.organization_domain == "https://spbu.miminet.com"


def test_to_test_dto_list_returns_empty_organization_fields_without_organization(
    mocker,
):
    test = SimpleNamespace(
        id=1,
        organization_id=None,
        name="Demo test",
        created_by_user=SimpleNamespace(nick="author"),
        description="desc",
        is_retakeable=False,
        is_ready=True,
        sections=[],
    )

    get_organizations_by_id_mock = mocker.patch(
        "quiz.util.dto.get_organizations_by_id", return_value={}
    )
    mocker.patch(
        "quiz.util.dto.get_last_correct_question_count_by_section", return_value={}
    )

    dto = to_test_dto_list([test])[0]

    get_organizations_by_id_mock.assert_called_once_with(set())
    assert dto.organization_id is None
    assert dto.organization_name is None
    assert dto.organization_logo_uri is None
    assert dto.organization_domain is None
