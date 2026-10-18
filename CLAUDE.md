# DCS Chess Toolkit — Team Rules (MANDATORY)

## Inbox Protocol — MECHANICAL ENFORCEMENT

**Every turn, before doing ANY work, you MUST:**

1. Read your inbox at `.team/inbox/<your-role>.md`
2. If there are unhandled messages (not struck through with ~~), process them FIRST
3. Post updates to other inboxes when you complete work or hit blockers
4. Only THEN continue with your assigned cards

**This is not a suggestion. This is a hard rule. Violating it blocks the entire team.**

When you have read and acted on a message, mark it as handled by wrapping
the header line in `~~strikethrough~~` and adding a `**-> HANDLED** ...` line.
Unhandled messages trigger loud alerts in the hook output.

The UserPromptSubmit hook injects team state automatically. If you see
"UNHANDLED MESSAGES DETECTED" in the injected context, you MUST address
those messages before writing any code.

## Self-Pacing Loop — ALL ROLES

**Every role (PM, ENG1, ENG2, ADV) MUST run a ScheduleWakeup loop at ~60 second
intervals.** This ensures you automatically check your inbox and continue work
without waiting for someone to prompt you.

At the start of your session, and after every action, schedule your next wakeup:
```
ScheduleWakeup(delaySeconds=60, prompt="<your loop prompt>", reason="...", noop=true/false)
```

Your loop should: check inbox, process messages, do your current work, post
updates, then schedule the next wakeup. Never stop the loop unless told to.

## Roles

- **PM** (`pm.md`): Drives the Kanban. Only PM moves cards between columns.
- **ENG1** (`eng1.md`): Primary engineer. Core package lane.
- **ENG2** (`eng2.md`): Secondary engineer. Engine/SVG/variant lane + support.
- **ADV** (`adv.md`): Adversarial controller. Gates every card before DONE.

## Card Workflow

1. Engineer picks up card (PM assigns, moves to IN PROGRESS)
2. Engineer completes → posts to `pm.md` AND `adv.md`
3. PM moves to IN REVIEW
4. ADV reviews → posts verdict to `pm.md` and engineer's inbox
5. If APPROVED: PM moves to DONE
6. If REJECTED: PM moves back to IN PROGRESS, engineer fixes

## Key Constraints

- C1: Clean-room — never read python-chess source code
- C2: Pure Python 3.11+, stdlib only (except optional ctypes for Gaviota)
- C4: Behavior parity with python-chess (same inputs → same outputs)
- C5: Within 20% speed of python-chess

## Project Structure

```
dcs_chess/          — the library
tests/              — pytest test suite
.team/kanban.md     — shared Kanban board
.team/inbox/*.md    — per-role inboxes
.team/PROTOCOL.md   — full coordination protocol
```
