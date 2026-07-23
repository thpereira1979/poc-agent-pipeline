"""Exceções do agente de análise de erros da pipeline.

Centraliza os tipos de erro para que falhas sejam propagadas de forma
explícita, em vez de serem sinalizadas por strings mágicas ou silenciadas.
"""


class AgenteError(Exception):
    """Erro base para o agente de análise."""


class ConfiguracaoError(AgenteError):
    """Configuração ausente ou inválida (ex.: variável de ambiente faltando)."""


class LogError(AgenteError):
    """Falha ao ler ou escrever arquivos de log/análise."""


class AnaliseLLMError(AgenteError):
    """Nenhum modelo LLM conseguiu produzir uma análise válida."""


class NotificacaoError(AgenteError):
    """Falha ao enviar a notificação para o Microsoft Teams."""
