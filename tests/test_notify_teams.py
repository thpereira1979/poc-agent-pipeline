"""Testes unitários para o notificador do Teams (agent/notify_teams.py)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from agent import notify_teams


# --------------------------------------------------------------------------- #
# carregar_analise
# --------------------------------------------------------------------------- #
class TestCarregarAnalise:
    def test_arquivo_inexistente_retorna_mensagem_padrao(self, tmp_path):
        caminho = str(tmp_path / "nao_existe.txt")
        assert (
            notify_teams.carregar_analise(caminho)
            == "Análise não disponível - arquivo não encontrado."
        )

    def test_arquivo_existente_retorna_conteudo_sem_espacos(self, tmp_path):
        arquivo = tmp_path / "analise.txt"
        arquivo.write_text("  minha analise  \n", encoding="utf-8")
        assert notify_teams.carregar_analise(str(arquivo)) == "minha analise"


# --------------------------------------------------------------------------- #
# enviar_teams
# --------------------------------------------------------------------------- #
class TestEnviarTeams:
    def test_sem_webhook_retorna_false(self):
        assert notify_teams.enviar_teams("msg", "") is False

    @pytest.mark.parametrize("status", [200, 202])
    def test_envio_com_sucesso(self, status):
        resposta = MagicMock()
        resposta.status_code = status
        with patch.object(
            notify_teams.requests, "post", return_value=resposta
        ) as mock_post:
            assert notify_teams.enviar_teams("msg", "http://webhook") is True
        mock_post.assert_called_once()

    def test_envio_falha_status(self):
        resposta = MagicMock()
        resposta.status_code = 500
        resposta.text = "erro"
        with patch.object(notify_teams.requests, "post", return_value=resposta):
            assert notify_teams.enviar_teams("msg", "http://webhook") is False

    def test_envio_erro_conexao(self):
        with patch.object(
            notify_teams.requests,
            "post",
            side_effect=requests.RequestException("boom"),
        ):
            assert notify_teams.enviar_teams("msg", "http://webhook") is False

    def test_payload_contem_dados_do_ambiente(self, monkeypatch):
        monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
        monkeypatch.setenv("GITHUB_REF_NAME", "feature/x")
        monkeypatch.setenv("GITHUB_SHA", "0123456789abcdef")
        monkeypatch.setenv("GITHUB_RUN_ID", "42")

        resposta = MagicMock()
        resposta.status_code = 200
        with patch.object(
            notify_teams.requests, "post", return_value=resposta
        ) as mock_post:
            notify_teams.enviar_teams("texto analise", "http://webhook")

        _, kwargs = mock_post.call_args
        card = kwargs["json"]["attachments"][0]["content"]
        facts = {f["title"]: f["value"] for f in card["body"][1]["facts"]}
        assert facts["Repositório"] == "org/repo"
        assert facts["Branch"] == "feature/x"
        assert facts["Commit"] == "01234567"
        assert card["actions"][0]["url"].endswith("org/repo/actions/runs/42")
        assert card["body"][-1]["text"] == "texto analise"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
class TestMain:
    def test_fluxo_com_sucesso(self, monkeypatch):
        monkeypatch.setenv("TEAMS_WEBHOOK_URL", "http://webhook")
        monkeypatch.setattr(
            notify_teams, "carregar_analise", lambda: "analise"
        )
        enviar = MagicMock(return_value=True)
        monkeypatch.setattr(notify_teams, "enviar_teams", enviar)

        notify_teams.main()

        enviar.assert_called_once_with("analise", "http://webhook")

    def test_fluxo_com_falha_nao_lanca_excecao(self, monkeypatch):
        monkeypatch.setenv("TEAMS_WEBHOOK_URL", "")
        monkeypatch.setattr(
            notify_teams, "carregar_analise", lambda: "analise"
        )
        monkeypatch.setattr(
            notify_teams, "enviar_teams", MagicMock(return_value=False)
        )

        # Não deve lançar exceção mesmo quando o envio falha.
        notify_teams.main()
