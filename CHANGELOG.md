# Changelog

Histórico de tudo que foi feito no projeto, da atualização mais recente para a mais antiga. Este arquivo é atualizado sempre que uma mudança é enviada ao repositório.

## 2026-07-28

- **Correção**: fallback local via Ollama quebrava com `AttributeError: 'list' object has no attribute 'get'` na Extração de Referência (`/extraction/ocr-preview`) — o modelo local (`qwen2.5:3b`) às vezes devolve uma lista JSON solta em vez do objeto `{"rows": [...]}` pedido no prompt (diferente da Groq, que garante um objeto no nível raiz). O helper `_ollama_chat_json` agora normaliza esse formato antes de devolver, corrigido nos 4 pontos que usam o fallback (extração de referência, geração de treino, geração a partir de referência e extração de imagem).
- **Correção e melhorias no Painel de Performance** (`/analytics/performance`), a partir de feedback de uso real:
  - **Volume Semanal por Grupo Muscular**: as barras já eram coloridas por status (verde/laranja/vermelho), mas a legenda de texto abaixo ficava sempre com a mesma cor neutra. Agora a legenda também fica colorida por status (verde = ok, laranja = sub-treinado, vermelho = overtraining), facilitando ver de relance onde está a performance.
  - **Correção real de bug**: a Tonelagem Total por sessão estava somando também os exercícios de aquecimento (Bloco 1) e volta à calma (Bloco 3), inflando o número — agora conta só o Bloco 2 (sessão principal), igual ao Volume Semanal. O gráfico também virou barras (uma por sessão, com o nome do treino no eixo), em vez de linha — mais fácil de comparar sessão a sessão.
  - **RPE Médio**: investigado a fundo — o cálculo já estava correto (média só das séries com RPE registrado). O "Sem dados" acontecia porque nenhuma execução real tinha sido registrada ainda (aparece só depois de "Registrar Execução" ou usar o Modo ao Vivo). A mensagem agora explica isso e o que fazer, e foi adicionado um gráfico de tendência do RPE médio ao longo do tempo (antes só existia um card com o valor da última sessão).
  - **Novo gráfico**: "Volume Semanal — Séries / Repetições / Carga por Grupo Muscular", complementar ao gráfico de séries efetivas já existente.
  - **Navegação**: link "⬅️ Dashboard" adicionado nos 3 gráficos que ainda não tinham nenhuma navegação (`/analytics/volume`, `/analytics/exercises`, `/analytics/muscles`) — antes só dava pra sair deles pelo botão voltar do navegador.
- **Correção crítica**: uma sessão anterior havia trocado a Groq pelo Ollama local (`qwen2.5:3b`) direto em `app/services/llm_service.py`, mas de um jeito quebrado — apagou funções (`structure_reference_table`, `parse_reference_and_generate`, etc.) que `app/routers/extraction.py` ainda importava, e não adicionou o pacote `ollama` ao `requirements.txt`. Resultado: o app inteiro falhava ao subir com `ImportError: cannot import name 'parse_reference_and_generate'`. Restaurada a versão completa e funcional da Groq.
- **Nova funcionalidade**: Ollama (`qwen2.5:3b`, rodando localmente) integrado como **fallback** da Groq, não substituto — a Groq continua sendo a IA principal:
  - Nas 3 tarefas "pesadas" (extrair treino de imagem, gerar treino, gerar treino a partir de referência), se a Groq bater o limite diário de tokens (429), o app tenta automaticamente o Ollama local antes de mostrar erro; só cai no aviso de limite atingido se o Ollama também não responder (ex: não estiver rodando).
  - Na tarefa leve de estruturar a tabela de referência extraída por OCR, a prioridade é invertida: tenta o Ollama primeiro (evita gastar token da Groq numa tarefa simples), só usa a Groq se o Ollama não estiver disponível.
  - Se o pacote `ollama` não estiver instalado na máquina, o app detecta isso e continua funcionando normalmente só com a Groq (sem fallback local), sem quebrar nada.

## 2026-07-27

- **Correção**: revisão da implementação do Painel de KPIs de Performance (`/analytics/performance`, enviada em `f86fb3d`) contra a especificação e a lógica de treino/RPE, corrigindo 7 problemas:
  - Filtro por aluno (FR-011) estava totalmente ausente — os KPIs somavam treinos de todos os alunos juntos. Agora `GET /analytics/performance?student_name=...` filtra os dados e a página tem um seletor de aluno.
  - A fórmula de e1RM "ajustado por RPE" estava com a lógica invertida (reduzia o e1RM conforme o RPE subia). Corrigida para o ajuste padrão por RIR (repetições em reserva = 10 − RPE): quanto menor o RPE, maior o e1RM estimado, já que o atleta poderia ter feito mais reps até a falha.
  - RPE não registrado virava silenciosamente "RPE 8.0" em vez de indicar "sem dados" — agora o RPE médio de sessão e o semáforo de fadiga mostram claramente quando não há dados suficientes.
  - "Remada" (exercício de costas/puxada) estava sendo contado como posterior de coxa, distorcendo a razão Quadríceps/Posterior.
  - A janela "semanal" usava a data do último treino registrado em vez da data atual, podendo mascarar sub-treino.
  - O volume semanal somava séries de aquecimento/volta à calma junto com a sessão principal, em vez de só o bloco principal.
  - A faixa "saudável" do Push/Pull Ratio era simétrica (0.8–1.2); ajustada para refletir que puxar um pouco mais que empurrar (até 1.5x) é desejável.
  - Testes também corrigidos para seguir o padrão de isolamento do resto da suíte (fixture `scope="module"` sem `drop_all`) e ganharam um teste do endpoint HTTP com filtro por aluno.
- **Documentação**: especificação (`specs/003-performance-kpi-dashboard/spec.md`, seguindo o processo Speckit já usado no projeto) do Painel de KPIs de Performance para musculação/hipertrofia — e1RM por composto, volume semanal por grupo muscular com alertas, tonelagem por sessão, razões de equilíbrio muscular (Push/Pull, Quadríceps/Posterior), RPE médio de sessão e semáforo de fadiga/deload, tudo por aluno. Só a especificação (o quê/porquê); a implementação em código é um próximo passo separado.
- **Nova funcionalidade**: campo "Aluno" (tag leve, sem login) nos treinos — dá pra marcar de qual aluno é cada treino gerado (Dashboard, Extração de Referência, Upload de Imagem e criação manual), com autocomplete dos nomes já usados e filtro por aluno no Histórico (`/workouts/view`) e na listagem da API (`GET /workouts/?student_name=...`). Resolve o problema de todos os treinos ficarem misturados numa lista só quando o app é usado para mais de uma pessoa.
- **Nova funcionalidade**: catálogo de exercícios (`app/services/exercise_catalog.py`), com ~50 exercícios comuns mapeados por nome canônico e grupo muscular. Resolve dois problemas de uma vez:
  - **Sobrecarga progressiva**: antes, o histórico de progressão só era encontrado se o nome do exercício fosse EXATAMENTE igual ao de uma sessão anterior — então toda vez que a Extração de Referência substituía um exercício por um equivalente (comportamento correto dela), a progressão "zerava" e mostrava "primeira sessão" de novo. Agora o histórico é casado pela identidade canônica do exercício (ex: "Supino Reto" e "Supino Reto com Barra" continuam o mesmo histórico), mas continua tratando exercícios genuinamente diferentes (ex: Supino Reto vs Crucifixo) como históricos separados — já que cargas de exercícios diferentes não são comparáveis.
  - **Gráfico de Grupo Muscular**: antes usava um dicionário fixo de ~12 palavras-chave; agora usa o catálogo completo, com cobertura muito maior.
  - Bancos existentes são migrados automaticamente (novas colunas `muscle_group` em `exercises` e `canonical_name` em `workout_progress`), com fallback para o comportamento antigo em registros de histórico anteriores à migração.

## 2026-07-26

- **Melhoria**: instrução de concisão adicionada ao prompt principal (campos de texto livre como `notes` devem ser diretos, no máximo 2 frases curtas, sem repetir informação) — reduz tokens de saída em cada chamada. (Investigamos também o repositório `JuliusBrussee/caveman` a pedido do usuário: é um "skill" de prompt para agentes de codificação de IA reduzirem tokens de conversa, não uma biblioteca para chamadas de API dentro do app — mas o princípio de concisão foi aproveitado diretamente no prompt.)
- **Melhoria**: otimização de consumo de tokens da Groq — modelo menor/mais barato (`llama-3.1-8b-instant`) para a etapa de estruturação da tabela de referência (que consome de um orçamento diário separado do modelo principal), `max_tokens` calculado proporcionalmente ao número de treinos pedidos em vez de sempre reservar o teto máximo, cache da estruturação de referência (evita gastar token de novo em tentativas repetidas com o mesmo texto), e prompt principal enxugado. (Investigamos o repositório `rtk-ai/rtk` a pedido do usuário, mas ele é uma ferramenta Rust para reduzir tokens de saída de terminal em agentes de código — não se aplica a chamadas de API de LLM dentro do app, então implementamos as otimizações diretamente.)
- **Correção**: erro 429 da Groq (limite diário de tokens atingido) aparecia como um 500 genérico "Falha ao gerar treinos", sem explicar o motivo real. Agora o app detecta esse erro especificamente e mostra uma mensagem clara ("Limite diário de tokens da IA atingido, tente novamente em ~X min"), tanto no Dashboard quanto na Extração de Referência.
- **Documentação**: novo [EXEMPLOS_PROMPTS.md](EXEMPLOS_PROMPTS.md) com exemplos prontos de como preencher Especialização do Professor, Filosofia de Treino e Instruções Adicionais.
- **Correção**: a extração de referência estava gerando treinos praticamente idênticos à imagem enviada. Agora o prompt exige que cada exercício principal seja **substituído por um equivalente** (mesmo grupo muscular/padrão de movimento), gerando uma variação de verdade em vez de uma cópia.
- **Nova funcionalidade**: controle de "Volume em relação à referência" (manter / aumentar / diminuir) na página de Extração.
- **Melhoria**: botão de Baixar PDF adicionado direto nos resultados da página de Extração (antes só dava pra baixar pelo Histórico).
- **Correção**: revisão de texto extraído por OCR agora aparece como tabela editável (Exercício, Apelido, Equipamento, Acessório, Método), no mesmo formato da planilha de referência, em vez de um bloco de texto solto.
- **Correção**: a IA estava ignorando instruções específicas na página de Extração (ex: pedir "treino de peito" e receber exercícios de outros grupos musculares porque estavam na tabela de referência). O prompt agora deixa claro que a referência é um repertório/estilo, não uma lista obrigatória, e que as instruções do usuário definem quais exercícios entram.
- **Melhoria**: nova etapa de IA (`structure_reference_table`) organiza o texto bruto do OCR em linhas e corrige erros óbvios de leitura (ex: "5UPIN0" → "Supino") usando conhecimento de nomes comuns de exercício.
- **Documentação**: adicionada seção de Autor & Créditos no README (Argeu Rodrigues, com apoio do Claude Code).
- **Nova funcionalidade**: página de Extração de Referência (`/extraction`) — sobe uma foto de um modelo de treino já usado, revisa o texto extraído, e a IA remonta de 1 a 6 treinos com base nele, seguindo a metodologia de 3 blocos do app. Não altera o dashboard existente, só adiciona um link no rodapé.
- **Correção de bug**: upload de imagem no dashboard (`/image/upload`) sempre retornava erro 400 "Nenhum exercício encontrado", mesmo com OCR e IA funcionando corretamente. Causa: o código procurava a lista de exercícios no lugar errado da resposta da IA.
- **Nova funcionalidade**: Modo Treino ao Vivo — registro de treino em tempo real na academia, série a série (carga, repetições e RPE individuais), com cronômetro automático de descanso entre séries e checklist de progresso por exercício.

## 2026-07-24

- **Documentação**: README.md completo adicionado (visão geral, funcionalidades, stack, como rodar, licença).
- **Nova funcionalidade**: edição de prescrição antes de salvar, registro de execução real pós-treino (carga/reps/RPE), sobrecarga progressiva automática com trava de segurança de 120%, e exportação de ficha de treino em PDF.
- **Melhoria**: prompt da IA atualizado com glossário de métodos e arquiteturas de treino (drop-set, bi-set, rest-pause, etc.).

## 2026-07-22

- **Início do projeto**: primeira versão do Gym Tracker AI — geração de treinos com IA (Groq/Llama), leitura de fichas de treino por OCR (EasyOCR), dashboard web.
