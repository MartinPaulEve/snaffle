from snaffle.secrets import SecretStore


def test_is_reference_detects_op_scheme():
    store = SecretStore()
    assert store.is_reference("op://vault/item/field") is True
    assert store.is_reference("literal-password") is False


def test_resolve_returns_literal_unchanged():
    store = SecretStore(runner=lambda args: "SHOULD NOT BE CALLED")
    assert store.resolve("just-a-password") == "just-a-password"


def test_resolve_invokes_op_read_for_reference():
    calls = []

    def runner(args):
        calls.append(args)
        return "s3cr3t\n"

    store = SecretStore(runner=runner)
    assert store.resolve("op://Private/JSTOR/password") == "s3cr3t"
    # The op reference must be passed to `op read`.
    assert any("op://Private/JSTOR/password" in a for a in calls[0])
    assert "read" in calls[0]


def test_totp_uses_op_otp():
    def runner(args):
        assert "--otp" in args
        return "123456\n"

    store = SecretStore(runner=runner)
    assert store.totp("op://Private/MSU") == "123456"
