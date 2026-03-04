# My-Workspace-TB-

See project instructions in `My-Workspace-TB-/CLAUDE.md`.

## Shell Recovery

If the Bash tool fails with "Path ... does not exist" (stale worktree CWD), fix it immediately: use the Write tool to create a `.keep` file at the missing path, then use `git -C /absolute/path` for all git commands. Do not ask the user — just fix it and continue.
