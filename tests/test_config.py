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
