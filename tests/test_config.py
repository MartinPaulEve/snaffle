from snaffle.config import parse_credentials


def test_parse_single_credential():
    env = {
        "SNAFFLE_CRED_BIRKBECK_USER": "ada",
        "SNAFFLE_CRED_BIRKBECK_PASS": "op://Vault/Birkbeck/password",
        "SNAFFLE_CRED_BIRKBECK_OTP": "op://Vault/Birkbeck",
        "SNAFFLE_CRED_BIRKBECK_EZPROXY": "https://ezproxy.bbk.ac.uk",
    }
    creds = parse_credentials(env)
    assert len(creds) == 1
    c = creds[0]
    assert c.institution == "BIRKBECK"
    assert c.username == "ada"
    assert c.password_ref == "op://Vault/Birkbeck/password"
    assert c.otp_ref == "op://Vault/Birkbeck"
    assert c.ezproxy_base == "https://ezproxy.bbk.ac.uk"


def test_parse_multiple_credentials():
    env = {
        "SNAFFLE_CRED_BIRKBECK_USER": "ada",
        "SNAFFLE_CRED_BIRKBECK_PASS": "p1",
        "SNAFFLE_CRED_MSU_USER": "grace",
        "SNAFFLE_CRED_MSU_PASS": "p2",
    }
    creds = parse_credentials(env)
    institutions = {c.institution for c in creds}
    assert institutions == {"BIRKBECK", "MSU"}


def test_parse_ignores_unrelated_env():
    env = {"PATH": "/usr/bin", "HOME": "/home/ada"}
    assert parse_credentials(env) == []


def test_credential_defaults_to_totp_mfa():
    env = {"SNAFFLE_CRED_BIRKBECK_USER": "ada", "SNAFFLE_CRED_BIRKBECK_PASS": "p"}
    (c,) = parse_credentials(env)
    assert c.mfa_method == "totp"
    assert c.okta_org is None


def test_parse_okta_push_credential():
    env = {
        "SNAFFLE_CRED_MSU_USER": "grace",
        "SNAFFLE_CRED_MSU_PASS": "op://Personal/MSU/password",
        "SNAFFLE_CRED_MSU_MFA": "push",
        "SNAFFLE_CRED_MSU_OKTA": "https://msu.okta.com",
    }
    (c,) = parse_credentials(env)
    assert c.institution == "MSU"
    assert c.mfa_method == "push"
    assert c.okta_org == "https://msu.okta.com"
