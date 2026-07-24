# Tasks: Workout PDF Export & Print Formatting (002-pdf-export)

**Input**: Design documents from `/specs/002-pdf-export/`

**Prerequisites**: [spec.md](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/002-pdf-export/spec.md)

---

## Phase 1: Frontend & CDN Integration

**Goal**: Integrar a biblioteca de exportação PDF e adicionar o botão "Baixar PDF" nos cards de treino da dashboard.

- [x] T001 [P] Adicionar a biblioteca `html2pdf.js` via CDN no `<head>` de `app/static/dashboard.html`
- [x] T002 Adicionar o botão `📄 Baixar PDF` na barra de ações dos cards de treino em `app/static/dashboard.html`
- [x] T003 Adicionar a classe CSS `.btn-info` para estilização responsiva do botão de download em `app/static/dashboard.html`

---

## Phase 2: PDF Layout & 3-Block Formatter Engine

**Goal**: Implementar o motor JavaScript de geração de PDF limpo, agrupando exercícios nos 3 blocos metodológicos e destacando observações do treinador.

- [x] T004 [P] Implementar a função `categorizeExercisesIntoBlocks(exercises)` para classificar exercícios em Bloco 1 (Aquecimento), Bloco 2 (Sessão Principal) e Bloco 3 (Volta à Calma) em `app/static/dashboard.html`
- [x] T005 Implementar a função `renderBlockTablePDF()` para renderizar tabelas limpas de fundo branco com colunas de Prescrição, Carga e espaço para Anotação de Execução Real em `app/static/dashboard.html`
- [x] T006 Implementar a função `downloadWorkoutPDF(workoutId)` com suporte a busca de dados do treino, renderização A4, destaque de observações de risco (`notes`) e fallback para impressão da janela em `app/static/dashboard.html`

---

## Phase 3: Servidor & Visualização HTML Secundária

**Goal**: Adicionar suporte a exportação de PDF na rota `/workouts/view` do backend.

- [x] T007 Adicionar o script `html2pdf.js` e o botão `📄 Baixar PDF` na rota `/workouts/view` em `app/routers/workout.py`
- [x] T008 Integrar o motor `downloadWorkoutPDF` na página HTML de histórico em `app/routers/workout.py`

---

## Phase 4: Validação & Testes Automatizados

**Goal**: Garantir a estabilidade da exportação e formatação através de testes automatizados.

- [x] T009 [P] Criar o arquivo de teste `tests/test_pdf_export.py` para validar endpoints, scripts CDN e elementos HTML de PDF
- [x] T010 Executar a suíte completa de testes `pytest` garantindo 100% de aprovação (9/9 testes passados)

---

## Dependencies & Execution Order

1. **Phase 1 (Frontend & CDN Integration)** -> Pre-requisite for Phase 2.
2. **Phase 2 (PDF Layout & Formatter Engine)** -> Depends on Phase 1 script CDN.
3. **Phase 3 (Server HTML View)** -> Mirrors Phase 1 & 2 capability in backend HTML view.
4. **Phase 4 (Validation & Testing)** -> Validates Phase 1, 2, and 3.

---

## Parallel Opportunities

- **Phase 1**: T001 e T003 podem ser executados em paralelo.
- **Phase 2**: T004 pode ser implementado em paralelo à estrutura HTML de T005.
- **Phase 4**: T009 pode ser executado enquanto a validação final de T010 é concluída.
