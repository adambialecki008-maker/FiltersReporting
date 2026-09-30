import pytest

from asyncua import ua
from asyncua.crypto.permission_rules import (
    UserRole,
)

from filters_reporting.opcua.auth import (
    FiltersReportingUserManager,
    OpcUaAuthenticationConfig,
    build_identity_tokens,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plain_password():
    password = "SuperSecret123!"

    result = hash_password(password)

    assert password not in result

    assert result.startswith("pbkdf2_sha256$")


def test_hash_password_uses_random_salt():
    password = "SuperSecret123!"

    first = hash_password(password)

    second = hash_password(password)

    assert first != second


def test_verify_password_accepts_correct_password():
    password = "SuperSecret123!"

    encoded = hash_password(password)

    assert (
        verify_password(
            password,
            encoded,
        )
        is True
    )


def test_verify_password_rejects_wrong_password():
    encoded = hash_password("CorrectPassword123!")

    assert (
        verify_password(
            "WrongPassword",
            encoded,
        )
        is False
    )


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "",
        "abc",
        "sha256$123$abc$xyz",
        "pbkdf2_sha256$abc$abc$xyz",
        "pbkdf2_sha256$0$abc$xyz",
    ],
)
def test_verify_password_rejects_invalid_hash(
    invalid_hash,
):
    assert (
        verify_password(
            "password",
            invalid_hash,
        )
        is False
    )


def test_hash_password_rejects_empty_password():
    with pytest.raises(ValueError):
        hash_password("")


def test_auth_config_allows_anonymous_only():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=True,
    )

    config.validate()

    assert config.username_enabled is False


def test_auth_config_allows_username_password_only():
    password_hash = hash_password("Password123!")

    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash=(password_hash),
    )

    config.validate()

    assert config.username_enabled is True


def test_auth_config_rejects_no_authentication_methods():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="",
        password_hash="",
    )

    with pytest.raises(ValueError):
        config.validate()


def test_auth_config_rejects_username_without_password():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash="",
    )

    with pytest.raises(ValueError):
        config.validate()


def test_auth_config_rejects_password_without_username():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=True,
        username="",
        password_hash=(hash_password("Password123!")),
    )

    with pytest.raises(ValueError):
        config.validate()


def test_build_identity_tokens_anonymous_only():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=True,
    )

    result = build_identity_tokens(config)

    assert result == [ua.AnonymousIdentityToken]


def test_build_identity_tokens_username_only():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash=(hash_password("Password123!")),
    )

    result = build_identity_tokens(config)

    assert result == [ua.UserNameIdentityToken]


def test_build_identity_tokens_supports_anonymous_and_username():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=True,
        username="operator",
        password_hash=(hash_password("Password123!")),
    )

    result = build_identity_tokens(config)

    assert result == [
        ua.AnonymousIdentityToken,
        ua.UserNameIdentityToken,
    ]


def test_user_manager_accepts_anonymous_when_enabled():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=True,
    )

    manager = FiltersReportingUserManager(config)

    user = manager.get_user(
        None,
        username=None,
        password=None,
    )

    assert user is not None

    assert user.role == UserRole.Anonymous


def test_user_manager_rejects_anonymous_when_disabled():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash=(hash_password("Password123!")),
    )

    manager = FiltersReportingUserManager(config)

    result = manager.get_user(
        None,
        username=None,
        password=None,
    )

    assert result is None


def test_user_manager_accepts_correct_username_and_password():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash=(hash_password("Password123!")),
    )

    manager = FiltersReportingUserManager(config)

    user = manager.get_user(
        None,
        username="operator",
        password="Password123!",
    )

    assert user is not None

    assert user.role == UserRole.User

    assert user.name == "operator"


def test_user_manager_rejects_wrong_username():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash=(hash_password("Password123!")),
    )

    manager = FiltersReportingUserManager(config)

    result = manager.get_user(
        None,
        username="wrong",
        password="Password123!",
    )

    assert result is None


def test_user_manager_rejects_wrong_password():
    config = OpcUaAuthenticationConfig(
        allow_anonymous=False,
        username="operator",
        password_hash=(hash_password("Password123!")),
    )

    manager = FiltersReportingUserManager(config)

    result = manager.get_user(
        None,
        username="operator",
        password="WrongPassword",
    )

    assert result is None
