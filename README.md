# POC - Agente LLM na Pipeline CI/CD

## Visão Geral

Esta POC demonstra a viabilidade técnica de ter um **agente inteligente (LLM)** rodando dentro de uma esteira CI/CD no GitHub Actions. Quando um módulo Python é alterado, a pipeline executa os testes e, em caso de falha, o agente analisa o erro usando **GitHub Models (GPT-4o)** e envia uma explicação detalhada para o **Microsoft Teams**.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS                             │
│                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌──────────────┐    ┌─────────┐ │
│  │ Checkout │───▶│ Pytest  │───▶│ Agente LLM   │───▶│  Teams  │ │
│  │  código  │    │ (testes)│    │ (analyzer.py)│    │ Webhook │ │
│  └─────────┘    └────┬────┘    └──────┬───────┘    └─────────┘ │
│                       │               │                          │
│                  test_output.log  GitHub Models                   │
│                                   (GPT-4o)                       │
└──────────────────────────────────────────────────────────────────┘
```

## Fluxo de Execução

1. Developer faz push no path `src/**`
2. GitHub Actions dispara a pipeline
3. Pytest executa os testes unitários
4. **Se testes passam** → pipeline finaliza com sucesso ✅
5. **Se testes falham** → agente é acionado:
   - Lê o log de erro
   - Envia para GitHub Models (GPT-4o) para análise
   - Recebe explicação inteligente com causa raiz e sugestão
   - Envia Adaptive Card para canal do Teams
   - Pipeline falha com indicação de verificar o Teams

---

## Passo a Passo de Configuração

### 1. Criar Repositório no GitHub

```bash
# Na raiz do projeto (esta pasta)
git init
git add .
git commit -m "feat: POC agente LLM na pipeline"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/poc-agent-pipeline.git
git push -u origin main
```

### 2. Configurar Webhook do Microsoft Teams

#### 2.1 Criar Incoming Webhook no Teams

1. Abra o **Microsoft Teams**
2. Vá ao **canal** onde deseja receber as notificações
3. Clique nos **três pontos (⋯)** ao lado do nome do canal
4. Selecione **Gerenciar canal** (Manage channel)
5. Expanda a seção **Conectores** (ou vá em Configurações > Conectores)
6. Procure **"Incoming Webhook"** e clique em **Configurar**
7. Dê um nome (ex: `CI Pipeline Agent`)
8. Opcionalmente, adicione um ícone
9. Clique em **Criar**
10. **Copie a URL gerada** — essa é a URL do webhook

> ⚠️ **Nota:** Se estiver usando o "novo" Teams (Workflows), o caminho pode ser:
> - Vá em **Power Automate** > **Criar fluxo** > **Quando um webhook é recebido**
> - Ou em Teams: Canal > ⋯ > **Workflows** > **Postar em um canal quando um webhook é recebido**
> - Copie a URL do webhook gerado

#### 2.2 Testar o Webhook (opcional)

```bash
curl -X POST "SUA_URL_DO_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","version":"1.4","body":[{"type":"TextBlock","text":"Teste de webhook!"}]}}]}'
```

Se aparecer a mensagem no canal, o webhook está funcionando.

### 3. Configurar GitHub Secrets

1. Vá ao repositório no GitHub
2. **Settings** > **Secrets and variables** > **Actions**
3. Clique em **New repository secret**
4. Adicione:

| Nome do Secret       | Valor                                      |
|---------------------|--------------------------------------------|
| `TEAMS_WEBHOOK_URL` | URL copiada do webhook do Teams            |

> **Nota:** O `GITHUB_TOKEN` já é fornecido automaticamente pelo GitHub Actions com permissão de acesso ao GitHub Models.

### 4. Habilitar GitHub Models

1. Vá ao repositório no GitHub
2. Verifique se o GitHub Models está disponível na sua conta/organização
3. No workflow, já adicionamos `permissions: models: read`
4. O `GITHUB_TOKEN` automático do Actions terá acesso ao endpoint de modelos

> ⚠️ Se o GitHub Models ainda não estiver disponível na sua conta, pode ser necessário entrar na lista de espera em: https://github.com/marketplace/models

---

## Testando a POC

### Cenário 1: Testes Passam (sem notificação)

Sem alterar nada no código, faça push. Todos os testes devem passar.

```bash
git push origin main
```

### Cenário 2: Forçar Erro (agente ativado + notificação Teams)

Altere o módulo para introduzir um bug:

```python
# src/calculadora.py - altere a função somar:
def somar(a: float, b: float) -> float:
    return a - b  # Bug intencional: subtrai ao invés de somar
```

```bash
git add .
git commit -m "test: introduzir bug para testar agente"
git push origin main
```

**Resultado esperado:**
1. Pipeline executa pytest → testes falham
2. Agente lê o log de erro
3. Agente envia para GPT-4o → recebe análise inteligente
4. Agente envia Adaptive Card para o Teams com:
   - Resumo da falha
   - Causa raiz
   - Sugestão de correção
5. Pipeline falha com mensagem indicando verificar o Teams

---

## Estrutura do Projeto

```
.
├── src/
│   ├── __init__.py
│   └── calculadora.py          # Módulo de exemplo (calculadora)
├── tests/
│   ├── __init__.py
│   └── test_calculadora.py     # Testes unitários (pytest)
├── agent/
│   └── analyzer.py             # Agente LLM (GitHub Models + Teams)
├── .github/
│   └── workflows/
│       └── ci-agent.yml        # Pipeline GitHub Actions
├── requirements.txt            # Dependências Python
└── README.md                   # Este arquivo
```

---

## Critérios de Sucesso da POC

| # | Critério                                                | Status |
|---|--------------------------------------------------------|--------|
| 1 | Pipeline dispara apenas quando `src/` é alterado       | ⬜     |
| 2 | Testes executam corretamente (pytest)                  | ⬜     |
| 3 | Agente é acionado SOMENTE quando há falha              | ⬜     |
| 4 | LLM (GitHub Models) retorna análise coerente           | ⬜     |
| 5 | Notificação chega no Teams com Adaptive Card           | ⬜     |
| 6 | Card contém: repo, branch, commit, análise, link       | ⬜     |
| 7 | Pipeline falha corretamente quando testes falham       | ⬜     |

---

## Troubleshooting

### Erro 403 no GitHub Models
- Verifique se sua conta/org tem acesso ao GitHub Models
- Confirme que o workflow tem `permissions: models: read`

### Webhook do Teams não funciona
- Teste a URL manualmente com curl
- Verifique se o formato está como Adaptive Card (necessário para novos webhooks)
- Se usar Workflows (Power Automate), o payload pode ter formato diferente

### Testes não encontram o módulo
- Verifique se `src/__init__.py` existe
- Teste localmente: `pytest tests/ -v`

---

## Executando Localmente (para debug)

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar testes
pytest tests/ -v

# Testar o agente manualmente (precisa das env vars)
export GITHUB_TOKEN="seu_token_pat"
export TEAMS_WEBHOOK_URL="url_do_webhook"
export TEST_LOG_PATH="test_output.log"

# Gerar log de erro
pytest tests/ -v --tb=long > test_output.log 2>&1

# Rodar agente
python agent/analyzer.py
```

---

## Tecnologias

- **Python 3.12** — Linguagem principal
- **pytest** — Framework de testes
- **GitHub Actions** — Plataforma de CI/CD
- **GitHub Models (GPT-4o)** — LLM para análise inteligente
- **Microsoft Teams (Incoming Webhook)** — Canal de notificação
- **Adaptive Cards** — Formato rico para mensagens no Teams
