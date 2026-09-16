"""Cliente da API pública do GitHub com timeout, retry e rate-limit."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import Settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class GitHubAPIError(Exception):
    """Erro controlado na integração com a API do GitHub."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_url = settings.github_api_base.rstrip("/")
        self.repo = settings.repo_full_name
        self.timeout = settings.request_timeout_seconds

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "devops-pulse-ai",
        }
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url,
            headers=self._headers(),
            timeout=self.timeout,
            follow_redirects=True,
        )

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self.repo:
            raise GitHubAPIError("GITHUB_OWNER e GITHUB_REPOSITORY não configurados.")
        with self._client() as client:
            response = client.get(path, params=params)
            if response.status_code == 403 and "rate limit" in response.text.lower():
                raise GitHubAPIError(
                    "Rate limit da API do GitHub atingido. Aguarde o reset ou configure GITHUB_TOKEN.",
                    status_code=403,
                )
            if response.status_code == 404:
                raise GitHubAPIError(
                    f"Repositório não encontrado: {self.repo}",
                    status_code=404,
                )
            if response.status_code >= 400:
                raise GitHubAPIError(
                    f"Erro na API do GitHub ({response.status_code}): {response.text[:200]}",
                    status_code=response.status_code,
                )
            return response.json()

    def fetch_raw(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
        max_items: int = 100,
    ) -> dict[str, Any]:
        """Coleta dados brutos normalizados da API."""
        if not self.repo or "/" not in self.repo:
            raise GitHubAPIError("GITHUB_OWNER e GITHUB_REPOSITORY não configurados.")
        since = window_start.isoformat()
        owner, name = self.repo.split("/", 1)

        commits = self._get(
            f"/repos/{owner}/{name}/commits",
            params={"since": since, "per_page": max_items},
        )
        issues = self._get(
            f"/repos/{owner}/{name}/issues",
            params={"state": "all", "since": since, "per_page": max_items},
        )
        pulls = self._get(
            f"/repos/{owner}/{name}/pulls",
            params={"state": "all", "sort": "updated", "direction": "desc", "per_page": max_items},
        )
        try:
            runs_payload = self._get(
                f"/repos/{owner}/{name}/actions/runs",
                params={"per_page": max_items},
            )
            runs = runs_payload.get("workflow_runs", []) if isinstance(runs_payload, dict) else []
        except GitHubAPIError as exc:
            logger.warning("workflow_runs indisponível: %s", exc)
            runs = []

        # Issues da API incluem PRs; separar apenas issues reais.
        pure_issues = [i for i in issues if "pull_request" not in i]

        normalized_commits = [
            {
                "sha": c.get("sha"),
                "date": (c.get("commit") or {}).get("author", {}).get("date"),
                "message": ((c.get("commit") or {}).get("message") or "").split("\n")[0][:120],
            }
            for c in commits
            if isinstance(c, dict)
        ]
        normalized_issues = [
            {
                "number": i.get("number"),
                "title": (i.get("title") or "")[:120],
                "state": i.get("state"),
                "created_at": i.get("created_at"),
                "closed_at": i.get("closed_at"),
            }
            for i in pure_issues
            if isinstance(i, dict)
        ]
        normalized_pulls = [
            {
                "number": p.get("number"),
                "title": (p.get("title") or "")[:120],
                "state": p.get("state"),
                "created_at": p.get("created_at"),
                "closed_at": p.get("closed_at"),
                "merged_at": p.get("merged_at"),
            }
            for p in pulls
            if isinstance(p, dict)
        ]
        normalized_runs = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "created_at": r.get("created_at") or r.get("run_started_at"),
            }
            for r in runs
            if isinstance(r, dict)
        ]

        return {
            "commits": normalized_commits,
            "issues": normalized_issues,
            "pull_requests": normalized_pulls,
            "workflow_runs": normalized_runs,
            "window_end_hint": window_end.isoformat(),
        }
