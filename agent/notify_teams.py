"""
Módulo responsável por enviar a análise do Copilot para o Microsoft Teams.

Lê o arquivo de análise gerado pelo Copilot CLI e envia como Adaptive Card
para um canal do Teams via Incoming Webhook.
"""

import os

try:
    from agent.common import enviar_teams, ler_arquivo
except ModuleNotFoundError:  # executado como script: `python agent/notify_teams.py`
    from common import enviar_teams, ler_arquivo


def carregar_analise(caminho: str = "copilot_analysis.txt") -> str:
    """Carrega o conteúdo da análise gerada pelo Copilot CLI."""
    return ler_arquivo(
        caminho,
        padrao="Análise não disponível - arquivo não encontrado.",
        strip=True,
    )


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
    sucesso = enviar_teams(
        analise,
        webhook_url,
        titulo="🚨 Falha na Pipeline CI - Análise Copilot",
        rotulo_analise="🤖 **Análise do GitHub Copilot:**",
    )

    if not sucesso:
        print("⚠️  Notificação não enviada, mas pipeline continua.")

    print("\n✅ Script finalizado.")


if __name__ == "__main__":
    main()
