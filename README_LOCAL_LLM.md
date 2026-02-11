# Dexter Engenharia - Local LLM Setup

Este projeto suporta execução de modelos locais via Ollama para economizar custos de API e garantir privacidade dos dados.

## Pré-requisitos

1.  **Ollama**: Deve estar instalado e rodando em `http://localhost:11434`.
2.  **Dependências**: O pacote `httpx` é necessário (já instalado no ambiente).

## Modelos Instalados

Detectamos que o ambiente já possui:
- `llama3.1:latest` (ou `llama3.1:8b`)

### Como Executar

Para usar o modelo local `llama3.1`, use a flag `--local-model`:

```bash
dexter src/dexter_eng/data/samples/edital_exemplo.pdf --local-model "llama3.1:latest" -v
```

### Usando Outros Modelos

Se preferir o **Mistral** (leve e eficiente):

1.  Baixe o modelo:
    ```bash
    ollama pull mistral
    ```
2.  Execute:
    ```bash
    dexter src/dexter_eng/data/samples/edital_exemplo.pdf --local-model mistral -v
    ```

## Configurações para RTX 4060 (8GB VRAM)

O `LocalOllamaClient` vem configurado com defaults seguros para sua GPU:
- **Context Window (`num_ctx`)**: 8192 tokens.
- **Predict `num_predict`**: 2048 tokens (para evitar cortes no JSON).
- **Temperatura**: 0.2 (para maior determinismo em tarefas de extração).

Se encontrar erros de memória (OOM), considere reduzir o `num_ctx` no arquivo `src/dexter_eng/adapters/llm/local_ollama_client.py` para 4096.

## Troubleshooting

- **JSON Inválido**: Modelos locais podem ser verbosos. O adapter tenta mitigar isso, mas se persistir, tente reduzir a temperatura para 0.0 ou reforçar o prompt.
- **Connection Error**: Verifique se o Ollama está rodando (`ollama serve` ou check o ícone na tray do Windows).

## GPU Troubleshooting

Se o modelo estiver lento e não usar a GPU (0% no Gerenciador de Tarefas):
1.  Verifique os logs em `%LOCALAPPDATA%\Ollama\server.log`. Procure por "failure during GPU discovery".
2.  **Solução**: Reinicie o Ollama.
    ```powershell
    taskkill /F /IM ollama.exe
    ollama serve
    ```
3.  Verifique se o driver NVIDIA está atualizado (`nvidia-smi`).
## Qualidade vs. Custo

Modelos locais (especialmente 7B/8B) são ótimos para testar o pipeline sem custo, mas **a qualidade da extração pode ser inferior** aos modelos cloud (GPT-4o ou Claude 3.5 Sonnet).

**Observações:**
- **Local (Llama 3.1 8B)**: Pode alucinar campos complexos ou simplificar demais o resumo. Ideal para *triagem inicial* ou desenvolvimento.
- **Cloud**: Continua sendo recomendado para a versão final de produção.

### Roadmap (Otimizações Futuras)
Estamos planejando melhorias para tornar o uso local mais viável em produção:
1.  **Modo Híbrido**: Usar Local LLM para tarefas simples (resumo, classificação) e Cloud LLM apenas para extração complexa (tabelas, regras de negócio).
2.  **Fine-tuning**: Ajustar um modelo Lora pequeno especificamente para leitura de editais.
3.  **Prompt Engineering**: Criar prompts específicos e mais rígidos para modelos menores.
