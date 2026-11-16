# Submission evidence

Save your screenshots here after running the Postman collection (see WINDOWS_SETUP_GUIDE.md, Step 11).
Evidence can only be captured on your machine, because it must show the live forecast from Open-Meteo
and answers from your local Ollama model.

| File name | Show | Postman request |
|---|---|---|
| `01_saved_trip.png` | `201` response with the saved trip | 1 (and 2 for the lookup) |
| `02_live_forecast.png` | Advisory with temperatures/rain and `tools_used` | 3 |
| `03_remembered_followup.png` | Follow-up answered about Jaipur without naming it, same `trip_id` | 4 |
| `04_failure_case.png` | Forecast unavailable / unknown city / `422` invalid dates | 7, 9 or 6 |
| `05_console_tool_calls.png` | uvicorn terminal with `assistant: tool call: ...` lines | any `/ask` |
