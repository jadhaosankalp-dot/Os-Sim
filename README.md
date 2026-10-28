# Scheduler Bench — CPU Scheduling Simulator

A Flask webpage that computes **FCFS**, **SJF (non-preemptive)**, and **Round Robin**
scheduling from process Arrival Time / Burst Time input, and shows Completion Time,
Turnaround Time, Waiting Time, per-algorithm averages, Gantt charts, and a side-by-side
comparison — all in a dark, colour-coded dashboard UI.

## Run it in VS Code

1. **Open the folder** — `File > Open Folder…` and select this `scheduler-bench` folder
   (do this, not just the single file, so the `.vscode` settings are picked up).

2. **Install the Python extension** (by Microsoft) if you don't already have it —
   VS Code will usually prompt you automatically when it sees `app.py`.

3. **Create a virtual environment** (recommended). Open a terminal in VS Code
   (`` Ctrl+` `` / `` Cmd+` ``) and run:

   ```bash
   python -m venv .venv
   ```

   VS Code will detect the new environment and may prompt "Select it as the workspace
   interpreter" — click **Yes**. If it doesn't ask, open the Command Palette
   (`Ctrl+Shift+P` / `Cmd+Shift+P`) → **Python: Select Interpreter** →
   choose `.venv`.

4. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

5. **Run it** — either:
   - Press **F5** (uses the included `.vscode/launch.json` debug config), or
   - Open the Command Palette → **Run Python File** with `app.py` active, or
   - From the terminal: `python app.py`

6. Open **http://localhost:8080** in your browser.

## Project structure

```
scheduler-bench/
├── app.py                  # Flask app — routes, scheduling algorithms, HTML rendering
├── requirements.txt        # Python dependencies (Flask)
├── .vscode/
│   ├── launch.json         # F5 debug configuration
│   └── settings.json       # Points VS Code at the .venv interpreter
└── README.md
```

## Notes

- Everything (scheduling logic + page rendering) lives in `app.py` — no templates
  folder or database needed.
- The Flask dev server auto-reloads on save when `FLASK_DEBUG=1` is set (already
  configured in `launch.json`).
- To change the port, edit the `app.run(...)` call at the bottom of `app.py`.
