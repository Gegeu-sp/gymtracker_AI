# Implementation Plan: Workout Execution & Editing Layer

**Branch**: `001-workout-execution-editing` | **Date**: 2026-07-24 | **Spec**: [spec.md](file:///c:/Users/MUSCULA%C3%87%C3%83O/Documents/Teste/gym-tracker/specs/001-workout-execution-editing/spec.md)

**Input**: Feature specification from `/specs/001-workout-execution-editing/spec.md`

## Summary

Implement a pre-save editing modal and post-workout execution recording layer into the existing GymTracker AI web application. 
The backend (FastAPI + SQLite/SQLAlchemy) will be enhanced with `actual_weight_kg`, `actual_reps`, `actual_rpe`, and `is_edited` columns on the `exercises` table and a new `workout_progress` table. 
A progression calculation service will analyze historical execution logs to suggest optimal load increases for subsequent sessions (+2.5kg to +5.0kg when RPE < 8), enforced with a strict **120% max load safety cap**. 
The static HTML/JS dashboard will feature a pre-saving review modal and a post-workout execution entry form while preserving the 3-block structure (Warm-up, Main Session, Cool-down) and controlled method glossary.

---

## Technical Context

- **Language/Version**: Python 3.11+
- **Primary Dependencies**: FastAPI, SQLAlchemy, Pydantic v2, Uvicorn, Jinja2 / Static Files
- **Storage**: SQLite (`gym.db`) with SQLAlchemy ORM
- **Testing**: `pytest`, `httpx` (FastAPI TestClient)
- **Target Platform**: Web application (FastAPI backend + Vanilla JS/HTML Dashboard frontend)
- **Project Type**: Web Application (Backend REST API + Frontend SPA/Dashboard)
- **Performance Goals**: Sub-50ms REST API response times for execution logging and progression calculations
- **Constraints**: Enforce RPE strictly between 1.0 and 10.0; cap load suggestions at max 120% of previous execution load
- **Scale/Scope**: Gym workout management, execution tracking, and progressive overload history

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Modular FastAPI Architecture**:
  - Routers (`app/routers/workout.py`) will delegate execution logging and progressive overload calculations to `app/services/workout_service.py` and `app/services/progression_service.py`.
  - Models in `app/models.py` and schemas in `app/schemas.py`. No business logic inside HTTP handlers. -> **PASS**
- **II. AI & OCR Resilience**:
  - Pydantic validation schemas enforce valid execution payloads and RPE bounds prior to persistence. -> **PASS**
- **III. Database Integrity & Data Security**:
  - Explicit transaction management using SQLAlchemy sessions. Schema migration script provided in `reset_db.py`. -> **PASS**
- **IV. Test-Driven Quality & Verification**:
  - `pytest` suite covering pre-save edits, execution log validation, progression calculations, and safety caps. -> **PASS**
- **V. API Contracts & REST Standards**:
  - Standard REST verbs (`PUT /workouts/{id}/execution`, `GET /workouts/{id}/progression`) with structured Pydantic schemas. -> **PASS**

---

## Project Structure

### Documentation (this feature)

```text
specs/001-workout-execution-editing/
├── spec.md              # Feature specification
├── plan.md              # Implementation plan (this file)
├── research.md          # Phase 0 research & architectural decisions
├── data-model.md        # Phase 1 data models & entity definitions
├── quickstart.md        # Phase 1 test & validation guide
├── contracts/
│   └── api-contracts.json # Phase 1 OpenAPI REST specifications
└── checklists/
    └── requirements.md  # Spec quality checklist
```

### Source Code (repository root)

```text
app/
├── database.py
├── main.py
├── models.py            # Workout, Exercise, WorkoutProgress SQLAlchemy models
├── schemas.py           # ExerciseBase, ExerciseExecutionUpdate, ExerciseProgressionOut Pydantic schemas
├── models/ (or models.py)
├── routers/
│   ├── workout.py       # REST endpoints for workout CRUD, execution logging, progression suggestions
│   ├── image.py
│   └── analytics.py
├── services/
│   ├── workout_service.py     # Execution log persistence and DB operations
│   ├── progression_service.py # Progressive overload algorithm & 120% safety check
│   └── llm_service.py
└── static/
    └── dashboard.html   # Pre-save Edit Modal, Post-workout Execution Form, Progression UI

tests/
├── test_models.py
├── test_execution_logging.py
└── test_progression.py
```

**Structure Decision**: Monolithic single-repo Web Application with FastAPI backend (`app/`) and static HTML/JS frontend (`app/static/`).

---

## Phases & Execution Workflow

### Phase 0: Research & Architecture
- [x] Create `research.md` detailing DB schema extension, pre-save modal workflow, progression logic (+2.5kg/+5kg when RPE < 8), and 120% load cap safety gate.

### Phase 1: Design & Contracts
- [x] Create `data-model.md` defining `Exercise` model additions (`actual_weight_kg`, `actual_reps`, `actual_rpe`, `is_edited`) and new `WorkoutProgress` table.
- [x] Create `contracts/api-contracts.json` specifying REST endpoints (`PUT /workouts/{id}/execution`, `GET /workouts/{id}/progression`).
- [x] Create `quickstart.md` defining step-by-step verification and automated testing workflows.

### Phase 2: Implementation Tasks (Next Command: `/speckit-tasks`)
- Task 1: Update database models in `app/models.py` (`Exercise` columns and `WorkoutProgress` model) & update `reset_db.py`.
- Task 2: Add Pydantic validation schemas in `app/schemas.py` (`ExerciseExecutionUpdate`, `ExerciseProgressionOut`).
- Task 3: Create `app/services/progression_service.py` implementing progressive overload logic with RPE rules and 120% safety check.
- Task 4: Add routers in `app/routers/workout.py` for `PUT /workouts/{id}/execution` and `GET /workouts/{id}/progression`.
- Task 5: Expand `app/static/dashboard.html` with Pre-Save Review/Edit Modal and Post-Workout Execution Entry Form.
- Task 6: Write automated pytest test suite in `tests/` and verify all scenarios.
