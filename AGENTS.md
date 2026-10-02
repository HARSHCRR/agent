# Agent Guidelines: Autonomous & Proactive Execution

## Execution Modality & Permissions
- **Proactive Command Execution**: Execute terminal commands, environment management, and script executions directly and proactively. Do not pause between steps to ask for permission or prompt the user for routine commands unless an action is irreversible/destructive (e.g., recursive deletion of unexpected directories or wiping databases).
- **End-to-End Task Ownership**: When a goal or task is requested, take full ownership:
  1. Inspect existing files and configs.
  2. Run setup or installation commands.
  3. Execute code and tests.
  4. Inspect logs and terminal outputs.
  5. Automatically diagnose and self-heal any errors or stack traces without requiring user intervention.
- **Verification First**: Always verify that a command or script succeeded before concluding a task. If output contains errors, immediately iterate and fix them.
