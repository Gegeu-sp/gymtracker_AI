# Changelog

Histórico de tudo que foi feito no projeto, da atualização mais recente para a mais antiga. Este arquivo é atualizado sempre que uma mudança é enviada ao repositório.

## 2026-07-26

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
