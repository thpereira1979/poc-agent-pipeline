"""
Agente LLM que analisa erros de testes e envia notificação inteligente via Teams.

Utiliza GitHub Models (GPT-4o) para gerar explicações dos erros encontrados
e envia o resultado para um canal do Microsoft Teams via Incoming Webhook.
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
    """Envia o log de erro para o GitHub Models e retorna a análise."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return "ERRO: GITHUB_TOKEN não configurado."

    endpoint = "https://models.github.ai/inference/chat/completions"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    prompt_sistema = (
        "Você é um engenheiro de software sênior especialista em Python. "
        "Analise o log de erro de testes abaixo e forneça:\n"
        "1. Um resumo claro do que falhou\n"
        "2. A causa raiz provável\n"
        "3. Sugestão de correção\n\n"
        "Seja direto e objetivo. Responda em português brasileiro."
    )

    payload = {
        "model": "openai/gpt-4o",
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": f"Log de erro dos testes:\n\n{log_erro}"},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=60)

    if response.status_code != 200:
        return f"Erro ao chamar GitHub Models: {response.status_code} - {response.text}"

    resultado = response.json()
    return resultado["choices"][0]["message"]["content"]


def enviar_teams(mensagem: str, webhook_url: str) -> bool:
    """Envia mensagem para o Microsoft Teams via Incoming Webhook."""
    if not webhook_url:
        print("AVISO: TEAMS_WEBHOOK_URL não configurado. Pulando envio.")
        return False

    # Formato Adaptive Card para Teams
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
                            "text": "🚨 Falha na Pipeline CI",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Attention",
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Repositório:** {os.environ.get('GITHUB_REPOSITORY', 'N/A')}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Branch:** {os.environ.get('GITHUB_REF_NAME', 'N/A')}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Commit:** {os.environ.get('GITHUB_SHA', 'N/A')[:8]}",
                            "wrap": True,
                        },
                        {"type": "TextBlock", "text": "---", "spacing": "Medium"},
                        {
                            "type": "TextBlock",
                            "text": "**Análise do Agente IA:**",
                            "weight": "Bolder",
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
                            "title": "Ver Pipeline",
                            "url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}",
                        }
                    ],
                },
            }
        ],
    }

    response = requests.post(webhook_url, json=payload, timeout=30)

    if response.status_code in (200, 202):
        print("✅ Notificação enviada ao Teams com sucesso.")
        return True
    else:
        print(f"❌ Falha ao enviar para Teams: {response.status_code} - {response.text}")
        return False


def main():
    """Fluxo principal do agente."""
    caminho_log = os.environ.get("TEST_LOG_PATH", "test_output.log")
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "")

    print("=" * 60)
    print("🤖 AGENTE DE ANÁLISE DE ERROS - INICIANDO")
    print("=" * 60)

    # 1. Carregar log de erro
    log_erro = carregar_log_erro(caminho_log)
    if not log_erro:
        print("ℹ️  Nenhum log de erro encontrado. Encerrando.")
        sys.exit(0)

    print(f"📄 Log carregado ({len(log_erro)} caracteres)")
    print("-" * 60)

    # 2. Analisar com LLM
    print("🧠 Enviando para análise via GitHub Models (GPT-4o)...")
    analise = analisar_com_llm(log_erro)
    print("\n📋 ANÁLISE DO AGENTE:")
    print("-" * 60)
    print(analise)
    print("-" * 60)

    # 3. Enviar para Teams
    print("\n📤 Enviando notificação para o Teams...")
    enviar_teams(analise, webhook_url)

    print("\n✅ Agente finalizado.")


if __name__ == "__main__":
    main()
