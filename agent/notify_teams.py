"""
Módulo responsável por enviar a análise do Copilot para o Microsoft Teams.

Lê o arquivo de análise gerado pelo Copilot CLI e envia como Adaptive Card
para um canal do Teams via Incoming Webhook.
"""

import json
import os
import sys

import requests


def carregar_analise(caminho: str = "copilot_analysis.txt") -> str:
    """Carrega o conteúdo da análise gerada pelo Copilot CLI."""
    if not os.path.exists(caminho):
        return "Análise não disponível - arquivo não encontrado."
    with open(caminho, "r", encoding="utf-8") as f:
        return f.read().strip()


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
                            "text": "🚨 Falha na Pipeline CI - Análise Copilot",
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
                                    "value": os.environ.get("GITHUB_SHA", "N/A")[:8],
                                },
                            ],
                        },
                        {"type": "TextBlock", "text": " ", "spacing": "Medium"},
                        {
                            "type": "TextBlock",
                            "text": "🤖 **Análise do GitHub Copilot:**",
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


def main():
    """Fluxo principal: carrega análise e envia para Teams."""
    webhook_url = os.environ.get("TEAMS_WEBHOOK_URL", "")

    print("=" * 60)
    print("📤 ENVIANDO ANÁLISE DO COPILOT PARA O TEAMS")
    print("=" * 60)

    # Carregar análise
    analise = carregar_analise()
    print(f"📄 Análise carregada ({len(analise)} caracteres)")
    print("-" * 60)
    print(analise)
    print("-" * 60)

    # Enviar para Teams
    sucesso = enviar_teams(analise, webhook_url)

    if not sucesso:
        print("⚠️  Notificação não enviada, mas pipeline continua.")

    print("\n✅ Script finalizado.")


if __name__ == "__main__":
    main()
