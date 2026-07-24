# Feature Specification: Workout Execution & Editing Layer

**Feature Branch**: `001-workout-execution-editing`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "Adicionar uma camada de edição e registro de execução ao aplicativo existente. Atualmente, o sistema apenas gera e salva a prescrição final. A melhoria deve permitir que o usuário revise e edite manualmente os exercícios gerados antes de confirmar o salvamento no histórico, corrigindo qualquer ajuste fino necessário. Além disso, ao registrar um treino no histórico, o usuário deve poder inserir os dados reais que foram executados na academia (carga real utilizada, repetições reais completas e RPE percebido). O sistema deve usar esses dados reais registrados para calcular e sugerir automaticamente a progressão de carga na próxima prescrição do mesmo exercício, garantindo a sobrecarga progressiva."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Edição Manual da Prescrição Gerada (Priority: P1)

Como praticante de musculação, quero revisar e ajustar manualmente os exercícios, séries, repetições e cargas sugeridas imediatamente após a geração do treino, para que a prescrição final reflita exatamente minhas necessidades e restrições antes de ser confirmada.

**Why this priority**: É fundamental garantir que o usuário tenha controle total sobre a prescrição recomendada pelo sistema antes de iniciar a sessão ou registrá-la.

**Independent Test**: Pode ser testado gerando uma prescrição, alterando carga/repetições/exercício na tela de revisão e verificando se os dados salvos correspondem às alterações manuais.

**Acceptance Scenarios**:

1. **Given** um treino prescrito recém-gerado, **When** o usuário altera a carga sugerida de 50kg para 55kg e adiciona uma série, **Then** o sistema atualiza a prescrição exibida com os novos valores.
2. **Given** um treino na tela de revisão, **When** o usuário substitui ou remove um exercício da lista prescrita, **Then** o sistema atualiza a lista de exercícios preservando a ordem e salva a versão revisada.

---

### User Story 2 - Registro de Dados Reais de Execução (Priority: P1)

Como praticante de musculação, quero registrar a carga real utilizada, as repetições reais efetuadas e o RPE (Escala de Percepção de Esforço) ao finalizar cada exercício/treino, para manter um histórico preciso do meu desempenho na academia.

**Why this priority**: O registro de dados reais de execução é o insumo indispensável para medir a performance verdadeira e alimentar o algoritmo de sobrecarga progressiva.

**Independent Test**: Pode ser testado ao selecionar um treino prescrito, preencher os campos de execução real (carga real, repetições reais, RPE de 1 a 10) e confirmar o salvamento no histórico.

**Acceptance Scenarios**:

1. **Given** um treino em fase de execução/registro, **When** o usuário preenche a carga real exercida (ex: 60kg), repetições efetuadas (ex: 10 reps) e RPE (ex: 8), **Then** o sistema grava esses dados de execução associados ao histórico daquela sessão.
2. **Given** a tela de registro de execução, **When** o usuário insere um valor de RPE inválido (fora da faixa de 1 a 10), **Then** o sistema impede o salvamento e exige a correção do valor.

---

### User Story 3 - Sugestão Automática de Sobrecarga Progressiva (Priority: P2)

Como praticante de musculação, quero que o sistema sugira automaticamente a nova carga recomendada na próxima prescrição de um exercício com base nos dados de execução real anteriores (carga, repetições e RPE), garantindo evolução constante e segura.

**Why this priority**: A sobrecarga progressiva automatizada elimina a necessidade de cálculos manuais pelo usuário, orientando a evolução contínua de carga.

**Independent Test**: Pode ser testado registrando uma execução com RPE baixo/médio e repetições máximas concluídas, e em seguida solicitando uma nova prescrição para o mesmo exercício para verificar se a carga sugerida aumentou.

**Acceptance Scenarios**:

1. **Given** um histórico onde o usuário concluiu as repetições alvo com RPE <= 8, **When** uma nova prescrição contendo o mesmo exercício for gerada, **Then** o sistema sugere um incremento automático de carga para a próxima sessão.
2. **Given** um histórico onde o usuário registrou RPE 10 ou não atingiu as repetições mínimas alvo, **When** uma nova prescrição for gerada, **Then** o sistema sugere manter a carga atual ou realizar uma redução estratégica.

---

### Edge Cases

- O que acontece se o usuário registrar um treino para um exercício inédito sem histórico prévio de execução? O sistema utiliza a carga padrão recomendada pela prescrição inicial como linha de base.
- Como o sistema se comporta se o usuário interromper o treino e salvar apenas parte dos exercícios executados? Os exercícios não executados são marcados como não realizados e não afetam o cálculo de progressão.
- Como o sistema reage se o usuário tentar inserir valores negativos de carga ou repetições? O sistema valida a entrada de dados e recusa valores inválidos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir a edição manual de todos os parâmetros da prescrição (exercícios, séries, repetições alvo, carga sugerida e tempo de descanso) antes da confirmação final do treino.
- **FR-002**: O sistema DEVE disponibilizar uma interface de registro de execução onde o usuário insere a carga real utilizada, as repetições reais efetuadas por série e a percepção subjetiva de esforço (RPE na escala de 1 a 10).
- **FR-003**: O sistema DEVE persistir no histórico de treinos tanto a prescrição planejada quanto os dados reais de execução para fins de comparação e auditoria.
- **FR-004**: O sistema DEVE calcular automaticamente a sugestão de progressão de carga para futuras prescrições utilizando o histórico mais recente de execução real (carga real, repetições e RPE).
- **FR-005**: O sistema DEVE validar os dados de entrada no registro de execução, garantindo que carga e repetições sejam não-negativas e o RPE esteja estritamente no intervalo de 1 a 10.
- **FR-006**: O sistema DEVE manter a rastreabilidade da evolução da carga real ao longo do tempo por exercício e por usuário.

### Key Entities

- **Prescrição de Exercício (Workout Prescription Item)**: Representa o planejamento proposto pelo sistema ou editado pelo usuário. Atributos principais: exercício, séries planejadas, repetições alvo, carga recomendada inicial, tempo de descanso.
- **Registro de Execução de Exercício (Exercise Execution Log)**: Representa a realização prática de uma série/exercício na academia. Atributos principais: data/hora da execução, carga real utilizada, repetições reais completadas, RPE percebido (1-10), observações do usuário.
- **Métrica de Progressão de Carga (Progression Rule Result)**: Representa o cálculo derivado de sobrecarga progressiva para um exercício específico. Atributos principais: exercício, carga anterior, nova carga sugerida, fator de ajuste baseado em RPE e conclusão de metas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários conseguem revisar e aplicar ajustes manuais em uma prescrição gerada em menos de 60 segundos.
- **SC-002**: 100% dos treinos confirmados e registrados no histórico armazenam com precisão os dados de execução real (carga real, repetições reais e RPE).
- **SC-003**: 100% das novas prescrições geradas para exercícios que possuem histórico prévio aplicam a recomendação de sobrecarga progressiva baseada no RPE e repetições registradas.
- **SC-004**: Redução de zero erros de persistência de dados de execução através de validação estrita de entradas (RPE 1-10 e valores numéricos válidos).

## Assumptions

- A escala de RPE (Rating of Perceived Exertion) adotada é a escala de 1 a 10 amplamente utilizada no treinamento de força.
- Se o usuário optar por não editar a prescrição recomendada, os valores sugeridos são assumidos como padrão para o início da execução.
- O cálculo de progressão de carga assume incrementos padrão adequados ao tipo de exercício caso não haja configuração customizada.
