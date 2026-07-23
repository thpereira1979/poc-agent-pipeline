"""
Utilitários compartilhados pelos scripts do agente.

Reúne funções reaproveitadas por ``analyzer.py`` e ``notify_teams.py``:
leitura de arquivos e envio de Adaptive Cards para o Microsoft Teams.
"""

import os

import requests


def ler_arquivo(caminho: str, padrao: str = "", strip: bool = False) -> str:
    """Lê o conteúdo de um arquivo de texto.

    Retorna ``padrao`` caso o arquivo não exista. Quando ``strip`` é ``True``,
    remove espaços em branco nas extremidades do conteúdo lido.
    """
    if not os.path.exists(caminho):
        return padrao
    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()
    return conteudo.strip() if strip else conteudo


def _montar_payload(mensagem: str, titulo: str, rotulo_analise: str) -> dict:
    """Monta o Adaptive Card enviado ao Teams."""
    return {
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
                            "text": titulo,
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
                            "text": rotulo_analise,
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


def enviar_teams(
    mensagem: str,
    webhook_url: str,
    titulo: str = "🚨 Falha na Pipeline CI",
    rotulo_analise: str = "🤖 **Análise do Agente IA:**",
) -> bool:
    """Envia mensagem para o Microsoft Teams via Incoming Webhook.

    ``titulo`` e ``rotulo_analise`` permitem personalizar o cabeçalho do card
    conforme a origem da análise (Gemini, Copilot, etc.).
    """
    if not webhook_url:
        print("⚠️  TEAMS_WEBHOOK_URL não configurado. Pulando envio.")
        return False

    payload = _montar_payload(mensagem, titulo, rotulo_analise)

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
