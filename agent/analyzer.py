"""
Agente LLM que analisa erros de testes usando Google Gemini
e envia notificação inteligente via Microsoft Teams.
"""

import json
import os
import sys

import requests


def carregar_log_erro(caminho_log: str) -> str:
    """Carrega o conteúdo do log de erro."""
    if not os.path.exists(caminho_log):
        return ""
    with open(caminho_log, "r", encoding="utf-8") as f:
        return f.read()


def analisar_com_llm(log_erro: str) -> str:
    """Envia o log de erro para o Google Gemini e retorna a análise."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "ERRO: GEMINI_API_KEY não configurada."

    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )

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

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )

        if response.status_code != 200:
            return (
                f"Erro ao chamar Gemini API: {response.status_code} - "
                f"{response.text}"
            )

        resultado = response.json()
        return resultado["candidates"][0]["content"]["parts"][0]["text"]

    except requests.RequestException as e:
        return f"Erro de conexão com Gemini API: {e}"
    except (KeyError, IndexError) as e:
        return f"Erro ao processar resposta do Gemini: {e}"


def enviar_teams(mensagem: str, webhook_url: str) -> bool:
    """Envia mensagem para o Microsoft Teams via Incoming Webhook."""
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

        if response.status_code in (200, 202):
            print("✅ Notificação enviada ao Teams com sucesso.")
            return True
        else:
            print(
                f"❌ Falha ao enviar para Teams: "
                f"{response.status_code} - {response.text}"
            )
            return False
    except requests.RequestException as e:
        print(f"❌ Erro de conexão com Teams: {e}")
        return False


def salvar_analise(analise: str, caminho: str = "copilot_analysis.txt"):
    """Salva a análise em arquivo para artifact."""
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(analise)
    print(f"💾 Análise salva em: {caminho}")


def main():
    """Fluxo principal do agente."""
    caminho_log = os.environ.get("TEST_LOG_PATH", "test_output.log")
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "")

    print("=" * 60)
    print("🤖 AGENTE DE ANÁLISE DE ERROS (Gemini) - INICIANDO")
    print("=" * 60)

    # 1. Carregar log de erro
    log_erro = carregar_log_erro(caminho_log)
    if not log_erro:
        print("ℹ️  Nenhum log de erro encontrado. Encerrando.")
        sys.exit(0)

    print(f"📄 Log carregado ({len(log_erro)} caracteres)")
    print("-" * 60)

    # 2. Analisar com LLM (Groq - Llama 3.1 70B)
    print("🧠 Enviando para análise via Google Gemini (gemini-2.0-flash)...")
    analise = analisar_com_llm(log_erro)
    print("\n📋 ANÁLISE DO AGENTE:")
    print("-" * 60)
    print(analise)
    print("-" * 60)

    # 3. Salvar análise para artifact
    salvar_analise(analise)

    # 4. Enviar para Teams
    print("\n📤 Enviando notificação para o Teams...")
    enviar_teams(analise, webhook_url)

    print("\n✅ Agente finalizado.")


if __name__ == "__main__":
    main()
