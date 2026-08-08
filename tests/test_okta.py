import httpx
import pytest

from snaffle.services.okta import OktaAuthenticator, OktaError

PRIMARY_MFA_REQUIRED = {
    "status": "MFA_REQUIRED",
    "stateToken": "state-123",
    "_embedded": {
        "factors": [
            {
                "id": "sms-factor",
                "factorType": "sms",
                "_links": {"verify": {"href": "https://msu.okta.com/api/v1/authn/factors/sms-factor/verify"}},
            },
            {
                "id": "push-factor",
                "factorType": "push",
                "_links": {"verify": {"href": "https://msu.okta.com/api/v1/authn/factors/push-factor/verify"}},
            },
        ]
    },
}
WAITING = {"status": "MFA_CHALLENGE", "factorResult": "WAITING"}
APPROVED = {"status": "SUCCESS", "sessionToken": "session-abc"}


def _auth(responses):
    it = iter(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        return next(it)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    return OktaAuthenticator("https://msu.okta.com", http=http, poll_interval=0.0)


def test_push_flow_polls_until_approved():
    auth = _auth(
        [
            httpx.Response(200, json=PRIMARY_MFA_REQUIRED),  # primary auth
            httpx.Response(200, json=WAITING),  # first poll: phone not yet tapped
            httpx.Response(200, json=WAITING),  # second poll
            httpx.Response(200, json=APPROVED),  # user approved on device
        ]
    )
    token = auth.authenticate("grace", "secret")
    assert token == "session-abc"


def test_push_rejected_raises():
    auth = _auth(
        [
            httpx.Response(200, json=PRIMARY_MFA_REQUIRED),
            httpx.Response(200, json={"status": "MFA_CHALLENGE", "factorResult": "REJECTED"}),
        ]
    )
    with pytest.raises(OktaError):
        auth.authenticate("grace", "secret")


def test_no_push_factor_raises():
    sms_factor = {"id": "x", "factorType": "sms", "_links": {"verify": {"href": "u"}}}
    no_push = {
        "status": "MFA_REQUIRED",
        "stateToken": "s",
        "_embedded": {"factors": [sms_factor]},
    }
    auth = _auth([httpx.Response(200, json=no_push)])
    with pytest.raises(OktaError):
        auth.authenticate("grace", "secret")


def test_primary_success_without_mfa_returns_token():
    auth = _auth([httpx.Response(200, json={"status": "SUCCESS", "sessionToken": "direct"})])
    assert auth.authenticate("grace", "secret") == "direct"
