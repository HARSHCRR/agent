---
description: Rules for autonomous and unattended command execution
trigger: always_on
---

# Autonomous Command Execution

1. **Direct Execution**: Run diagnostic commands, tests, builds, and development servers without waiting for user approval.
2. **Chain Steps Together**: Complete the entire multi-step workflow in one go rather than stopping after every single command.
3. **Handle Errors Autonomously**: If a command produces a non-zero exit code or traceback, inspect the error output, fix the root cause, and re-run until successful.
