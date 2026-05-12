# Deduction Backend Testing

Run the automated suite and generate the report artifacts:

```powershell
python scripts/run_deduction_suite.py
```

This writes the following outputs to `services/backend/test_reports/` by default:

- `summary.md`
- `scenario_results.json`
- `scenario_final_rank.svg`
- `scenario_target_score.svg`
- `scenario_rank_progression.svg`

If you only want the tests without report generation:

```powershell
Set-Location services\backend
..\..\.venv\Scripts\python.exe -m unittest discover tests -v
```
