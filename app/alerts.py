"""Geração de alertas objetivos a partir dos indicadores."""

from __future__ import annotations

from app.schemas import Alert, Metrics


def generate_alerts(
    metrics: Metrics,
    *,
    stale_pr_days: int = 3,
    low_ci_success_rate: float = 80.0,
    high_issue_volume: int = 10,
    unusual_activity_multiplier: float = 2.0,
    baseline_activity: int | None = None,
) -> list[Alert]:
    alerts: list[Alert] = []

    if metrics.workflow_failure > 0:
        alerts.append(
            Alert(
                type="CI_FAILURE",
                severity="high",
                message=(
                    f"Foram identificadas {metrics.workflow_failure} execuções "
                    "de CI/CD com falha no período."
                ),
            )
        )

    if metrics.workflow_runs > 0 and metrics.workflow_success_rate < low_ci_success_rate:
        alerts.append(
            Alert(
                type="LOW_CI_SUCCESS_RATE",
                severity="high",
                message=(
                    f"Taxa de sucesso de CI/CD em {metrics.workflow_success_rate:.1f}%, "
                    f"abaixo do limiar de {low_ci_success_rate:.0f}%."
                ),
            )
        )

    if metrics.stale_pull_requests > 0:
        alerts.append(
            Alert(
                type="STALE_PR",
                severity="medium",
                message=(
                    f"{metrics.stale_pull_requests} pull request(s) aberto(s) "
                    f"há mais de {stale_pr_days} dias."
                ),
            )
        )

    if metrics.issues_opened >= high_issue_volume:
        alerts.append(
            Alert(
                type="HIGH_ISSUE_VOLUME",
                severity="medium",
                message=(
                    f"Volume elevado de issues abertas no período: "
                    f"{metrics.issues_opened} (limiar {high_issue_volume})."
                ),
            )
        )

    if baseline_activity is not None and baseline_activity > 0:
        current = metrics.commits + metrics.pull_requests_opened + metrics.issues_opened
        threshold = baseline_activity * unusual_activity_multiplier
        if current > threshold:
            alerts.append(
                Alert(
                    type="UNUSUAL_ACTIVITY",
                    severity="low",
                    message=(
                        f"Atividade ({current}) acima do esperado "
                        f"(baseline {baseline_activity}, multiplicador {unusual_activity_multiplier})."
                    ),
                )
            )

    return alerts
