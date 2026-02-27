# Application Catalog

> Auto-generated on 2026-02-24 12:53 UTC | 24 applications
>
> Regenerate: `npm run catalog` or `python3 scripts/generate_app_catalog.py`

## Quick Reference

| App                                                                     | Language   | Deployment    | Last Updated | Description                                                                      |
| ----------------------------------------------------------------------- | ---------- | ------------- | ------------ | -------------------------------------------------------------------------------- |
| [amazon-ynab-reconciler](#amazon-ynab-reconciler)                       | Python     | AWS Lambda    | 2025-12-10   | An automated system that scrapes Amazon order history, intelligently matches ... |
| [autonomous-email-assistant](#autonomous-email-assistant)               | Node.js    | AWS Lambda    | 2025-12-10   | An intelligent, fully autonomous email management system built with Claude Co... |
| [brandon-family-calendar-reporting](#brandon-family-calendar-reporting) | Node.js    | Serverless    | 2025-12-09   | AWS Lambda function for automated calendar reporting                             |
| [credit-card-rewards-tracker](#credit-card-rewards-tracker)             | Python     | AWS Lambda    | 2025-12-09   | Track and optimize credit card rewards across multiple issuers.                  |
| [daily-ai-news-report](#daily-ai-news-report)                           | Python     | Local         | 2025-12-03   | Daily Ai News Report application                                                 |
| [factor75-meal-selector](#factor75-meal-selector)                       | Python     | AWS Lambda    |              | Automate your weekly Factor 75 meal selection with email-based interaction.      |
| [fireflies-meeting-notes](#fireflies-meeting-notes)                     | Python     | AWS Lambda    |              | Fireflies Meeting Notes application                                              |
| [gmail-email-actions](#gmail-email-actions)                             | Python     | AWS Lambda    |              | Gmail Email Actions application                                                  |
| [gmail-unread-digest](#gmail-unread-digest)                             | Python     | AWS Lambda    |              | Gmail Unread Digest application                                                  |
| [homeschool-events-gwinnett](#homeschool-events-gwinnett)               | Python     | AWS Lambda    | 2026-02-23   | Weekly automated digest of homeschooling events in Gwinnett County, GA.          |
| [jt-teaching-newsletter](#jt-teaching-newsletter)                       | Python     | AWS Lambda    | 2026-02-23   | Daily morning email with 2 Jesus' Teachings from Obsidian vault                  |
| [love-brittany-tracker](#love-brittany-tracker)                         | Python     | AWS Lambda    | 2025-12-03   | Intelligent relationship tracking automation that monitors relationship activ... |
| [love-kaelin-tracker](#love-kaelin-tracker)                             | Python     | Local         | 2025-12-03   | Intelligent father-daughter relationship and development tracking automation ... |
| [todoist-coding-digest](#todoist-coding-digest)                         | Python     | AWS Lambda    |              | Todoist Coding Digest application                                                |
| [todoist-daily-reminders](#todoist-daily-reminders)                     | Python     | AWS Lambda    | 2025-12-09   | Automated daily reminder creation for Todoist tasks.                             |
| [todoist-daily-reviewer](#todoist-daily-reviewer)                       | Node.js    | Script Deploy | 2025-12-03   | An AI-powered daily task review system that analyzes your high-priority Todoi... |
| [todoist-inbox-manager](#todoist-inbox-manager)                         | Python     | AWS Lambda    |              | Todoist Inbox Manager application                                                |
| [toggl-calendar-sync](#toggl-calendar-sync)                             | Python     | Local         | 2025-12-09   | Automatically synchronize your Toggl Track time entries to Google Calendar in... |
| [toggl-daily-productivity](#toggl-daily-productivity)                   | Python     | Local         | 2025-12-09   | Automated daily email reports showing your Toggl time tracking performance me... |
| [twilio-personal](#twilio-personal)                                     | Python     | Local         | 2025-12-03   | A comprehensive Python application for managing Twilio SMS operations for per... |
| [weekly-atlanta-news-report](#weekly-atlanta-news-report)               | Python     | AWS Lambda    | 2025-12-09   | Automated weekly news digest for Atlanta, GA.                                    |
| [weekly-budget-report](#weekly-budget-report)                           | Python     | AWS Lambda    | 2025-12-03   | Automated weekly budget reports delivered to your inbox every Saturday at 7pm... |
| [ynab-dashboard](#ynab-dashboard)                                       | TypeScript | Vercel        | 2025-12-10   | A Next.js web application for managing YNAB transactions with deep linking su... |
| [ynab-transaction-reviewer](#ynab-transaction-reviewer)                 | Python     | AWS Lambda    | 2026-02-23   | An intelligent daily email system that proactively pushes uncategorized YNAB ... |

## Summary

- **Total apps**: 24
- **Languages**: Node.js (3), Python (20), TypeScript (1)
- **Deployment**: AWS Lambda (16), Local (5), Script Deploy (1), Serverless (1),
  Vercel (1)
- **With README**: 16/24

## Detailed Entries

### amazon-ynab-reconciler

**An automated system that scrapes Amazon order history, intelligently matches
transactions with YNAB, and updates transaction memos with Amazon categorization
and item links.**

|                  |                                                             |
| ---------------- | ----------------------------------------------------------- |
| **Language**     | Python                                                      |
| **Deployment**   | AWS Lambda                                                  |
| **Last Updated** | 2025-12-10                                                  |
| **Entry Points** | `lambda_handler.py`, `src/reconciler_main.py`               |
| **Integrations** | Google APIs, Google Auth, HTTP/REST, TOTP/2FA, Web Scraping |
| **Source Files** | 28                                                          |
| **Config Files** | `.env`, `.env.example`, `config.yaml`                       |
| **Has README**   | Yes                                                         |
| **Has Tests**    | Yes                                                         |

**Key Dependencies**: `requests`, `pyyaml`, `python-dotenv`, `pyotp`,
`beautifulsoup4`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`,
`google-api-python-client`, `pytest` + 1 more

---

### autonomous-email-assistant

**An intelligent, fully autonomous email management system built with Claude
Code Max and GitHub Actions. Monitors Gmail inbox, classifies emails by priority
tier, handles routine tasks automatically...**

|                  |                                          |
| ---------------- | ---------------------------------------- |
| **Language**     | Node.js                                  |
| **Deployment**   | AWS Lambda                               |
| **Last Updated** | 2025-12-10                               |
| **Entry Points** | `lambda_handler.js`, `lambda_handler.py` |
| **Integrations** | Browser Automation, Google APIs          |
| **Source Files** | 0                                        |
| **Config Files** | `.env.example`, `Dockerfile.lambda`      |
| **Has README**   | Yes                                      |
| **Has Tests**    | Yes                                      |

**Key Dependencies**: `aws-sdk`, `axios`, `express`, `googleapis`, `playwright`,
`uuid`, `winston`, `@types/jest`, `jest`

---

### brandon-family-calendar-reporting

**AWS Lambda function for automated calendar reporting**

|                  |                                  |
| ---------------- | -------------------------------- |
| **Language**     | Node.js                          |
| **Deployment**   | Serverless                       |
| **Last Updated** | 2025-12-09                       |
| **Integrations** | AWS, Google APIs                 |
| **Source Files** | 0                                |
| **Config Files** | `.env.example`, `serverless.yml` |
| **Has README**   | No                               |
| **Has Tests**    | No                               |

**Key Dependencies**: `@aws-sdk/client-ses`, `@aws-sdk/client-ssm`,
`googleapis`, `moment-timezone`, `dotenv`, `open`

---

### credit-card-rewards-tracker

**Track and optimize credit card rewards across multiple issuers. Get weekly
email reports, CLI dashboard access, and intelligent recommendations for
maximizing your rewards.**

|                  |                                            |
| ---------------- | ------------------------------------------ |
| **Language**     | Python                                     |
| **Deployment**   | AWS Lambda                                 |
| **Last Updated** | 2025-12-09                                 |
| **Entry Points** | `lambda_handler.py`, `src/rewards_main.py` |
| **Integrations** | AWS, HTTP/REST, Jinja2 Templates, Rich CLI |
| **Source Files** | 7                                          |
| **Config Files** | `.env.example`, `config.yaml`              |
| **Has README**   | Yes                                        |
| **Has Tests**    | No                                         |

**Key Dependencies**: `pyyaml`, `python-dotenv`, `requests`, `rich`, `jinja2`,
`boto3`, `pytz`, `python-dateutil`

---

### daily-ai-news-report

**Daily Ai News Report application**

|                  |                                                           |
| ---------------- | --------------------------------------------------------- |
| **Language**     | Python                                                    |
| **Deployment**   | Local                                                     |
| **Last Updated** | 2025-12-03                                                |
| **Integrations** | AWS, HTTP/REST, Jinja2 Templates, RSS Feeds, Web Scraping |
| **Source Files** | 0                                                         |
| **Config Files** | `.env.example`                                            |
| **Has README**   | No                                                        |
| **Has Tests**    | No                                                        |

**Key Dependencies**: `feedparser`, `beautifulsoup4`, `requests`,
`python-dotenv`, `boto3`, `jinja2`, `PyYAML`, `pytest`, `pytest-mock`,
`pytest-cov` + 3 more

---

### factor75-meal-selector

**Automate your weekly Factor 75 meal selection with email-based interaction.**

|                  |                                                 |
| ---------------- | ----------------------------------------------- |
| **Language**     | Python                                          |
| **Deployment**   | AWS Lambda                                      |
| **Entry Points** | `lambda_handler.py`, `src/factor75_main.py`     |
| **Integrations** | AWS, Google APIs, Google Auth, Jinja2 Templates |
| **Source Files** | 8                                               |
| **Config Files** | `.env`, `.env.example`                          |
| **Has README**   | Yes                                             |
| **Has Tests**    | No                                              |

**Key Dependencies**: `boto3`, `google-api-python-client`,
`google-auth-oauthlib`, `google-auth-httplib2`, `python-dotenv`, `PyYAML`,
`pytz`, `Jinja2`, `python-dateutil`, `coloredlogs`

---

### fireflies-meeting-notes

**Fireflies Meeting Notes application**

|                  |                                              |
| ---------------- | -------------------------------------------- |
| **Language**     | Python                                       |
| **Deployment**   | AWS Lambda                                   |
| **Entry Points** | `lambda_handler.py`, `src/fireflies_main.py` |
| **Integrations** | AWS, HTTP/REST                               |
| **Source Files** | 7                                            |
| **Config Files** | `.env`, `.env.example`                       |
| **Has README**   | No                                           |
| **Has Tests**    | No                                           |

**Key Dependencies**: `requests`, `boto3`, `python-dotenv`

**Claude Code Sessions** (11 sessions):

- `2026-02-24` — Email Visual Redesign — Fireflies Meeting Notes
  (`claude --resume 15dc650c-05b7-4cb4-9689-3d6a56359f1d`)
- `2026-02-24` — Email Visual Polish — Fireflies Meeting Notes (Round 2)
  (`claude --resume 34d924d4-b04d-493a-a359-ae0e5c66e4ca`)
- `2026-02-24` — Fireflies Meeting Notes Email — Full Redesign
  (`claude --resume 6b93350b-d826-415e-b0ba-26a35db2c9c4`)
- `2026-02-24` — Backfill All Fireflies Recordings to S3
  (`claude --resume 73af5c46-3a31-4d3b-a7b9-6666065fcd1f`)
- `2026-02-24` — All Recordings Web Page — Fireflies Meeting Notes
  (`claude --resume 74e1f15b-90ca-4528-8491-1d1c9444cc7f`)
- `2026-02-24` — Deploy + Resend: Obsidian Note Fix
  (`claude --resume a734a4aa-b1ac-4082-84a0-59f3367cebc6`)
- `2026-02-24` — Obsidian Notes: AI Title + Full Transcript
  (`claude --resume aeea4065-4856-4e9b-add5-66129d87f868`)
- `2026-02-24` — Fix: Obsidian Save Button — Clipboard Fails on Mobile
  (`claude --resume b2195d66-493b-49d2-b3b8-14226d3601f2`)
- `2026-02-24` — Fix: Obsidian Note Naming + Click Latency
  (`claude --resume e5e59aaf-eaa2-48b4-bbb0-73746aba8026`)
- `2026-02-23` — Fireflies Meeting Notes Processor
  (`claude --resume 50c37044-2440-4ff7-8dab-d0d83a647b52`)
- `2026-02-23` — Fix Fireflies Email Template + Obsidian One-Click Save
  (`claude --resume e5ba9a74-d88f-4d25-a7cc-1b3242dcf0a3`)

---

### gmail-email-actions

**Gmail Email Actions application**

|                  |                                                      |
| ---------------- | ---------------------------------------------------- |
| **Language**     | Python                                               |
| **Deployment**   | AWS Lambda                                           |
| **Entry Points** | `src/email_actions_main.py`, `src/lambda_handler.py` |
| **Source Files** | 6                                                    |
| **Has README**   | No                                                   |
| **Has Tests**    | No                                                   |

**Claude Code Sessions** (26 sessions):

- `2026-02-24` — Add Split-Pane Inline Email Viewer to gmail-email-actions
  (`claude --resume 04d664ea-0f80-4715-8adb-b5c524342c69`)
- `2026-02-24` — Trash Previous YNAB Review Emails on New Send
  (`claude --resume 08fb7e0e-5f6c-4de7-9d41-379b66d45e5c`)
- `2026-02-24` — Improve List Row Readability (v4)
  (`claude --resume 158f0d20-4419-49e6-95f4-a15561b0c488`)
- `2026-02-24` — Restyle Coding Digest Email to Match Gmail Email Actions UI
  (`claude --resume 49839b13-a68b-44e4-80fb-c610651bc0e4`)
- `2026-02-24` — Fireflies Meeting Notes Email — Full Redesign
  (`claude --resume 6b93350b-d826-415e-b0ba-26a35db2c9c4`)
- `2026-02-24` — Polished Digest Email — Clean List UI (v2)
  (`claude --resume 6d0a85db-7365-444a-9d0b-c79fa60d25a0`)
- `2026-02-24` — All Recordings Web Page — Fireflies Meeting Notes
  (`claude --resume 74e1f15b-90ca-4528-8491-1d1c9444cc7f`)
- `2026-02-24` — Polish Email Digest — v5 Pill Buttons + De-clutter
  (`claude --resume 7c81b210-65e6-4326-a7d1-6b7866121a46`)
- `2026-02-24` — Combined Tabbed Gmail Inbox (Starred + Unread)
  (`claude --resume a4a48749-774f-4773-9b63-a18aef25c36a`)
- `2026-02-24` — Gmail Unread Digest — replicate starred-email automation for
  unread emails (`claude --resume a75c219c-7e6b-46de-9a45-7a5b8acd61ff`)
- `2026-02-24` — Add Todoist Tabs to Dashboard Container
  (`claude --resume bd460fc6-0e0d-489c-8fcc-d5f2a0445d75`)
- `2026-02-24` — Polished Header (v3)
  (`claude --resume dba94fc7-08fa-4004-b2d8-9403ba94b5d7`)
- `2026-02-24` — v6 — Plain-text titles + star emoji header
  (`claude --resume f1f5ac9f-b8e8-4877-876a-d2ecd638a605`)
- `2026-02-24` — Web digest page with one-click unstar
  (`claude --resume f49fe541-3461-48bb-8abe-cfcb11b80f06`)
- `2026-02-23` — Fireflies Meeting Notes Processor
  (`claude --resume 50c37044-2440-4ff7-8dab-d0d83a647b52`)
- `2026-02-23` — Rerun Button Placement + Visual Polish
  (`claude --resume 70f2d5e0-31c7-4957-b3b6-0e15b2b6fb11`)
- `2026-02-23` — Mobile-Friendly Digest Email Redesign
  (`claude --resume 8a9a3fb4-faa4-43da-8711-585eb371ba70`)
- `2026-02-23` — Render Email Content on Lambda Page (Bypass Gmail Deep-Link
  Limitation) (`claude --resume 9557f750-26f1-49c9-8ad8-7f811b1bccfd`)
- `2026-02-23` — update my fireflies app to no longer send this email but rather
  a detailed summary of notes via emai
  (`claude --resume d2eafe9f-c22a-426c-8f1b-166f788d20ed`)
- `2026-02-23` — Auto-Delete Previous Digest Emails When New Digest Is Sent
  (`claude --resume db31c9ed-b47f-41ad-aae3-a8eb7cda39a4`)
- `2026-02-23` — Fix Gmail Links on iOS via Lambda Redirect
  (`claude --resume f417f96d-856a-4bf8-a512-4118d973a942`)
- `2026-02-23` — Fix Buttons + Gmail Links + Title Rename
  (`claude --resume fd769bd2-d7b0-452d-9034-8a4eb596d18d`)
- `2026-02-22` — Gmail Email Actions — Digest Enhancements
  (`claude --resume 2bd3e26c-13a5-4f3b-a326-c831a8678b0c`)
- `2026-02-22` — Gmail Starred Email → Todoist + Daily Digest Automation
  (`claude --resume 34f4f709-e36f-4217-972a-8bed4cd84bd2`)
- `2026-02-22` — Todoist Coding Digest - Daily Email Automation
  (`claude --resume 73a49379-29e6-43ec-8c53-0f456fc53295`)
- `2026-02-22` — Digest Email Visual Redesign
  (`claude --resume 888ea415-dc47-4475-a825-5f7998b1873b`)

---

### gmail-unread-digest

**Gmail Unread Digest application**

|                  |                                           |
| ---------------- | ----------------------------------------- |
| **Language**     | Python                                    |
| **Deployment**   | AWS Lambda                                |
| **Entry Points** | `lambda_handler.py`, `src/unread_main.py` |
| **Integrations** | AWS, Google APIs, Google Auth, HTTP/REST  |
| **Source Files** | 4                                         |
| **Has README**   | No                                        |
| **Has Tests**    | No                                        |

**Key Dependencies**: `google-api-python-client`, `google-auth`,
`google-auth-oauthlib`, `google-auth-httplib2`, `requests`, `boto3`

**Claude Code Sessions** (5 sessions):

- `2026-02-24` — Add Split-Pane Inline Email Viewer to gmail-email-actions
  (`claude --resume 04d664ea-0f80-4715-8adb-b5c524342c69`)
- `2026-02-24` — Deploy Inline Email Viewer Changes to Lambda
  (`claude --resume 522633c1-93c3-4ffe-b326-0bf109c3820a`)
- `2026-02-24` — Remove Todoist from Gmail Unread Digest
  (`claude --resume 549522ea-30c0-4ada-ba03-bb43c6c84f93`)
- `2026-02-24` — Combined Tabbed Gmail Inbox (Starred + Unread)
  (`claude --resume a4a48749-774f-4773-9b63-a18aef25c36a`)
- `2026-02-24` — Gmail Unread Digest — replicate starred-email automation for
  unread emails (`claude --resume a75c219c-7e6b-46de-9a45-7a5b8acd61ff`)

---

### homeschool-events-gwinnett

**Weekly automated digest of homeschooling events in Gwinnett County, GA.
Searches using Perplexity AI and delivers styled HTML emails with one-click "Add
to Calendar" buttons.**

|                  |                                           |
| ---------------- | ----------------------------------------- |
| **Language**     | Python                                    |
| **Deployment**   | AWS Lambda                                |
| **Last Updated** | 2026-02-23                                |
| **Entry Points** | `lambda_handler.py`, `src/events_main.py` |
| **Integrations** | AWS, HTTP/REST, Web Scraping              |
| **Source Files** | 13                                        |
| **Config Files** | `.env`, `.env.example`, `config.yaml`     |
| **Has README**   | Yes                                       |
| **Has Tests**    | No                                        |

**Key Dependencies**: `requests`, `python-dateutil`, `pytz`, `PyYAML`,
`python-dotenv`, `boto3`, `beautifulsoup4`, `lxml`

**Claude Code Sessions** (7 sessions):

- `2026-02-24` — Add Gwinnett County Library as Event Source
  (`claude --resume 3b2dd4f1-5e7c-49ba-9ce5-c4cf93010b91`)
- `2026-02-24` — Filter Events by Drive-Time Radius from Zip 30019
  (`claude --resume 5aa8c665-52ba-40fe-9fd4-a4ef8a2e304e`)
- `2026-02-24` — Redesign Email Header — Bold & Modern Style
  (`claude --resume c675a1ef-1df3-4ad0-b0fc-adf89206b77e`)
- `2026-02-24` — Add Relevance Filter to Remove Non-Homeschool Events
  (`claude --resume cdf02e4f-9c0b-4d9f-b4b4-d8743cb3aea3`)
- `2026-02-24` — Refine Email Header — Remove Emoji, Clean Typographic Style
  (`claude --resume f2522ec2-b785-4edd-a762-4d6800819cb9`)
- `2026-02-23` — Filter Events to Gwinnett County Only
  (`claude --resume 87a4fd2c-d165-4ecf-a8a1-de9c9f45efff`)
- `2026-02-23` — Homeschool Events Gwinnett - Weekly Event Digest Automation
  (`claude --resume cf36fde7-bba4-49a0-bef7-5c7159d53f90`)

---

### jt-teaching-newsletter

**Daily morning email with 2 Jesus' Teachings from Obsidian vault**

|                  |                                             |
| ---------------- | ------------------------------------------- |
| **Language**     | Python                                      |
| **Deployment**   | AWS Lambda                                  |
| **Last Updated** | 2026-02-23                                  |
| **Entry Points** | `lambda_handler.py`, `src/teaching_main.py` |
| **Integrations** | AWS, Claude AI                              |
| **Source Files** | 7                                           |
| **Config Files** | `.env`, `.env.example`, `config.yaml`       |
| **Has README**   | No                                          |
| **Has Tests**    | No                                          |

**Key Dependencies**: `anthropic`, `boto3`, `python-dotenv`, `PyYAML`

**Claude Code Sessions** (7 sessions):

- `2026-02-24` — JT Teaching Newsletter — Quality Improvements
  (`claude --resume eb888ae2-010a-4eaa-abea-bda40507082e`)
- `2026-02-23` — Fix Missing Verses — JT Teaching Newsletter
  (`claude --resume 3ebb7e7d-b631-499c-93d4-048b790754c5`)
- `2026-02-23` — Fix Empty Verses — Today's Teachings (Feb 23)
  (`claude --resume 97081298-7af4-4193-be26-7271ccc69056`)
- `2026-02-23` — Homeschool Events Gwinnett - Weekly Event Digest Automation
  (`claude --resume cf36fde7-bba4-49a0-bef7-5c7159d53f90`)
- `2026-02-22` — Premium Email Redesign — JT Teaching Newsletter
  (`claude --resume 06df76fb-4c8a-4aec-9168-e42f2c5fc2b3`)
- `2026-02-22` — JT Teaching Newsletter
  (`claude --resume 7259b0bb-633e-4c8e-83d5-39860b9c940e`)
- `2026-02-22` — Populate 506 Stub Teaching Files with Guessed Verses
  (`claude --resume fd41664e-3279-4285-993e-10f93760b534`)

---

### love-brittany-tracker

**Intelligent relationship tracking automation that monitors relationship
activities and generates beautiful bi-weekly HTML email reports.**

|                  |                                                                |
| ---------------- | -------------------------------------------------------------- |
| **Language**     | Python                                                         |
| **Deployment**   | AWS Lambda                                                     |
| **Last Updated** | 2025-12-03                                                     |
| **Entry Points** | `lambda_handler.py`, `src/relationship_main.py`                |
| **Integrations** | Flask Web Server, Google APIs, Google Auth, HTTP/REST, Todoist |
| **Source Files** | 11                                                             |
| **Config Files** | `.env.example`, `config.yaml`, `Dockerfile.lambda`             |
| **Has README**   | Yes                                                            |
| **Has Tests**    | Yes                                                            |

**Key Dependencies**: `google-api-python-client`, `google-auth-httplib2`,
`google-auth-oauthlib`, `requests`, `Flask`, `PyYAML`, `python-dotenv`,
`python-dateutil`, `colorlog`, `schedule` + 6 more

**Claude Code Sessions** (1 sessions):

- `2026-02-23` — update my fireflies app to no longer send this email but rather
  a detailed summary of notes via emai
  (`claude --resume d2eafe9f-c22a-426c-8f1b-166f788d20ed`)

---

### love-kaelin-tracker

**Intelligent father-daughter relationship and development tracking automation
that monitors activities and generates beautiful weekly HTML email reports.**

|                  |                      |
| ---------------- | -------------------- |
| **Language**     | Python               |
| **Deployment**   | Local                |
| **Last Updated** | 2025-12-03           |
| **Entry Points** | `src/kaelin_main.py` |
| **Source Files** | 4                    |
| **Config Files** | `config.yaml`        |
| **Has README**   | Yes                  |
| **Has Tests**    | No                   |

---

### todoist-coding-digest

**Todoist Coding Digest application**

|                  |                                           |
| ---------------- | ----------------------------------------- |
| **Language**     | Python                                    |
| **Deployment**   | AWS Lambda                                |
| **Entry Points** | `lambda_handler.py`, `src/digest_main.py` |
| **Integrations** | AWS, HTTP/REST                            |
| **Source Files** | 5                                         |
| **Config Files** | `.env`, `.env.example`, `config.yaml`     |
| **Has README**   | No                                        |
| **Has Tests**    | No                                        |

**Key Dependencies**: `requests`, `pytz`, `PyYAML`, `python-dotenv`, `boto3`

**Claude Code Sessions** (3 sessions):

- `2026-02-24` — Restyle Coding Digest Email to Match Gmail Email Actions UI
  (`claude --resume 49839b13-a68b-44e4-80fb-c610651bc0e4`)
- `2026-02-23` — Homeschool Events Gwinnett - Weekly Event Digest Automation
  (`claude --resume cf36fde7-bba4-49a0-bef7-5c7159d53f90`)
- `2026-02-22` — Todoist Coding Digest - Daily Email Automation
  (`claude --resume 73a49379-29e6-43ec-8c53-0f456fc53295`)

---

### todoist-daily-reminders

**Automated daily reminder creation for Todoist tasks. Creates reminders at 8am,
11am, 4pm, and 7pm for all tasks that are due today and have the @commit
label.**

|                  |                                             |
| ---------------- | ------------------------------------------- |
| **Language**     | Python                                      |
| **Deployment**   | AWS Lambda                                  |
| **Last Updated** | 2025-12-09                                  |
| **Entry Points** | `lambda_handler.py`, `src/reminder_main.py` |
| **Integrations** | AWS, HTTP/REST                              |
| **Source Files** | 3                                           |
| **Has README**   | Yes                                         |
| **Has Tests**    | No                                          |

**Key Dependencies**: `requests`, `python-dateutil`, `pytz`, `boto3`

**Claude Code Sessions** (2 sessions):

- `2026-02-23` — update my fireflies app to no longer send this email but rather
  a detailed summary of notes via emai
  (`claude --resume d2eafe9f-c22a-426c-8f1b-166f788d20ed`)
- `2026-02-19` — 33dd2fcd-9e1
  (`claude --resume 33dd2fcd-9e1d-4650-a819-36435228faf9`)

---

### todoist-daily-reviewer

**An AI-powered daily task review system that analyzes your high-priority
Todoist tasks and sends you a beautiful email report with suggestions for which
tasks Claude can help you complete autonomously.**

|                  |                  |
| ---------------- | ---------------- |
| **Language**     | Node.js          |
| **Deployment**   | Script Deploy    |
| **Last Updated** | 2025-12-03       |
| **Entry Points** | `src/index.js`   |
| **Integrations** | AWS, Google APIs |
| **Source Files** | 7                |
| **Config Files** | `.env.example`   |
| **Has README**   | Yes              |
| **Has Tests**    | No               |

**Key Dependencies**: `@aws-sdk/client-ses`, `dotenv`, `googleapis`,
`googleapis-common`, `jest`

---

### todoist-inbox-manager

**Todoist Inbox Manager application**

|                  |                                          |
| ---------------- | ---------------------------------------- |
| **Language**     | Python                                   |
| **Deployment**   | AWS Lambda                               |
| **Entry Points** | `lambda_handler.py`, `src/inbox_main.py` |
| **Integrations** | AWS, HTTP/REST                           |
| **Source Files** | 3                                        |
| **Has README**   | No                                       |
| **Has Tests**    | No                                       |

**Key Dependencies**: `requests`, `pytz`, `boto3`

**Claude Code Sessions** (3 sessions):

- `2026-02-24` — Add Todoist Tabs to Dashboard Container
  (`claude --resume bd460fc6-0e0d-489c-8fcc-d5f2a0445d75`)
- `2026-02-23` — update my fireflies app to no longer send this email but rather
  a detailed summary of notes via emai
  (`claude --resume d2eafe9f-c22a-426c-8f1b-166f788d20ed`)
- `2026-02-19` — Todoist Inbox Manager Automation
  (`claude --resume 9b8bc592-e6ee-4f56-90e6-7ff629468248`)

---

### toggl-calendar-sync

**Automatically synchronize your Toggl Track time entries to Google Calendar in
real-time.**

|                  |                                                                |
| ---------------- | -------------------------------------------------------------- |
| **Language**     | Python                                                         |
| **Deployment**   | Local                                                          |
| **Last Updated** | 2025-12-09                                                     |
| **Entry Points** | `src/main.py`                                                  |
| **Integrations** | Flask Web Server, Google APIs, Google Auth, HTTP/REST, Todoist |
| **Source Files** | 6                                                              |
| **Config Files** | `.env.example`, `config.yaml`                                  |
| **Has README**   | Yes                                                            |
| **Has Tests**    | No                                                             |

**Key Dependencies**: `google-api-python-client`, `google-auth-httplib2`,
`google-auth-oauthlib`, `requests`, `Flask`, `PyYAML`, `python-dotenv`,
`python-dateutil`, `colorlog`, `schedule` + 6 more

---

### toggl-daily-productivity

**Automated daily email reports showing your Toggl time tracking performance
metrics.**

|                  |                               |
| ---------------- | ----------------------------- |
| **Language**     | Python                        |
| **Deployment**   | Local                         |
| **Last Updated** | 2025-12-09                    |
| **Entry Points** | `src/main.py`                 |
| **Integrations** | AWS, HTTP/REST                |
| **Source Files** | 7                             |
| **Config Files** | `.env.example`, `config.yaml` |
| **Has README**   | Yes                           |
| **Has Tests**    | No                            |

**Key Dependencies**: `requests`, `PyYAML`, `python-dotenv`, `python-dateutil`,
`pytz`, `schedule`, `boto3`, `colorlog`

---

### twilio-personal

**A comprehensive Python application for managing Twilio SMS operations for
personal use, including automated reminders, alerts, and bulk messaging
capabilities.**

|                  |                                 |
| ---------------- | ------------------------------- |
| **Language**     | Python                          |
| **Deployment**   | Local                           |
| **Last Updated** | 2025-12-03                      |
| **Integrations** | Click CLI, Rich CLI, Twilio SMS |
| **Source Files** | 4                               |
| **Config Files** | `.env`, `.env.example`          |
| **Has README**   | Yes                             |
| **Has Tests**    | No                              |

**Key Dependencies**: `twilio`, `python-dotenv`, `click`, `rich`, `pyyaml`

**Claude Code Sessions** (2 sessions):

- `2026-02-22` — '/Users/terrancebrandon/Desktop/Code Projects (Official)/My
  Workspace/My-Workspace-TB-/My-Workspace-
  (`claude --resume 0bebbe53-d7a3-4998-99ec-14c75c0121e6`)
- `2026-02-22` — Get Twilio Working via Toll-Free Number Verification
  (`claude --resume f46c79e7-ea08-4cb4-93c5-3eda51f4c91c`)

---

### weekly-atlanta-news-report

**Automated weekly news digest for Atlanta, GA. Aggregates local news from major
Atlanta news sources via RSS feeds and delivers a curated email report every
Friday at 6:30 PM EST.**

|                  |                                                           |
| ---------------- | --------------------------------------------------------- |
| **Language**     | Python                                                    |
| **Deployment**   | AWS Lambda                                                |
| **Last Updated** | 2025-12-09                                                |
| **Entry Points** | `lambda_handler.py`, `src/news_main.py`                   |
| **Integrations** | AWS, HTTP/REST, Jinja2 Templates, RSS Feeds, Web Scraping |
| **Source Files** | 6                                                         |
| **Config Files** | `.env.example`, `config.yaml`                             |
| **Has README**   | Yes                                                       |
| **Has Tests**    | Yes                                                       |

**Key Dependencies**: `feedparser`, `beautifulsoup4`, `requests`,
`python-dateutil`, `pytz`, `PyYAML`, `python-dotenv`, `jinja2`, `boto3`,
`pytest` + 6 more

**Claude Code Sessions** (1 sessions):

- `2026-02-23` — Homeschool Events Gwinnett - Weekly Event Digest Automation
  (`claude --resume cf36fde7-bba4-49a0-bef7-5c7159d53f90`)

---

### weekly-budget-report

**Automated weekly budget reports delivered to your inbox every Saturday at 7pm,
powered by YNAB transaction data and beautiful HTML email reports.**

|                  |                                                            |
| ---------------- | ---------------------------------------------------------- |
| **Language**     | Python                                                     |
| **Deployment**   | AWS Lambda                                                 |
| **Last Updated** | 2025-12-03                                                 |
| **Entry Points** | `lambda_handler.py`, `src/budget_main.py`                  |
| **Integrations** | AWS, Google APIs, Google Auth, HTTP/REST, Jinja2 Templates |
| **Source Files** | 6                                                          |
| **Config Files** | `.env.example`, `config.yaml`                              |
| **Has README**   | Yes                                                        |
| **Has Tests**    | Yes                                                        |

**Key Dependencies**: `requests`, `python-dateutil`, `pytz`, `PyYAML`,
`python-dotenv`, `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`,
`google-api-python-client`, `jinja2` + 5 more

**Claude Code Sessions** (1 sessions):

- `2026-02-22` — Todoist Coding Digest - Daily Email Automation
  (`claude --resume 73a49379-29e6-43ec-8c53-0f456fc53295`)

---

### ynab-dashboard

**A Next.js web application for managing YNAB transactions with deep linking
support from email reports.**

|                  |                                                |
| ---------------- | ---------------------------------------------- |
| **Language**     | TypeScript                                     |
| **Deployment**   | Vercel                                         |
| **Last Updated** | 2025-12-10                                     |
| **Integrations** | Next.js, React, Tailwind CSS, Zustand State    |
| **Source Files** | 27                                             |
| **Config Files** | `.env.example`, `vercel.json`, `tsconfig.json` |
| **Has README**   | Yes                                            |
| **Has Tests**    | No                                             |

**Key Dependencies**: `@radix-ui/react-dialog`, `@radix-ui/react-dropdown-menu`,
`@radix-ui/react-label`, `@radix-ui/react-select`, `@radix-ui/react-slot`,
`@radix-ui/react-toast`, `@tanstack/query-sync-storage-persister`,
`@tanstack/react-query`, `@tanstack/react-query-persist-client`,
`class-variance-authority` + 17 more

---

### ynab-transaction-reviewer

**An intelligent daily email system that proactively pushes uncategorized YNAB
transactions for review, featuring smart categorization suggestions and
one-click actions.**

|                  |                                          |
| ---------------- | ---------------------------------------- |
| **Language**     | Python                                   |
| **Deployment**   | AWS Lambda                               |
| **Last Updated** | 2026-02-23                               |
| **Entry Points** | `src/reviewer_main.py`                   |
| **Integrations** | AWS, Google APIs, Google Auth, HTTP/REST |
| **Source Files** | 11                                       |
| **Config Files** | `.env.example`                           |
| **Has README**   | Yes                                      |
| **Has Tests**    | No                                       |

**Key Dependencies**: `requests`, `PyYAML`, `python-dateutil`,
`google-api-python-client`, `google-auth`, `google-auth-oauthlib`,
`google-auth-httplib2`, `boto3`, `pytest`, `black` + 1 more

**Claude Code Sessions** (1 sessions):

- `2026-02-24` — Trash Previous YNAB Review Emails on New Send
  (`claude --resume 08fb7e0e-5f6c-4de7-9d41-379b66d45e5c`)

---
