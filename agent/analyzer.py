"""
Agente LLM que analisa erros de testes usando Google Gemini
e envia notificação inteligente via Microsoft Teams.
"""

import os
import sys

import requests

from agent.errors import (
    AnaliseLLMError,
    ConfiguracaoError,
    LogError,
    NotificacaoError,
)


def carregar_log_erro(caminho_log: str) -> str:
    """Carrega o conteúdo do log de erro.

    Retorna string vazia quando o arquivo não existe (situação esperada
    quando os testes passaram). Falhas reais de leitura são propagadas
    como ``LogError`` em vez de silenciadas.
    """
    if not os.path.exists(caminho_log):
        return ""
    try:
        with open(caminho_log, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise LogError(
            f"Falha ao ler o log de erro em '{caminho_log}': {e}"
        ) from e


def analisar_com_llm(log_erro: str) -> str:
    """Envia o log de erro para o Google Gemini e retorna a análise.

    Raises:
        ConfiguracaoError: Se ``GEMINI_API_KEY`` não estiver configurada.
        AnaliseLLMError: Se nenhum modelo retornar uma análise válida.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ConfiguracaoError("GEMINI_API_KEY não configurada.")

    # Lista de modelos para tentar (do mais novo ao mais antigo)
    modelos = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-preview-05-20",
        "gemini-3-flash-preview",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
    ]

    prompt = (
        "Você é um engenheiro de software sênior especialista em Python. "
        "Analise o log de erro de testes abaixo e forneça:\n"
        "1. Um resumo claro do que falhou\n"
        "2. A causa raiz provável\n"
        "3. Sugestão de correção com exemplo de código\n\n"
        "Seja direto e objetivo. Responda em português brasileiro.\n\n"
        f"=== LOG DE ERRO ===\n{log_erro}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        },
    }

    erros: list[str] = []

    for modelo in modelos:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{modelo}:generateContent?key={api_key}"
        )
        print(f"  Tentando modelo: {modelo}...")

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
        except requests.RequestException as e:
            msg = f"{modelo}: erro de conexão - {e}"
            print(f"  ❌ {msg}")
            erros.append(msg)
            continue

        if response.status_code != 200:
            detalhe = _extrair_mensagem_erro(response)
            msg = f"{modelo}: HTTP {response.status_code} - {detalhe}"
            print(f"  ❌ {msg}")
            erros.append(msg)
            continue

        try:
            resultado = response.json()
            texto = resultado["candidates"][0]["content"]["parts"][0]["text"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            msg = f"{modelo}: resposta inesperada da API - {e}"
            print(f"  ❌ {msg}")
            erros.append(msg)
            continue

        print(f"  ✅ Sucesso com modelo: {modelo}")
        return texto

    raise AnaliseLLMError(
        "Nenhum modelo Gemini respondeu com sucesso. Tentativas:\n- "
        + "\n- ".join(erros)
    )


def _extrair_mensagem_erro(response: requests.Response) -> str:
    """Extrai uma mensagem legível de uma resposta de erro da API."""
    try:
        corpo = response.json()
    except ValueError:
        return response.text[:500] or "erro desconhecido"
    if isinstance(corpo, dict):
        return corpo.get("error", {}).get("message", "erro desconhecido")
    return "erro desconhecido"


def enviar_teams(mensagem: str, webhook_url: str) -> bool:
    """Envia mensagem para o Microsoft Teams via Incoming Webhook.

    Returns:
        ``True`` se enviado, ``False`` se o webhook não está configurado
        (envio pulado intencionalmente).

    Raises:
        NotificacaoError: Se a requisição de envio falhar.
    """
    if not webhook_url:
        print("⚠️  TEAMS_WEBHOOK_URL não configurado. Pulando envio.")
        return False

    # Adaptive Card para Teams
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "contentUrl": None,
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "🚨 Falha na Pipeline CI - Análise Gemini",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Attention",
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {
                                    "title": "Repositório",
                                    "value": os.environ.get(
                                        "GITHUB_REPOSITORY", "N/A"
                                    ),
                                },
                                {
                                    "title": "Branch",
                                    "value": os.environ.get(
                                        "GITHUB_REF_NAME", "N/A"
                                    ),
                                },
                                {
                                    "title": "Commit",
                                    "value": os.environ.get("GITHUB_SHA", "N/A")[
                                        :8
                                    ],
                                },
                            ],
                        },
                        {"type": "TextBlock", "text": " ", "spacing": "Medium"},
                        {
                            "type": "TextBlock",
                            "text": "🤖 **Análise do Agente IA (Gemini):**",
                            "weight": "Bolder",
                            "size": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": mensagem,
                            "wrap": True,
                            "spacing": "Small",
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "🔗 Ver Pipeline",
                            "url": (
                                f"https://github.com/"
                                f"{os.environ.get('GITHUB_REPOSITORY', '')}/"
                                f"actions/runs/"
                                f"{os.environ.get('GITHUB_RUN_ID', '')}"
                            ),
                        }
                    ],
                },
            }
        ],
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
    except requests.RequestException as e:
        raise NotificacaoError(f"Erro de conexão com Teams: {e}") from e

    if response.status_code in (200, 202):
        print("✅ Notificação enviada ao Teams com sucesso.")
        return True

    raise NotificacaoError(
        f"Teams respondeu com HTTP {response.status_code}: {response.text[:500]}"
    )


def salvar_analise(analise: str, caminho: str = "copilot_analysis.txt") -> None:
    """Salva a análise em arquivo para artifact.

    Raises:
        LogError: Se a escrita do arquivo falhar.
    """
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(analise)
    except OSError as e:
        raise LogError(
            f"Falha ao salvar a análise em '{caminho}': {e}"
        ) from e
    print(f"💾 Análise salva em: {caminho}")


def main() -> int:
    """Fluxo principal do agente.

    Retorna código de saída: 0 em sucesso, diferente de zero quando a
    análise ou a notificação falham, garantindo que o erro seja propagado
    para a pipeline em vez de silenciado.
    """
    caminho_log = os.environ.get("TEST_LOG_PATH", "test_output.log")
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "")

    print("=" * 60)
    print("🤖 AGENTE DE ANÁLISE DE ERROS (Gemini) - INICIANDO")
    print("=" * 60)

    # 1. Carregar log de erro
    log_erro = carregar_log_erro(caminho_log)
    if not log_erro:
        print("ℹ️  Nenhum log de erro encontrado. Encerrando.")
        return 0

    print(f"📄 Log carregado ({len(log_erro)} caracteres)")
    print("-" * 60)

    # 2. Analisar com LLM (Google Gemini)
    print("🧠 Enviando para análise via Google Gemini...")
    analise_falhou = False
    try:
        analise = analisar_com_llm(log_erro)
    except (ConfiguracaoError, AnaliseLLMError) as e:
        analise_falhou = True
        analise = (
            "⚠️ O agente NÃO conseguiu gerar a análise automática.\n\n"
            f"Motivo: {e}\n\n"
            "Verifique o log de testes anexado como artifact."
        )
        print(f"❌ Falha na análise via LLM: {e}", file=sys.stderr)

    print("\n📋 ANÁLISE DO AGENTE:")
    print("-" * 60)
    print(analise)
    print("-" * 60)

    # 3. Salvar análise para artifact (mesmo em caso de falha da LLM)
    salvar_analise(analise)

    # 4. Enviar para Teams (best-effort, mas falhas não são silenciadas)
    print("\n📤 Enviando notificação para o Teams...")
    notificacao_falhou = False
    try:
        enviar_teams(analise, webhook_url)
    except NotificacaoError as e:
        notificacao_falhou = True
        print(f"❌ {e}", file=sys.stderr)

    if analise_falhou or notificacao_falhou:
        print("\n⚠️  Agente finalizado com erros (veja acima).")
        return 1

    print("\n✅ Agente finalizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
