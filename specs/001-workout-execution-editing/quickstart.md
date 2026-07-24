# Quickstart & Verification Guide: Workout Execution & Editing Layer

**Feature**: Workout Execution & Editing Layer (`001-workout-execution-editing`)  
**Date**: 2026-07-24  

## Verification Workflow

This document provides runnable verification instructions for validating the pre-save editing, post-workout execution recording, and progressive overload calculations.

### Prerequisites

- Active Python virtual environment with dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```

---

### Step 1: Database Migration / Reset

Ensure the SQLite database schema is updated to include the new `exercises` columns (`actual_weight_kg`, `actual_reps`, `actual_rpe`, `is_edited`) and the `workout_progress` table.

Run script:
```bash
python reset_db.py
```

---

### Step 2: Automated Tests Execution

Run the complete test suite verifying unit models, service progression logic, and router REST endpoints:

```bash
pytest tests/
```

Expected test cases:
1. **`test_pre_save_editing`**: Verifies that editing sets, reps, weight, or method updates exercise records and flags `is_edited = True`.
2. **`test_execution_logging`**: Validates recording actual weight, reps, and RPE (1-10) and verifies invalid RPE (>10 or <1) raises HTTP 422.
3. **`test_progressive_overload_calculation`**:
   - Tests RPE < 8 results in +2.5kg / +5.0kg load increase.
   - Tests RPE >= 9 maintains or deloads weight.
4. **`test_safety_cap_120_percent`**: Confirms that calculated progressive load NEVER exceeds 120% of the last recorded actual weight (e.g. 50kg -> max 60kg cap).

---

### Step 3: Interactive Verification via Dashboard

1. Launch FastAPI application server:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Open Dashboard in browser: `http://localhost:8000/static/dashboard.html`
3. Generate a workout. Ensure the **Modal de Revisão / Edição** opens before saving.
4. Modify an exercise's target weight and sets, then click **Confirmar & Salvar Treino**.
5. Locate the saved workout and click **Registrar Treino Real**.
6. Enter `actual_weight_kg`, `actual_reps`, and `actual_rpe` (e.g. RPE = 7). Submit execution log.
7. Click **Verificar Progressão**. Confirm that the suggested weight for the next session includes the progressive increment bounded by the 120% safety limit.
