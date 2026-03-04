---
description:
  Analyze a task and determine whether it is a good fit for the Haiku model
  (claude-haiku-4-5-20251001) or requires Sonnet. When invoked with a task
  argument, assess that specific task. When invoked with no argument, print
  the full classification reference card.
---

# Model Router — Haiku vs. Sonnet

Use this skill to decide whether a task warrants the Haiku model before
switching models. Follow the steps below in order.

---

## Step 1 — Read the Input

Check whether the user provided an argument when invoking the skill.

- **With argument** (e.g., `/use-haiku "write a commit message"`): treat the
  argument text as the task to analyze. Go to Step 2.
- **No argument** (bare `/use-haiku`): skip to Step 4 and print the full
  reference card instead of a recommendation.

---

## Step 2 — Classify the Task

Evaluate the task against the two lists below. Use your judgment — tasks may
not match a category word-for-word, so reason about the underlying complexity.

### Good fits for Haiku

These tasks are fast, self-contained, and do not require deep cross-file
reasoning. Haiku handles them reliably at lower cost and higher speed.

- Simple code edits: renaming variables, fixing typos, reformatting blocks
- Reading and summarizing a single file or a short code section
- Answering factual or lookup questions (what does X option do, what is Y flag)
- Generating boilerplate or repetitive code (CRUD stubs, config files, test fixtures)
- Writing commit messages
- Simple grep or search tasks (find all usages of X, list all TODO comments)
- Translating or reformatting data (JSON to CSV, camelCase to snake_case, etc.)
- Writing or editing short text: email drafts, code comments, label names,
  PR descriptions for small changes
- Extracting specific information from a file (list all function names, show
  all imports)

### Not a good fit for Haiku — use Sonnet

These tasks require sustained reasoning, broad code context, or nuanced
judgment that Haiku may handle inconsistently.

- Complex architectural decisions (how should this system be restructured,
  what is the right data model for X)
- Multi-file refactors that require understanding how components relate across
  the codebase
- Debugging hard or ambiguous errors where the root cause is not obvious
- Long reasoning chains or tasks requiring step-by-step inference across
  many pieces of context
- Anything requiring deep understanding of code spread across many files
- Security reviews, performance profiling, or root cause analysis
- Designing new systems, writing technical specs, or evaluating trade-offs

---

## Step 3 — Print the Recommendation

After classifying, output a recommendation using exactly this format.

### If the task is a good fit for Haiku

```
USE HAIKU

Reason: [one sentence explaining why this task is simple/self-contained enough
for Haiku — be specific about what makes it a good fit]

To switch models in Claude Code, run:
  /model claude-haiku-4-5-20251001
```

### If the task requires Sonnet

```
USE SONNET

Reason: [one sentence explaining why this task needs Sonnet — name the specific
complexity that disqualifies Haiku, e.g., "requires reasoning across many files"
or "involves an ambiguous architectural decision"]
```

Do not add disclaimers, caveats, or extra paragraphs. The output must be
short and scannable.

---

## Step 4 — Reference Card (no-argument mode only)

When `/use-haiku` is invoked with no argument, skip Steps 2 and 3 and print
the following reference card verbatim. Do not add extra commentary.

```
MODEL ROUTING REFERENCE — Haiku vs. Sonnet

USE HAIKU (claude-haiku-4-5-20251001) for:
  - Simple code edits: renames, reformatting, typo fixes
  - Reading and summarizing a single file
  - Factual/lookup questions
  - Boilerplate and repetitive code generation
  - Writing commit messages
  - Simple grep/search tasks
  - Data translation: JSON, CSV, case conversion
  - Short text: emails, comments, labels, small PR descriptions

USE SONNET for:
  - Complex architectural decisions
  - Multi-file refactors
  - Debugging hard or ambiguous errors
  - Long reasoning chains
  - Deep cross-file code understanding
  - Security reviews or performance root cause analysis
  - Designing new systems or evaluating trade-offs

To switch to Haiku in Claude Code:
  /model claude-haiku-4-5-20251001

To switch back to Sonnet:
  /model claude-sonnet-4-6
```

---

## Trigger

Invoke this skill by typing:

```
/use-haiku
```

Or pass a task description as an argument to get a specific recommendation:

```
/use-haiku "write a commit message for this diff"
/use-haiku "refactor the auth module to support OAuth2"
/use-haiku "rename all instances of user_id to account_id in this file"
```
