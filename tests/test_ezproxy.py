import httpx

from snaffle.models import Credential
from snaffle.secrets import SecretStore
from snaffle.services import ServiceContext
from snaffle.services.ezproxy import EZProxySession

OKTA_MFA = {
    "status": "MFA_REQUIRED",
    "stateToken": "s",
    "_embedded": {
        "factors": [
            {
                "id": "push",
                "factorType": "push",
                "_links": {"verify": {"href": "https://msu.okta.com/api/v1/authn/factors/push/verify"}},
            }
        ]
    },
}
OKTA_OK = {"status": "SUCCESS", "sessionToken": "session-abc"}


def test_push_credential_obtains_token_via_okta():
    responses = iter([httpx.Response(200, json=OKTA_MFA), httpx.Response(200, json=OKTA_OK)])

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(handler)),
        secrets=SecretStore(runner=lambda args: "resolved-password"),
    )
    cred = Credential(
        institution="MSU",
        username="grace",
        password_ref="op://Personal/MSU/password",
        mfa_method="push",
        okta_org="https://msu.okta.com",
    )
    session = EZProxySession(cred, ctx)
    assert session.obtain_session_token() == "session-abc"


def test_totp_credential_returns_generated_code():
    ctx = ServiceContext(
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404))),
        secrets=SecretStore(runner=lambda args: "123456" if "--otp" in args else "pw"),
    )
    cred = Credential(
        institution="BIRKBECK",
        username="ada",
        password_ref="op://Vault/Birkbeck/password",
        otp_ref="op://Vault/Birkbeck",
        mfa_method="totp",
    )
    session = EZProxySession(cred, ctx)
    assert session.current_otp() == "123456"
