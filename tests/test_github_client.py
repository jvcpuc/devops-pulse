"""Testes do cliente GitHub (sem rede — valida normalização e erros)."""

from datetime import datetime, timezone

import pytest

from app.config import Settings
from app.github_client import GitHubAPIError, GitHubClient


def test_headers_include_token():
    s = Settings(github_owner="octocat", github_repository="hello-world", github_token="tok123")
    c = GitHubClient(s)
    headers = c._headers()
    assert headers["Authorization"] == "Bearer tok123"
    assert "application/vnd.github+json" in headers["Accept"]


def test_headers_without_token():
    s = Settings(github_owner="octocat", github_repository="hello-world", github_token="")
    headers = GitHubClient(s)._headers()
    assert "Authorization" not in headers


def test_missing_repo_raises():
    s = Settings(github_owner="", github_repository="", demo_mode=False)
    c = GitHubClient(s)
    with pytest.raises(GitHubAPIError, match="não configurados"):
        c._get("/repos/x/y/commits")


def test_repo_full_name():
    s = Settings(github_owner="owner", github_repository="repo")
    assert s.repo_full_name == "owner/repo"


def test_fetch_raw_requires_repo():
    s = Settings(github_owner="", github_repository="", demo_mode=False)
    c = GitHubClient(s)
    now = datetime.now(timezone.utc)
    with pytest.raises(GitHubAPIError):
        c.fetch_raw(window_start=now, window_end=now)
