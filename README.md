# POC - Agente Copilot na Pipeline CI/CD

## Visão Geral

Esta POC demonstra a viabilidade técnica de ter um **agente inteligente (GitHub Copilot)** rodando dentro de uma esteira CI/CD no GitHub Actions. Quando o módulo Python é alterado, a pipeline executa os testes e, em caso de falha, o **Copilot CLI** analisa o erro e envia uma explicação inteligente para o **Microsoft Teams**.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS                                 │
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │ Checkout │───▶│ Pytest  │───▶│ Copilot CLI  │───▶│ Teams       │ │
│  │  código  │    │ (testes)│    │ (análise IA) │    │ (Webhook)   │ │
│  └─────────┘    └────┬────┘    └──────────────┘    └─────────────┘ │
│                       │                                              │
│                  test_output.log                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Execução

1. Developer faz push alterando algo no path `src/**`
2. GitHub Actions dispara a pipeline
3. Pytest executa os testes unitários
4. **Se testes passam** → pipeline finaliza com sucesso ✅
5. **Se testes falham** → Copilot CLI é acionado:
   - Recebe o log de erro como prompt
   - Gera análise inteligente (causa raiz + sugestão de correção)
   - Script Python envia Adaptive Card para canal do Teams
   - Pipeline falha com indicação de verificar o Teams

---

## Pré-requisitos

- Conta GitHub com **plano Copilot ativo** (Individual, Business ou Enterprise)
- Acesso a um canal do **Microsoft Teams**
- Git instalado localmente

---

## Passo a Passo de Configuração

### 1. Clonar/Subir o Repositório

Se ainda não fez push:
```bash
git init
git add .
git commit -m "feat: POC agente Copilot na pipeline"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/poc-agent-pipeline.git
git push -u origin main
```

### 2. Criar Personal Access Token (PAT) para o Copilot

O Copilot CLI precisa de um PAT com permissão específica:

1. Acesse: https://github.com/settings/personal-access-tokens/new
2. Selecione **Fine-grained token**
3. Configure:
   - **Nome:** `copilot-ci-agent`
   - **Expiração:** 90 dias (ou conforme política)
   - **Repository access:** selecione o repositório `poc-agent-pipeline`
   - **Permissions:**
     - Em **Account permissions**, habilite: **Copilot Requests → Read and write**
4. Clique em **Generate token**
5. **Copie o token** (começa com `github_pat_...`)

### 3. Configurar Incoming Webhook no Microsoft Teams

#### Opção A: Teams Clássico (Conectores)

1. Abra o **Microsoft Teams**
2. Vá ao **canal** onde deseja receber as notificações
3. Clique nos **três pontos (⋯)** ao lado do nome do canal
4. Selecione **Gerenciar canal** > **Conectores**
5. Procure **"Incoming Webhook"** e clique em **Configurar**
6. Dê um nome: `CI Pipeline Copilot`
7. Clique em **Criar**
8. **Copie a URL** do webhook gerado

#### Opção B: Teams Novo (Workflows / Power Automate)

1. No canal do Teams, clique nos **⋯** > **Workflows**
2. Busque: **"Postar em um canal quando um webhook é recebido"**
3. Selecione o template e configure o canal de destino
4. Clique em **Adicionar fluxo de trabalho**
5. **Copie a URL** do webhook gerado

#### Testar o Webhook (opcional)

Linux/Mac:
```bash
curl -X POST "SUA_URL_DO_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","version":"1.4","body":[{"type":"TextBlock","text":"✅ Webhook funcionando!"}]}}]}'
```

PowerShell:
```powershell
$body = '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","version":"1.4","body":[{"type":"TextBlock","text":"✅ Webhook funcionando!"}]}}]}'
Invoke-RestMethod -Uri "SUA_URL_DO_WEBHOOK" -Method Post -Body $body -ContentType "application/json"
```

Se a mensagem aparecer no canal, o webhook está OK.

### 4. Configurar GitHub Secrets

1. Vá ao repositório no GitHub: **Settings** > **Secrets and variables** > **Actions**
2. Clique em **New repository secret** e adicione:

| Nome do Secret       | Valor                                          |
|---------------------|------------------------------------------------|
| `COPILOT_PAT`       | Token PAT criado no passo 2                    |
| `TEAMS_WEBHOOK_URL` | URL do webhook do Teams criada no passo 3      |

### 5. Verificar Permissões do Workflow

O workflow já está configurado com:
```yaml
permissions:
  contents: read
  copilot-requests: write
```

Isso permite que o Copilot CLI funcione com o PAT dentro do Actions.

---

## Testando a POC

### Cenário 1: Testes Passam (sem notificação)

Sem alterar nada no módulo, a pipeline passa normalmente:
```bash
git commit --allow-empty -m "test: trigger pipeline"
git push
```
> Nota: só dispara se houver mudanças em `src/`. Para teste rápido, adicione um comentário.

### Cenário 2: Forçar Erro (Copilot analisa + notifica Teams)

Introduza um bug no módulo:

```python
# src/calculadora.py - altere a função somar:
def somar(a: float, b: float) -> float:
    """Retorna a soma de dois números."""
    return a - b  # BUG INTENCIONAL: subtrai ao invés de somar
```

Faça push:
```bash
git add src/calculadora.py
git commit -m "test: introduzir bug para testar agente Copilot"
git push
```

**Resultado esperado:**
1. ✅ Pipeline dispara (mudança em `src/`)
2. ✅ Pytest executa → testes falham
3. ✅ Copilot CLI recebe o log e gera análise
4. ✅ Script Python envia Adaptive Card para o Teams
5. ✅ Pipeline falha com mensagem clara

### Cenário 3: Corrigir o Bug

```python
# src/calculadora.py - restaure a função:
def somar(a: float, b: float) -> float:
    """Retorna a soma de dois números."""
    return a + b  # Corrigido
```

```bash
git add src/calculadora.py
git commit -m "fix: corrigir função somar"
git push
```

Pipeline deve passar sem acionar o Copilot.

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
│   ├── __init__.py
│   ├── analyzer.py             # (legado - GitHub Models)
│   └── notify_teams.py         # Envia análise para Teams
├── .github/
│   └── workflows/
│       └── ci-agent.yml        # Pipeline GitHub Actions
├── requirements.txt            # Dependências Python
├── .gitignore
└── README.md                   # Este arquivo
```

---

## Critérios de Sucesso da POC

| # | Critério                                                    | Status |
|---|-------------------------------------------------------------|--------|
| 1 | Pipeline dispara apenas quando `src/` é alterado            | ⬜     |
| 2 | Testes executam corretamente (pytest)                       | ⬜     |
| 3 | Copilot CLI é acionado SOMENTE quando há falha              | ⬜     |
| 4 | Copilot retorna análise coerente em português               | ⬜     |
| 5 | Notificação chega no Teams com Adaptive Card                | ⬜     |
| 6 | Card contém: repo, branch, commit, análise, link            | ⬜     |
| 7 | Pipeline falha corretamente quando testes falham            | ⬜     |

---

## Troubleshooting

### Erro "copilot: command not found"
- Verifique se o step de instalação está antes do step de execução
- Confirme que `npm install -g @github/copilot` foi executado com sucesso

### Erro de autenticação do Copilot
- Confirme que o secret `COPILOT_PAT` está configurado
- Verifique se o PAT tem a permissão **"Copilot Requests"**
- Confirme que seu plano Copilot está ativo

### Webhook do Teams não funciona
- Teste a URL manualmente com curl/PowerShell
- Verifique se o payload está no formato Adaptive Card
- Se usar Workflows (Power Automate), confirme que o fluxo está ativo

### Testes não encontram o módulo
- Verifique se `src/__init__.py` existe
- Teste localmente: `pytest tests/ -v`

---

## Executando Localmente (para debug)

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar testes (devem passar)
pytest tests/ -v

# Simular falha e gerar log
# (altere calculadora.py com bug, depois rode:)
pytest tests/ -v --tb=long > test_output.log 2>&1

# Testar envio para Teams (precisa da env var)
export TEAMS_WEBHOOK_URL="url_do_webhook"
python agent/notify_teams.py
```

---

## Tecnologias

- **Python 3.12** — Linguagem do módulo e scripts
- **pytest** — Framework de testes
- **GitHub Actions** — Plataforma de CI/CD
- **GitHub Copilot CLI** — Agente LLM para análise de erros
- **Microsoft Teams (Incoming Webhook)** — Canal de notificação
- **Adaptive Cards** — Formato rico para mensagens no Teams

---

## Referências

- [GitHub Copilot CLI em Actions](https://docs.github.com/en/copilot/how-tos/copilot-cli/automate-copilot-cli/automate-with-actions)
- [Autenticação com GITHUB_TOKEN](https://docs.github.com/en/copilot/how-tos/copilot-cli/use-copilot-cli-in-actions)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [Teams Incoming Webhooks](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)
