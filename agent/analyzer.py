"""
Agente LLM que analisa erros de testes usando Google Gemini
e envia notificação inteligente via Microsoft Teams.
"""

import os
import sys

import requests

try:
    from agent.common import enviar_teams, ler_arquivo
except ModuleNotFoundError:  # executado como script: `python agent/analyzer.py`
    from common import enviar_teams, ler_arquivo


def carregar_log_erro(caminho_log: str) -> str:
    """Carrega o conteúdo do log de erro."""
    return ler_arquivo(caminho_log, padrao="")


def analisar_com_llm(log_erro: str) -> str:
    """Envia o log de erro para o Google Gemini e retorna a análise."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "ERRO: GEMINI_API_KEY não configurada."

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

            if response.status_code == 200:
                resultado = response.json()
                print(f"  ✅ Sucesso com modelo: {modelo}")
                return resultado["candidates"][0]["content"]["parts"][0]["text"]
            else:
                print(f"  ❌ {modelo}: {response.status_code} - {response.json().get('error', {}).get('message', 'erro desconhecido')}")
                continue

        except requests.RequestException as e:
            print(f"  ❌ {modelo}: erro de conexão - {e}")
            continue
        except (KeyError, IndexError) as e:
            print(f"  ❌ {modelo}: erro ao processar resposta - {e}")
            continue

    return "ERRO: Nenhum modelo Gemini disponível respondeu com sucesso."


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

    # 2. Analisar com LLM (Google Gemini)
    print("🧠 Enviando para análise via Google Gemini...")
    analise = analisar_com_llm(log_erro)
    print("\n📋 ANÁLISE DO AGENTE:")
    print("-" * 60)
    print(analise)
    print("-" * 60)

    # 3. Salvar análise para artifact
    salvar_analise(analise)

    # 4. Enviar para Teams
    print("\n📤 Enviando notificação para o Teams...")
    enviar_teams(
        analise,
        webhook_url,
        titulo="🚨 Falha na Pipeline CI - Análise Gemini",
        rotulo_analise="🤖 **Análise do Agente IA (Gemini):**",
    )

    print("\n✅ Agente finalizado.")


if __name__ == "__main__":
    main()
