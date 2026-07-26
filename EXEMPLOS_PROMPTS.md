# Exemplos de Comandos (Prompts) — Gym Tracker AI

Guia com exemplos prontos de como preencher os campos **Especialização do Professor**, **Filosofia de Treino** e **Instruções Adicionais** — tanto no formulário "Gerar com IA" do Dashboard quanto na página de [Extração de Referência](app/static/extraction.html) (`/extraction`).

Esses três campos alimentam o prompt que é enviado para a IA (Groq/Llama-3.3-70B) em `app/services/llm_service.py`. Quanto mais claro e específico o texto, melhor o resultado — principalmente em **Instruções Adicionais**, que tem **prioridade máxima** sobre tudo o mais (inclusive sobre os exercícios da tabela de referência, na página de Extração).

---

## 🧑‍🏫 Especialização do Professor

Descreve a área de atuação/expertise do professor. Influencia o tom e o tipo de exercício escolhido.

- `Hipertrofia e ganho de força para atletas amadores`
- `Reabilitação pós-lesão de joelho e ombro`
- `CrossFit e treinamento funcional de alta intensidade`
- `Emagrecimento e condicionamento físico para iniciantes`
- `Powerlifting (supino, agachamento, terra)`
- `Treinamento para idosos com foco em mobilidade e segurança`

---

## 📖 Filosofia de Treino

Descreve a abordagem/metodologia geral que o professor segue. Afeta como os exercícios são estruturados (cadência, técnica, ordem).

- `Foco em controle excêntrico e conexão mente-músculo, sem pressa na execução`
- `Priorizar exercícios compostos multiarticulares antes dos isolados`
- `Treinos curtos e intensos, direto ao ponto, sem enrolação`
- `Progressão linear de carga a cada treino, sempre testando o limite com segurança`
- `Variação constante de estímulo (nunca repetir a mesma sequência de exercícios)`
- `Treino baseado em RPE (percepção de esforço), não em porcentagem fixa de carga`

---

## ⚠️ Instruções Adicionais (o campo mais importante)

É aqui que você manda o pedido específico. Este campo tem **prioridade sobre tudo**: se você pedir algo aqui, a IA precisa seguir isso mesmo que contrarie o "padrão" ou a tabela de referência usada na Extração.

### Focar em um grupo muscular / tipo de treino
- `Quero um treino de peito e tríceps`
- `Treino focado só em posterior de coxa e glúteo`
- `Treino de corpo inteiro (full body), sem dividir por grupo muscular`
- `Só membros superiores hoje`

### Restringir ou excluir exercícios
- `Sem agachamento livre, tenho dor no joelho`
- `Evite qualquer exercício com salto ou impacto`
- `Não usar máquinas, só peso livre (barra, halter, peso corporal)`
- `Sem exercícios que exijam deitar no chão`

### Controlar volume/intensidade (fora da Extração, que já tem campo próprio para isso)
- `Aumente a carga em relação ao treino anterior, estou pronto para evoluir`
- `Reduza o volume esta semana, é semana de deload`
- `Quero só 4 exercícios no treino principal, sem contar aquecimento`
- `Treino mais longo, com 8 a 10 exercícios`

### Pedir troca/substituição pontual (útil na página de Extração)
- `Troque o exercício de ombro por algo que não force a articulação`
- `No lugar de levantamento terra, use um exercício mais seguro para as costas`
- `Substitua qualquer exercício de perna por variações que não usem a máquina smith`

### Combinações (pode juntar tudo na mesma instrução)
- `Treino de peito e tríceps, sem supino reto (uso banco inclinado só), e aumente 1 série em cada exercício`
- `Corpo inteiro, sem impacto, priorizando exercícios com halteres, treino curto (30-40min)`

---

## 💡 Dicas gerais

- Seja específico: `"treino de peito"` funciona melhor que `"treino bom"`.
- Pode citar lesões/limitações — a IA usa isso para gerar alertas de risco no campo de observações do treino.
- Na página de Extração de Referência, use este campo para dizer **o que manter e o que mudar** em relação à imagem enviada — ele tem prioridade sobre a tabela extraída (ver regra em `app/services/llm_service.py::parse_reference_and_generate`).
- Se o resultado não vier como esperado, tente reescrever a instrução de forma mais direta e objetiva — frases muito longas ou vagas tendem a ser menos seguidas à risca pela IA.
