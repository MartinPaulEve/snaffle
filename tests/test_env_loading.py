from snaffle.config import load_env_file


def test_loads_simple_and_tricky_values(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "# a comment",
                "SNAFFLE_KAGI_KEY=op://Personal/Kagi API Key/password",
                'SNAFFLE_OPENALEX_EXCLUDES={"Martin Paul Eve": ["W568507393"]}',
                "SNAFFLE_CRED_MSU_MFA=push   # inline comment",
                "",
            ]
        ),
        encoding="utf-8",
    )
    env = load_env_file(env_file)
    assert env["SNAFFLE_KAGI_KEY"] == "op://Personal/Kagi API Key/password"
    assert env["SNAFFLE_OPENALEX_EXCLUDES"] == '{"Martin Paul Eve": ["W568507393"]}'
    assert env["SNAFFLE_CRED_MSU_MFA"] == "push"


def test_missing_file_returns_empty(tmp_path):
    assert load_env_file(tmp_path / "nope.env") == {}
