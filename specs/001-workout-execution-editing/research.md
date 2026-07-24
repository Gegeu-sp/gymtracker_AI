# Research & Architecture Decisions: Workout Execution & Editing Layer

**Feature**: Workout Execution & Editing Layer (`001-workout-execution-editing`)  
**Date**: 2026-07-24  

## Overview & Technical Choices

### 1. Database Schema Extension (SQLite / SQLAlchemy)

- **Decision**: Alter existing `exercises` table to store execution data and edit state directly on the exercise item, and create a dedicated `workout_progress` historical tracking table.
- **Rationale**:
  - `exercises` table columns:
    - `actual_weight_kg`: Float (nullable=True) - Real weight lifted during workout session.
    - `actual_reps`: Integer (nullable=True) - Real reps completed.
    - `actual_rpe`: Float (nullable=True) - Rating of Perceived Exertion (1.0 to 10.0).
    - `is_edited`: Boolean (default=False) - True if the user manually modified prescription parameters prior to saving.
  - `workout_progress` table columns:
    - `id`: Integer (primary_key=True)
    - `exercise_name`: String (indexed)
    - `date`: DateTime
    - `actual_weight_kg`: Float
    - `actual_reps`: Integer
    - `actual_rpe`: Float
    - `suggested_weight_kg`: Float
- **Alternatives Considered**:
  - Creating a separate execution table for every single set. *Rejected*: Adds unnecessary complexity for MVP given workouts track total exercise-level summary metrics.

---

### 2. Pre-Saving Review & Edit Workflow

- **Decision**: The LLM workout generation flow returns a structured prescription payload to the frontend. The frontend presents an interactive modal showing the 3 blocks (Warm-up, Main Session, Cool-down) allowing user adjustments to `weight_kg`, `reps`, `sets`, and `method` (using controlled glossary) before sending a `POST /workouts/` request to persist the confirmed workout.
- **Rationale**: Keeps users in full control before database persistence and ensures `is_edited` is accurately tagged.

---

### 3. Execution Log & Progression Calculation Algorithm

- **Decision**: Provide an endpoint `PUT /workouts/{id}/execution` to update actual execution data, which automatically inserts historical entries into `workout_progress`. Provide `GET /workouts/{id}/progression` (or service call) to calculate next target load per exercise.
- **Progression Logic**:
  - Retrieve the last execution record for `exercise_name` from `workout_progress` or `exercises`.
  - Check `actual_rpe` and completed reps:
    - If `actual_rpe < 8.0` and `actual_reps >= target_reps`:
      - Increment load by +2.5 kg (isolation/upper) or +5.0 kg (compound/heavy).
    - If `8.0 <= actual_rpe <= 9.0`:
      - Maintain current load.
    - If `actual_rpe > 9.0` or `actual_reps < target_reps`:
      - Maintain or suggest -5% deload.
  - **Safety Gate**: The suggested weight MUST NEVER exceed `120%` (1.20x) of `last_actual_weight_kg`. If `suggested_weight_kg > last_actual_weight_kg * 1.20`, cap at `last_actual_weight_kg * 1.20`.

---

### 4. Controlled Glossary & 3-Block Structure Integrity

- **Decision**: Enforce method selection in frontend dropdowns and backend Pydantic schemas against a controlled glossary (e.g., `"Traditional"`, `"Drop-set"`, `"Rest-pause"`, `"Bi-set"`, `"Pyramid"`, `"Cluster"`). Retain 3 blocks (Warm-up, Main Session, Cool-down) in workout JSON structures.
