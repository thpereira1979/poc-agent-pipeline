# POC - Agente LLM na Pipeline CI/CD

## Visão Geral

Esta POC demonstra a viabilidade técnica de ter um **agente inteligente (LLM)** rodando dentro de uma esteira CI/CD no GitHub Actions. Quando o módulo Python é alterado, a pipeline executa os testes e, em caso de falha, o agente analisa o erro usando **Google Gemini** e envia uma explicação inteligente para o **Microsoft Teams**.

## Arquitetura

```
┌──────────────────────────────────────────────────────────────────────┐
│                        GITHUB ACTIONS                                 │
│                                                                      │
│  ┌─────────┐    ┌─────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │ Checkout │───▶│ Pytest  │───▶│ Agente LLM   │───▶│ Teams       │ │
│  │  código  │    │ (testes)│    │ (Gemini API) │    │ (Webhook)   │ │
│  └─────────┘    └────┬────┘    └──────┬───────┘    └─────────────┘ │
│                       │               │                              │
│                  test_output.log   Análise salva                      │
│                                   como Artifact                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Fluxo de Execução

1. Developer faz push alterando algo no path `src/**`
2. GitHub Actions dispara a pipeline
3. Pytest executa os testes unitários
4. **Se testes passam** → pipeline finaliza com sucesso ✅
5. **Se testes falham** → Agente LLM é acionado:
   - Lê o log de erro dos testes
   - Envia para a API do Google Gemini para análise inteligente
   - Recebe: resumo da falha, causa raiz e sugestão de correção
   - Salva análise como artifact (download disponível por 30 dias)
   - Envia Adaptive Card para canal do Teams via webhook
   - Pipeline falha com indicação de verificar o Teams

---

## Pré-requisitos

- Conta GitHub
- **Google AI Studio** com API key (billing habilitado)
- Acesso a um canal do **Microsoft Teams**
- Git instalado localmente
- Python 3.12+

---

## Passo a Passo de Configuração

### 1. Clonar o Repositório

```bash
git clone https://github.com/thpereira1979/poc-agent-pipeline.git
cd poc-agent-pipeline
```

### 2. Obter API Key do Google Gemini

1. Acesse: https://aistudio.google.com/apikey
2. Clique em **"Create API Key"**
3. Selecione um projeto com billing habilitado
4. **Copie a key** gerada

> ⚠️ O billing precisa estar habilitado no projeto Google Cloud vinculado.
> Para habilitar: https://console.cloud.google.com/billing

### 3. Configurar Incoming Webhook no Microsoft Teams

#### Opção A: Teams Clássico (Conectores)

1. Abra o **Microsoft Teams**
2. Vá ao **canal** onde deseja receber as notificações
3. Clique nos **três pontos (⋯)** ao lado do nome do canal
4. Selecione **Gerenciar canal** > **Conectores**
5. Procure **"Incoming Webhook"** e clique em **Configurar**
6. Dê um nome: `CI Pipeline Agent`
7. Clique em **Criar**
8. **Copie a URL** do webhook gerado

#### Opção B: Teams Novo (Workflows / Power Automate)

1. No canal do Teams, clique nos **⋯** > **Workflows**
2. Busque: **"Postar em um canal quando um webhook é recebido"**
3. Selecione o template e configure o canal de destino
4. Clique em **Adicionar fluxo de trabalho**
5. **Copie a URL** do webhook gerado

#### Testar o Webhook (opcional)

PowerShell:
```powershell
$body = '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","version":"1.4","body":[{"type":"TextBlock","text":"✅ Webhook funcionando!"}]}}]}'
Invoke-RestMethod -Uri "SUA_URL_DO_WEBHOOK" -Method Post -Body $body -ContentType "application/json"
```

Linux/Mac:
```bash
curl -X POST "SUA_URL_DO_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","version":"1.4","body":[{"type":"TextBlock","text":"✅ Webhook funcionando!"}]}}]}'
```

### 4. Configurar GitHub Secrets

1. Acesse: https://github.com/thpereira1979/poc-agent-pipeline/settings/secrets/actions
2. Clique em **New repository secret** e adicione:

| Nome do Secret       | Valor                                          |
|---------------------|------------------------------------------------|
| `GEMINI_API_KEY`    | API key do Google AI Studio                    |
| `TEAMS_WEBHOOK_URL` | URL do webhook do Teams                        |

---

## Testando a POC

### Cenário 1: Testes Passam (sem notificação)

Com o código correto, faça um push com alteração em `src/`:
```bash
# Adicione um comentário no arquivo, por exemplo
git add src/calculadora.py
git commit -m "test: validar pipeline sem erro"
git push
```
Pipeline passa sem acionar o agente.

### Cenário 2: Forçar Erro (agente analisa + notifica Teams)

Introduza um bug no módulo:

```python
# src/calculadora.py - altere a função somar:
def somar(a: float, b: float) -> float:
    """Retorna a soma de dois números."""
    return a - b  # BUG INTENCIONAL
```

```bash
git add src/calculadora.py
git commit -m "test: introduzir bug para testar agente"
git push
```

**Resultado esperado:**
1. ✅ Pipeline dispara (mudança em `src/`)
2. ✅ Pytest executa → testes falham
3. ✅ Agente chama API do Gemini com o log de erro
4. ✅ Gemini retorna análise (resumo, causa raiz, sugestão)
5. ✅ Análise salva como artifact (download na página do Actions)
6. ✅ Adaptive Card enviada para o canal do Teams
7. ❌ Pipeline falha com mensagem indicando verificar o Teams

### Cenário 3: Corrigir o Bug

```python
# src/calculadora.py - restaure:
def somar(a: float, b: float) -> float:
    """Retorna a soma de dois números."""
    return a + b
```

```bash
git add src/calculadora.py
git commit -m "fix: corrigir função somar"
git push
```

Pipeline passa sem acionar o agente.

---

## Onde Ver a Análise do Agente

A análise gerada pelo LLM fica disponível em 3 lugares:

1. **Log da pipeline** — Expanda o step "Executar Agente de Análise (Gemini)" na aba Actions
2. **Artifact** — Na página Summary da execução, role até "Artifacts" e baixe `analise-agente` (contém `copilot_analysis.txt` e `test_output.log`)
3. **Teams** — Adaptive Card no canal configurado com link direto para a pipeline

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
│   ├── analyzer.py             # Agente LLM (Gemini + Teams)
│   └── notify_teams.py         # Script auxiliar de notificação
├── .github/
│   └── workflows/
│       └── ci-agent.yml        # Pipeline GitHub Actions
├── requirements.txt            # Dependências Python
├── .gitignore
└── README.md                   # Este arquivo
```

---

## Como o Agente Funciona (analyzer.py)

O agente executa o seguinte fluxo:

1. **Carrega o log** de erro gerado pelo pytest (`test_output.log`)
2. **Tenta múltiplos modelos** Gemini em sequência (fallback automático):
   - `gemini-3.5-flash`
   - `gemini-3.5-flash-preview-05-20`
   - `gemini-3-flash-preview`
   - `gemini-1.5-flash-latest`
   - `gemini-1.5-flash`
3. **Recebe a análise** com: resumo, causa raiz e sugestão de correção
4. **Salva em arquivo** (`copilot_analysis.txt`) para upload como artifact
5. **Envia para o Teams** como Adaptive Card com informações do repositório, branch, commit e link para a pipeline

---

## Critérios de Sucesso da POC

| # | Critério                                                    | Status |
|---|-------------------------------------------------------------|--------|
| 1 | Pipeline dispara apenas quando `src/` é alterado            | ⬜     |
| 2 | Testes executam corretamente (pytest)                       | ⬜     |
| 3 | Agente é acionado SOMENTE quando há falha                   | ⬜     |
| 4 | LLM retorna análise coerente em português                   | ⬜     |
| 5 | Análise salva como artifact para download                   | ⬜     |
| 6 | Notificação chega no Teams com Adaptive Card                | ⬜     |
| 7 | Card contém: repo, branch, commit, análise, link            | ⬜     |
| 8 | Pipeline falha corretamente quando testes falham            | ⬜     |

---

## Troubleshooting

### Erro 404 no Gemini (modelo não encontrado)
- O agente tenta múltiplos modelos automaticamente
- Se todos falharem, verifique se o billing está ativo no projeto Google Cloud
- Acesse https://aistudio.google.com para verificar modelos disponíveis

### Erro 429 (quota excedida)
- Habilite billing no Google Cloud: https://console.cloud.google.com/billing
- Vincule o projeto da API key a uma billing account

### Webhook do Teams não funciona
- Teste a URL manualmente com curl/PowerShell
- Verifique se o payload está no formato Adaptive Card
- Se usar Workflows (Power Automate), confirme que o fluxo está ativo

### Testes não encontram o módulo
- Verifique se `src/__init__.py` existe
- Teste localmente: `python -m pytest tests/ -v`

### Artifact não aparece
- O artifact fica na página **Summary** da execução (não no job)
- Role até o final da página Summary para encontrar a seção "Artifacts"

---

## Executando Localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Rodar testes (devem passar com código correto)
python -m pytest tests/ -v

# Simular falha (altere calculadora.py com bug, depois rode):
python -m pytest tests/ -v --tb=long > test_output.log 2>&1

# Rodar agente manualmente
set GEMINI_API_KEY=sua_key_aqui
set TEAMS_WEBHOOK_URL=url_do_webhook
set TEST_LOG_PATH=test_output.log
python agent/analyzer.py
```

---

## Custos

| Recurso | Custo estimado |
|---------|---------------|
| GitHub Actions | Gratuito (2000 min/mês em repos públicos) |
| Gemini API (por execução) | ~$0.0002 (menos de 0,02 centavos) |
| Teams Webhook | Gratuito |

Para gastar $1 no Gemini, seriam necessárias ~5.000 execuções do agente.

---

## Tecnologias

- **Python 3.12** — Linguagem do módulo e scripts
- **pytest** — Framework de testes
- **GitHub Actions** — Plataforma de CI/CD
- **Google Gemini API** — LLM para análise inteligente de erros
- **Microsoft Teams (Incoming Webhook)** — Canal de notificação
- **Adaptive Cards** — Formato rico para mensagens no Teams

---

## Referências

- [Google AI Studio - API Keys](https://aistudio.google.com/apikey)
- [Gemini API Docs](https://ai.google.dev/gemini-api/docs)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [Teams Incoming Webhooks](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook)
