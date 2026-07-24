# Tasks: Workout Execution & Editing Layer

**Input**: Design documents from `/specs/001-workout-execution-editing/`

**Prerequisites**: [plan.md](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/001-workout-execution-editing/plan.md), [spec.md](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/001-workout-execution-editing/spec.md), [research.md](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/001-workout-execution-editing/research.md), [data-model.md](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/001-workout-execution-editing/data-model.md), [contracts/api-contracts.json](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/001-workout-execution-editing/contracts/api-contracts.json)

---

## Phase 1: Backend - Schema de Banco de Dados & Schemas Pydantic

**Goal**: Adicionar suporte no banco de dados SQLite/SQLAlchemy e schemas Pydantic para armazenar edições pré-salvamento, execuções reais e histórico de evolução.

- [x] T001 [P] Adicionar colunas `actual_weight_kg`, `actual_reps`, `actual_rpe` e `is_edited` ao modelo `Exercise` em `app/models.py`
- [x] T002 [P] Criar o modelo SQLAlchemy `WorkoutProgress` para registro de histórico em `app/models.py`
- [x] T003 Atualizar o script de redefinição/migração do banco de dados em `reset_db.py`
- [x] T004 [P] Criar schemas Pydantic `ExerciseExecutionUpdate` (com validação de RPE 1-10) e `ExerciseProgressionOut` em `app/schemas.py`

**Checkpoint**: Banco de dados e schemas Pydantic prontos para persistência.

---

## Phase 2: Backend - Endpoints REST & Serviço de Progressão Automática

**Goal**: Implementar a lógica de negócios de sobrecarga progressiva (regra RPE < 8 com limite de segurança de 120%) e expor os endpoints REST de edição, registro e consulta.

- [x] T005 [P] Criar o serviço `app/services/progression_service.py` com o algoritmo de sobrecarga progressiva (+2.5kg/+5.0kg para RPE < 8) e trava de segurança de 120%
- [x] T006 Criar o endpoint `PUT /workouts/{id}/edit` em `app/routers/workout.py` para salvar ajustes manuais pré-treino
- [x] T007 Criar o endpoint `POST /workouts/{id}/log` em `app/routers/workout.py` para registrar a execução real e inserir histórico em `workout_progress`
- [x] T008 Criar o endpoint `GET /workouts/{id}/progression` em `app/routers/workout.py` delegando para `progression_service.py`

**Checkpoint**: Endpoints backend testáveis via Swagger / HTTP clients.

---

## Phase 3: Frontend - Interface do Usuário (Dashboard HTML/JS)

**Goal**: Atualizar o dashboard web com o modal de revisão pré-salvamento, formulário de registro pós-treino e visualização de sugestões de carga.

- [x] T009 [P] Adicionar botão "Editar" nos cards de prescrição e modal de edição interativo em `app/static/dashboard.html`
- [x] T010 Adicionar formulário de "Registro Pós-Treino" em `app/static/dashboard.html` para captura de carga real, repetições reais e RPE percebido
- [x] T011 Adicionar componente UI de "Verificar Progressão" em `app/static/dashboard.html` exibindo as recomendações calculadas e badges de trava de segurança

**Checkpoint**: Interface do usuário integrada e interativa.

---

## Phase 4: Validação, Testes & Trava de Segurança

**Goal**: Garantir a estabilidade da aplicação com testes automatizados unitários e de integração, além da verificação estrita da trava de segurança de 120%.

- [x] T012 [P] Criar testes unitários para a lógica de progressão e limite de 120% em `tests/test_progression.py`
- [x] T013 [P] Criar testes de integração para os endpoints `PUT /edit`, `POST /log` e `GET /progression` em `tests/test_execution_logging.py`
- [x] T014 Executar a suíte de testes `pytest` e realizar a validação ponta a ponta seguindo o `quickstart.md`

---

## Dependencies & Execution Order

1. **Phase 1 (Database & Models)** -> Pre-requisite for Phase 2 & Phase 3.
2. **Phase 2 (Backend Endpoints & Logic)** -> Depends on Phase 1 models and schemas.
3. **Phase 3 (Frontend UI)** -> Depends on Phase 2 endpoints.
4. **Phase 4 (Validation & Testing)** -> Validates Phase 1, 2, and 3.

---

## Parallel Opportunities

- **Phase 1**: T001, T002 e T004 podem ser executados em paralelo.
- **Phase 2**: T005 pode ser desenvolvido em paralelo aos schemas da Phase 1.
- **Phase 3**: T009 pode ser desenhado no HTML enquanto os endpoints da Phase 2 são finalizados.
- **Phase 4**: T012 e T013 podem ser implementados em paralelo.
