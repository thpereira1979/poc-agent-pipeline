"""Testes para os utilitários compartilhados do agente."""

from agent.common import _montar_payload, ler_arquivo


class TestLerArquivo:
    def test_arquivo_inexistente_retorna_padrao(self):
        assert ler_arquivo("nao_existe.txt", padrao="fallback") == "fallback"

    def test_le_conteudo(self, tmp_path):
        arquivo = tmp_path / "log.txt"
        arquivo.write_text("conteúdo do log\n", encoding="utf-8")
        assert ler_arquivo(str(arquivo)) == "conteúdo do log\n"

    def test_strip_remove_espacos(self, tmp_path):
        arquivo = tmp_path / "analise.txt"
        arquivo.write_text("  texto  \n", encoding="utf-8")
        assert ler_arquivo(str(arquivo), strip=True) == "texto"


class TestMontarPayload:
    def test_usa_titulo_e_rotulo(self):
        payload = _montar_payload("análise", "TÍTULO", "RÓTULO")
        body = payload["attachments"][0]["content"]["body"]
        textos = [bloco.get("text") for bloco in body]
        assert "TÍTULO" in textos
        assert "RÓTULO" in textos
        assert "análise" in textos
