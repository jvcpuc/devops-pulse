"""TTS: SSML com pronúncia inglesa (IPA) para termos de TI.

A voz pt-BR fonemiza tudo em português ("pull requests" saía como
"pɔl ɔkʷists"); o glossário envolve esses termos em <phoneme alphabet="ipa">
para a Kokoro pronunciá-los em inglês correto.
"""

from app.tts_client import _ssml_speech


def test_ssml_wraps_english_terms_with_ipa():
    ssml = _ssml_speech("O pipeline teve 3 pull requests mergeados no GitHub.")
    assert '<phoneme alphabet="ipa" ph="ˈpaɪpaɪl">pipeline</phoneme>' in ssml
    assert '<phoneme alphabet="ipa" ph="pʊl">pull</phoneme>' in ssml
    assert '<phoneme alphabet="ipa" ph="rɪˈkwests">requests</phoneme>' in ssml
    assert '<phoneme alphabet="ipa" ph="ˈɡɪthʌb">GitHub</phoneme>' in ssml
    # palavra em português permanece sem marcação
    assert " teve " in ssml


def test_ssml_preserva_case_e_escapa_xml():
    ssml = _ssml_speech("GitHub & CI no DevOps")
    assert ">GitHub</phoneme>" in ssml
    assert ">CI</phoneme>" in ssml
    assert "&amp;" in ssml


def test_ssml_nao_casa_substrings_de_palavras_pt():
    # "ci" aparece dentro de "raciocínio", mas não como palavra isolada
    ssml = _ssml_speech("raciocínio")
    assert "<phoneme" not in ssml


def test_ssml_plural_diferente_do_singular():
    ssml = _ssml_speech("commits e workflows")
    assert '<phoneme alphabet="ipa" ph="kəˈmɪts">commits</phoneme>' in ssml
    assert '<phoneme alphabet="ipa" ph="ˈwɝkfloʊz">workflows</phoneme>' in ssml
