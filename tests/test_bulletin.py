"""Versão falada do boletim — fonética de termos ingleses por motor."""

from app.bulletin import _speak_en, format_bulletin, format_spoken_bulletin


def _base(**kw):
    data = dict(
        execution_id="PULSE-X",
        repository="n8n-io/n8n",
        data_source="github",
        status="success",
        metrics={
            "commits": 12,
            "pull_requests_opened": 3,
            "pull_requests_closed": 1,
            "open_issues": 5,
            "workflow_success_rate": 92.0,
        },
        alerts=[],
    )
    data.update(kw)
    return data


_CI_ALERT = {
    "severity": "high",
    "message": "Foram identificadas 3 execuções de CI/CD com falha no período.",
}


def test_edge_phonetics_siglas_e_termos():
    text = format_spoken_bulletin(**_base(engine="edge", alerts=[_CI_ALERT]))
    assert "si ai, si di" in text  # CI/CD do alerta
    assert "ei ai" in text  # "DevOps Pulse AI" → AI
    assert "devóps" in text  # "DevOps Pulse" → devóps
    assert "guit rubi" in text  # fonte github
    assert "ene eigth ene ponto ai ou barra ene eigth ene" in text  # n8n-io/n8n
    assert "CI/CD" not in text
    assert "GitHub" not in text
    assert "DevOps" not in text


def test_kokoro_mantem_fonetica_propria():
    text = format_spoken_bulletin(**_base(engine="kokoro", alerts=[_CI_ALERT]))
    assert "integração contínua" in text
    assert "Guit-Hub" in text
    assert "guit rubi" not in text
    assert "si ai" not in text


def test_speak_en_idempotente():
    s = "Fonte GitHub. CI/CD, CI, AI, API, DevOps devops e IO."
    once = _speak_en(s)
    assert _speak_en(once) == once
    assert once.count("si ai") == 2
    assert "ei ai" in once
    assert "guit rubi" in once
    assert "ei pi ai" in once
    assert "devóps" in once
    assert "ai ou" in once
    assert "DevOps" not in once and "GitHub" not in once


def test_texto_escrito_nao_fonetizado():
    txt = format_bulletin(**_base())
    assert "GitHub" in txt  # WhatsApp mantém grafia normal
    assert "guit rubi" not in txt
