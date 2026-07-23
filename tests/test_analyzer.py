"""Testes unitários para o agente de análise (agent/analyzer.py)."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from agent import analyzer


# --------------------------------------------------------------------------- #
# carregar_log_erro
# --------------------------------------------------------------------------- #
class TestCarregarLogErro:
    def test_arquivo_inexistente_retorna_vazio(self, tmp_path):
        caminho = str(tmp_path / "nao_existe.log")
        assert analyzer.carregar_log_erro(caminho) == ""

    def test_arquivo_existente_retorna_conteudo(self, tmp_path):
        arquivo = tmp_path / "erro.log"
        arquivo.write_text("FAILED test_x", encoding="utf-8")
        assert analyzer.carregar_log_erro(str(arquivo)) == "FAILED test_x"


# --------------------------------------------------------------------------- #
# analisar_com_llm
# --------------------------------------------------------------------------- #
class TestAnalisarComLlm:
    def test_sem_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        resultado = analyzer.analisar_com_llm("log")
        assert resultado == "ERRO: GEMINI_API_KEY não configurada."

    def test_sucesso_primeiro_modelo(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "Análise gerada."}]}}
            ]
        }
        with patch.object(
            analyzer.requests, "post", return_value=resposta
        ) as mock_post:
            resultado = analyzer.analisar_com_llm("log de erro")

        assert resultado == "Análise gerada."
        assert mock_post.call_count == 1

    def test_fallback_para_proximo_modelo(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        falha = MagicMock()
        falha.status_code = 404
        falha.json.return_value = {"error": {"message": "not found"}}

        sucesso = MagicMock()
        sucesso.status_code = 200
        sucesso.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}]
        }

        with patch.object(
            analyzer.requests, "post", side_effect=[falha, sucesso]
        ) as mock_post:
            resultado = analyzer.analisar_com_llm("log")

        assert resultado == "ok"
        assert mock_post.call_count == 2

    def test_todos_modelos_falham(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        falha = MagicMock()
        falha.status_code = 500
        falha.json.return_value = {"error": {"message": "server error"}}

        with patch.object(analyzer.requests, "post", return_value=falha):
            resultado = analyzer.analisar_com_llm("log")

        assert resultado == (
            "ERRO: Nenhum modelo Gemini disponível respondeu com sucesso."
        )

    def test_erro_de_conexao(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        with patch.object(
            analyzer.requests,
            "post",
            side_effect=requests.RequestException("timeout"),
        ):
            resultado = analyzer.analisar_com_llm("log")

        assert resultado == (
            "ERRO: Nenhum modelo Gemini disponível respondeu com sucesso."
        )

    def test_resposta_malformada(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        resposta = MagicMock()
        resposta.status_code = 200
        resposta.json.return_value = {"candidates": []}  # IndexError

        with patch.object(analyzer.requests, "post", return_value=resposta):
            resultado = analyzer.analisar_com_llm("log")

        assert resultado == (
            "ERRO: Nenhum modelo Gemini disponível respondeu com sucesso."
        )


# --------------------------------------------------------------------------- #
# enviar_teams
# --------------------------------------------------------------------------- #
class TestEnviarTeams:
    def test_sem_webhook_retorna_false(self):
        assert analyzer.enviar_teams("msg", "") is False

    @pytest.mark.parametrize("status", [200, 202])
    def test_envio_com_sucesso(self, status):
        resposta = MagicMock()
        resposta.status_code = status
        with patch.object(
            analyzer.requests, "post", return_value=resposta
        ) as mock_post:
            assert analyzer.enviar_teams("msg", "http://webhook") is True
        mock_post.assert_called_once()

    def test_envio_falha_status(self):
        resposta = MagicMock()
        resposta.status_code = 400
        resposta.text = "bad request"
        with patch.object(analyzer.requests, "post", return_value=resposta):
            assert analyzer.enviar_teams("msg", "http://webhook") is False

    def test_envio_erro_conexao(self):
        with patch.object(
            analyzer.requests,
            "post",
            side_effect=requests.RequestException("boom"),
        ):
            assert analyzer.enviar_teams("msg", "http://webhook") is False

    def test_payload_contem_dados_do_ambiente(self, monkeypatch):
        monkeypatch.setenv("GITHUB_REPOSITORY", "org/repo")
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        monkeypatch.setenv("GITHUB_SHA", "abcdef1234567890")
        monkeypatch.setenv("GITHUB_RUN_ID", "999")

        resposta = MagicMock()
        resposta.status_code = 200
        with patch.object(
            analyzer.requests, "post", return_value=resposta
        ) as mock_post:
            analyzer.enviar_teams("minha analise", "http://webhook")

        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        card = payload["attachments"][0]["content"]
        facts = {f["title"]: f["value"] for f in card["body"][1]["facts"]}
        assert facts["Repositório"] == "org/repo"
        assert facts["Branch"] == "main"
        assert facts["Commit"] == "abcdef12"
        assert card["actions"][0]["url"].endswith("org/repo/actions/runs/999")
        assert card["body"][-1]["text"] == "minha analise"


# --------------------------------------------------------------------------- #
# salvar_analise
# --------------------------------------------------------------------------- #
class TestSalvarAnalise:
    def test_salva_conteudo_no_arquivo(self, tmp_path):
        destino = tmp_path / "analise.txt"
        analyzer.salvar_analise("conteudo da analise", str(destino))
        assert destino.read_text(encoding="utf-8") == "conteudo da analise"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
class TestMain:
    def test_sem_log_encerra_com_zero(self, monkeypatch):
        monkeypatch.setattr(analyzer, "carregar_log_erro", lambda _: "")
        with pytest.raises(SystemExit) as exc:
            analyzer.main()
        assert exc.value.code == 0

    def test_fluxo_completo(self, monkeypatch):
        monkeypatch.setenv("TEST_LOG_PATH", "qualquer.log")
        monkeypatch.setenv("TEAMS_WEBHOOK_URL", "http://webhook")
        monkeypatch.setattr(analyzer, "carregar_log_erro", lambda _: "log")
        monkeypatch.setattr(analyzer, "analisar_com_llm", lambda _: "analise")

        salvar = MagicMock()
        enviar = MagicMock()
        monkeypatch.setattr(analyzer, "salvar_analise", salvar)
        monkeypatch.setattr(analyzer, "enviar_teams", enviar)

        analyzer.main()

        salvar.assert_called_once_with("analise")
        enviar.assert_called_once_with("analise", "http://webhook")
