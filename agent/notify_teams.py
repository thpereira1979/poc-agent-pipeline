"""
Módulo responsável por enviar a análise do Copilot para o Microsoft Teams.

Lê o arquivo de análise gerado pelo Copilot CLI e envia como Adaptive Card
para um canal do Teams via Incoming Webhook.
"""

import os
import sys

import requests

from agent.errors import LogError, NotificacaoError


def carregar_analise(caminho: str = "copilot_analysis.txt") -> str:
    """Carrega o conteúdo da análise gerada pelo Copilot CLI.

    Raises:
        LogError: Se o arquivo existir mas não puder ser lido.
    """
    if not os.path.exists(caminho):
        return "Análise não disponível - arquivo não encontrado."
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError as e:
        raise LogError(
            f"Falha ao ler a análise em '{caminho}': {e}"
        ) from e


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
    except requests.RequestException as e:
        raise NotificacaoError(f"Erro de conexão com Teams: {e}") from e

    if response.status_code in (200, 202):
        print("✅ Notificação enviada ao Teams com sucesso.")
        return True

    raise NotificacaoError(
        f"Teams respondeu com HTTP {response.status_code}: {response.text[:500]}"
    )


def main() -> int:
    """Fluxo principal: carrega análise e envia para Teams.

    A notificação é best-effort, mas uma falha real de envio é propagada
    via código de saída diferente de zero, em vez de silenciada.
    """
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
    try:
        enviar_teams(analise, webhook_url)
    except NotificacaoError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("⚠️  Notificação não enviada.")
        return 1

    print("\n✅ Script finalizado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
