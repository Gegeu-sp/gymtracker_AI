# Feature Specification: Painel de KPIs de Performance (Musculação e Hipertrofia)

**Feature Branch**: `003-performance-kpi-dashboard`

**Created**: 2026-07-27

**Status**: Draft

**Input**: User description: "Adicionar um Painel de KPIs de Performance focado em Musculação e Hipertrofia ao Gym Tracker AI existente. O painel deve calcular e exibir automaticamente: (1) Gráfico de tendência do e1RM (1RM estimado via Epley ajustado por RPE) para os principais compostos (Supino, Agachamento, Terra); (2) Volume Semanal por Grupo Muscular (total de séries efetivas por músculo), com alertas visuais se estiver abaixo de 10 (sub-treinado) ou acima de 25 (junk volume/overtraining); (3) Tonelagem Total (Volume Load = sets x reps x kg) por sessão; (4) Razões de Equilíbrio Muscular para prevenção de lesões: Push/Pull Ratio (Empurrar vs Puxar) e Quadríceps/Posteriores, com alertas de desequilíbrio; (5) RPE Médio da Sessão para garantir que a intensidade está na zona de hipertrofia (RPE 7-9); (6) Semáforo de Fadiga (Deload Automático): acionar alerta vermelho se o e1RM estagnar ou o RPE médio subir progressivamente com a mesma carga, sugerindo redução de volume. O painel deve aparecer como uma nova aba /analytics/performance no dashboard, usando Plotly para os gráficos e mantendo a estrutura de dados existente."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Acompanhar evolução de força nos grandes compostos (Priority: P1)

Como praticante de musculação focado em hipertrofia/força, quero ver a tendência do meu 1RM estimado (e1RM) para Supino, Agachamento e Levantamento Terra ao longo do tempo, para saber se minha força nesses movimentos está realmente evoluindo ou estagnada.

**Why this priority**: É o indicador mais direto de progresso de longo prazo nos movimentos que mais importam; sem ele, o usuário não sabe se o programa está funcionando.

**Independent Test**: Pode ser testado de forma isolada acessando o painel após ter pelo menos duas sessões registradas com carga/reps/RPE para um exercício composto reconhecido, e verificando que o gráfico de e1RM aparece com pelo menos dois pontos.

**Acceptance Scenarios**:

1. **Given** o usuário registrou execuções reais de Supino em pelo menos duas datas diferentes, **When** ele abre o painel de performance para esse aluno, **Then** vê um gráfico de linha com o e1RM estimado de Supino ao longo do tempo.
2. **Given** o usuário nunca registrou execução real de nenhum dos três compostos monitorados, **When** ele abre o painel, **Then** vê uma mensagem clara de que ainda não há dados suficientes, em vez de um gráfico vazio ou erro.

---

### User Story 2 - Monitorar volume de treino por grupo muscular (Priority: P1)

Como praticante, quero ver quantas séries efetivas fiz por grupo muscular na semana, com aviso quando estou treinando de menos ou de mais, para ajustar meu volume e evitar tanto estagnação quanto overtraining.

**Why this priority**: Volume semanal por grupo muscular é a principal alavanca de hipertrofia; sem visibilidade disso o usuário não consegue autorregular o treino.

**Independent Test**: Testável de forma independente registrando treinos com exercícios de um grupo muscular reconhecido ao longo de uma semana e conferindo que a contagem de séries e o alerta aparecem corretamente.

**Acceptance Scenarios**:

1. **Given** o usuário fez 8 séries de exercícios de peito na semana corrente, **When** ele vê o painel, **Then** o grupo "Peito" aparece com contagem 8 e um alerta visual de volume abaixo do recomendado (menor que 10).
2. **Given** o usuário fez 28 séries de um grupo muscular na semana, **When** ele vê o painel, **Then** esse grupo aparece com alerta visual de volume acima do recomendado (maior que 25).
3. **Given** o usuário fez entre 10 e 25 séries de um grupo na semana, **When** ele vê o painel, **Then** esse grupo aparece sem alerta (dentro da faixa considerada adequada).

---

### User Story 3 - Avaliar equilíbrio muscular e risco de lesão (Priority: P2)

Como praticante, quero ver a proporção entre exercícios de empurrar e puxar, e entre quadríceps e posterior de coxa, para identificar desequilíbrios que aumentam risco de lesão antes que eles se tornem um problema.

**Why this priority**: Previne lesões de médio prazo, mas depende de histórico acumulado (menos urgente no primeiro uso do que os KPIs de progresso e volume).

**Independent Test**: Testável registrando exercícios classificados como "empurrar", "puxar", "quadríceps" e "posterior de coxa" e conferindo que as razões calculadas e os alertas de desequilíbrio batem com o volume registrado.

**Acceptance Scenarios**:

1. **Given** o volume de séries de puxar é menos da metade do volume de empurrar no período analisado, **When** o usuário vê o painel, **Then** aparece um alerta de desequilíbrio Push/Pull.
2. **Given** os volumes de quadríceps e posterior de coxa estão numa proporção considerada saudável, **When** o usuário vê o painel, **Then** a razão aparece sem alerta.

---

### User Story 4 - Confirmar que a intensidade está na zona de hipertrofia (Priority: P2)

Como praticante, quero ver o RPE médio das minhas sessões, para saber se estou treinando com intensidade suficiente (nem muito leve, nem sempre até a falha).

**Why this priority**: Garante que o volume contado nos outros KPIs está sendo feito com intensidade eficaz — volume alto com RPE baixo demais tem efeito de hipertrofia reduzido.

**Independent Test**: Testável registrando execuções com RPE variado e conferindo que a média por sessão e a sinalização de zona ideal batem com os valores registrados.

**Acceptance Scenarios**:

1. **Given** o usuário registrou execuções com RPE médio de sessão entre 7 e 9, **When** ele vê o painel, **Then** a sessão aparece marcada como dentro da zona de hipertrofia.
2. **Given** o RPE médio de uma sessão está fora da faixa 7-9, **When** o usuário vê o painel, **Then** a sessão aparece destacada como fora da zona ideal.

---

### User Story 5 - Ser avisado quando é hora de reduzir o volume (deload) (Priority: P3)

Como praticante, quero um alerta automático quando meu progresso estagna e meu esforço percebido está subindo com a mesma carga, para saber quando devo reduzir o volume antes de acumular fadiga demais.

**Why this priority**: É o KPI mais avançado/derivado dos demais (depende da tendência histórica de e1RM e RPE já calculada nas stories anteriores), então é a última camada a ser entregue.

**Independent Test**: Testável simulando um histórico onde a carga se mantém igual em sessões consecutivas de um mesmo exercício enquanto o RPE relatado sobe, e conferindo que o alerta aparece; e um histórico saudável onde o alerta não aparece.

**Acceptance Scenarios**:

1. **Given** o e1RM de um exercício composto está estagnado (sem melhora) nas últimas sessões e o RPE médio está subindo com carga equivalente, **When** o usuário vê o painel, **Then** aparece um alerta vermelho de fadiga sugerindo redução de volume.
2. **Given** o e1RM está evoluindo normalmente e o RPE está estável, **When** o usuário vê o painel, **Then** nenhum alerta de fadiga é mostrado.

### Edge Cases

- O que acontece quando o usuário tem menos de duas sessões registradas para um exercício? O sistema deve mostrar "dados insuficientes" para aquele KPI específico, sem quebrar a página nem esconder os outros KPIs que já têm dados suficientes.
- Como o sistema lida com um exercício cujo grupo muscular não é reconhecido pelo catálogo (cai em "Outros")? Ele deve ser contabilizado em "Outros" no volume por grupo, mas não deve contar para Push/Pull nem Quadríceps/Posterior (que exigem classificação de padrão de movimento reconhecida).
- O que acontece se o usuário nunca registrou RPE em nenhuma execução? O RPE médio de sessão e o semáforo de fadiga (que dependem de RPE) devem indicar "sem dados" em vez de assumir um valor default silenciosamente.
- Como o painel trata treinos sem aluno marcado (treinos antigos, de antes da feature de Aluno existir)? Devem aparecer agrupados sob uma opção "Sem aluno / Geral" no seletor, para não ficarem invisíveis nem misturados com um aluno específico.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE calcular e exibir a tendência do 1RM estimado (e1RM) ao longo do tempo para Supino, Agachamento e Levantamento Terra (e variações reconhecidas desses movimentos), com base nas execuções reais registradas (carga, repetições e RPE).
- **FR-002**: O sistema DEVE calcular o volume semanal (número de séries efetivas) por grupo muscular, considerando apenas séries de treinos executados dentro dos últimos 7 dias corridos a partir da data atual.
- **FR-003**: O sistema DEVE exibir um alerta visual quando o volume semanal de um grupo muscular estiver abaixo de 10 séries (sub-treinado) ou acima de 25 séries (volume excessivo/overtraining).
- **FR-004**: O sistema DEVE calcular e exibir a tonelagem total (carga total movimentada: séries × repetições × carga) por sessão de treino.
- **FR-005**: O sistema DEVE calcular a razão entre volume de exercícios de "empurrar" e "puxar" (Push/Pull Ratio) e entre volume de exercícios de quadríceps e de posterior de coxa, e exibir um alerta de desequilíbrio quando essas razões estiverem fora de uma faixa saudável.
- **FR-006**: O sistema DEVE calcular e exibir o RPE médio de cada sessão de treino, sinalizando quando estiver fora da faixa de intensidade recomendada para hipertrofia (RPE 7 a 9).
- **FR-007**: O sistema DEVE exibir um alerta de fadiga ("semáforo") quando o e1RM de um exercício monitorado estiver estagnado (sem progresso) nas sessões mais recentes E o RPE médio associado a uma carga equivalente estiver subindo ao longo dessas sessões, sugerindo redução de volume.
- **FR-008**: O sistema DEVE indicar claramente, para cada KPI individual, quando não há dados suficientes para calculá-lo, em vez de exibir um gráfico vazio, um erro, ou um valor enganoso.
- **FR-009**: O painel DEVE ser acessível a partir do Dashboard/navegação existente do aplicativo, como uma seção própria dedicada a métricas de performance.
- **FR-010**: O sistema DEVE classificar cada exercício reconhecido em um padrão de movimento (empurrar, puxar, quadríceps-dominante, posterior-de-coxa-dominante ou nenhum desses) para viabilizar o cálculo das razões de equilíbrio muscular (FR-005).
- **FR-011**: O sistema DEVE permitir selecionar de qual aluno (ou "Sem aluno / Geral") os KPIs de performance serão calculados e exibidos, reaproveitando o mesmo conceito de aluno já usado no filtro do Histórico de treinos.

### Key Entities *(include if feature involves data)*

- **Estimativa de Força (e1RM)**: Uma força máxima estimada para um exercício composto específico, calculada a partir de uma execução real (carga, repetições, RPE) em uma data. Cada execução registrada de um exercício monitorado gera um ponto de e1RM.
- **Volume Semanal por Grupo Muscular**: Uma contagem de séries efetivas realizadas para um grupo muscular específico dentro de uma janela de 7 dias, junto com um estado (adequado, sub-treinado, ou excessivo).
- **Sessão de Treino**: Um treino executado em uma data, com uma tonelagem total e um RPE médio associados, calculados a partir das execuções reais registradas naquela sessão.
- **Razão de Equilíbrio Muscular**: Uma proporção entre o volume de dois padrões de movimento opostos ou complementares (empurrar/puxar, quadríceps/posterior), junto com um estado de equilíbrio ou desequilíbrio.
- **Padrão de Movimento**: Uma classificação de um exercício (empurrar, puxar, quadríceps-dominante, posterior-de-coxa-dominante), usada para agrupar exercícios nas razões de equilíbrio.
- **Alerta de Fadiga**: Um sinal derivado da combinação de estagnação de e1RM e aumento de RPE percebido para uma carga equivalente ao longo de sessões recentes de um mesmo exercício.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário com histórico de pelo menos 2 sessões de um exercício composto monitorado consegue visualizar a tendência de e1RM desse exercício em menos de 5 segundos após abrir o painel.
- **SC-002**: 100% dos grupos musculares com séries registradas na semana corrente exibem sua contagem de volume e o estado de alerta correto (sub-treinado/adequado/excessivo) segundo os limites definidos.
- **SC-003**: Um usuário consegue identificar, sem precisar calcular nada manualmente, se sua última sessão de treino teve intensidade dentro da zona de hipertrofia (RPE 7-9).
- **SC-004**: Um usuário em tendência de estagnação (e1RM parado + RPE subindo com carga igual em pelo menos 3 sessões consecutivas do mesmo exercício) recebe o alerta de fadiga na primeira vez que abre o painel após essa condição se configurar.

## Assumptions

- O painel de performance analisa apenas execuções reais registradas (carga/reps/RPE efetivamente executados), não valores prescritos/planejados.
- "Séries efetivas" para o cálculo de volume semanal (FR-002/FR-003) são séries de exercícios do Bloco 2 (sessão principal), excluindo aquecimento e volta à calma — consistente com a metodologia de 3 blocos já usada no restante do aplicativo.
- A classificação de padrão de movimento (push/pull/quadríceps/posterior) é definida por exercício reconhecido no catálogo já existente; exercícios não reconhecidos ficam de fora das razões de equilíbrio, mas continuam contando no volume geral por grupo muscular.
- Os KPIs são calculados por aluno, com um seletor reaproveitando o conceito de Aluno já existente no aplicativo; treinos sem aluno marcado ficam agrupados sob "Sem aluno / Geral".
- As faixas numéricas fornecidas no pedido original (10/25 séries semanais, RPE 7-9) são adotadas como estão, sem validação adicional de literatura esportiva além do que já foi especificado.
