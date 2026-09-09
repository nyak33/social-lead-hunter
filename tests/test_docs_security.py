from pathlib import Path


def test_public_docs_do_not_contain_real_secret_patterns():
    text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in [Path("README.md"), Path("SKILL.md"), Path("config.example.yaml"), Path(".env.example")]
    )
    forbidden = ["Bearer ey", "service_role", "sk-proj-", "ghp_", "xoxb-"]
    assert not any(token in text for token in forbidden)


def test_skill_is_safe_by_default():
    text = Path("skills/social-lead-hunter/SKILL.md").read_text(encoding="utf-8")
    assert "dry-run" in text.lower()
    assert "explicit" in text.lower()
    assert "THREADS_ACCESS_TOKEN=" not in text
