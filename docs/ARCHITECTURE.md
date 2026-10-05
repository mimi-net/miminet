# ARCHITECTURE.md — Miminet architecture

Reference map of the Miminet codebase: what each module owns, how data moves
between the two halves, how the templates are composed, and the conventions a
change has to follow.

This document describes **what is**. What Miminet *should* be lives in
[REQUIREMENTS.md](REQUIREMENTS.md) and `docs/REQUIREMENTS/`. How to run and test
it lives in [DEVELOPMENT.md](DEVELOPMENT.md), `README.md` and `docs/*_TESTS.md`.
Repository-specific traps live in [AGENTS.md](../AGENTS.md).

The reference is **maintained as work proceeds**. A new module, a new data path
or a new rule is added to the section that owns the subject, together with
everything already implemented that deserves a description.

## Contents

- [Subjects](#subjects)
- [Principles](#principles)

---

## Subjects

| File | Description |
|---|---|
| [ARCHITECTURE/SYSTEM.md](ARCHITECTURE/SYSTEM.md) | Deployment topology, processes per container, exchanges and queues |
| [ARCHITECTURE/MODULES.md](ARCHITECTURE/MODULES.md) | Module map: what every module owns and what it may depend on |
| [ARCHITECTURE/DATA-FLOW.md](ARCHITECTURE/DATA-FLOW.md) | The shared network document, emulation and grading sequences, pcap, AI, auth |
| [ARCHITECTURE/TEMPLATES.md](ARCHITECTURE/TEMPLATES.md) | The page shell, template conventions, route → template map |
| [ARCHITECTURE/CONVENTIONS.md](ARCHITECTURE/CONVENTIONS.md) | Naming, the `job_id` contract, database and environment rules, per-change checklists, CI commands |

### Where to look first

| Question | File |
|---|---|
| What runs where, and how do the halves talk | [SYSTEM.md](ARCHITECTURE/SYSTEM.md) |
| Which module do I edit for feature X | [MODULES.md](ARCHITECTURE/MODULES.md) |
| What happens when the user presses *Emulate* | [DATA-FLOW.md](ARCHITECTURE/DATA-FLOW.md) |
| Why did my template change not show up | [TEMPLATES.md](ARCHITECTURE/TEMPLATES.md) |
| What do I have to update when I add a command or a device | [CONVENTIONS.md](ARCHITECTURE/CONVENTIONS.md) |

---

## Principles

**The reference describes the implementation, not the plan.** It answers "how is
this built" and "where does this live". Desired behaviour is a requirement and
belongs in [REQUIREMENTS.md](REQUIREMENTS.md); a gap between the two is a
finding to raise, not a sentence to write here.

**Code references are exact.** Every claim about the implementation is
accompanied by a `path:line` reference. When the code changes the reference goes
stale — that is a reason to update the section, not to drop the claim.

**Facts are separated from traps.** A rule belongs in a section of this
reference. A gotcha that is not a rule — something that bites you once — belongs
in [AGENTS.md](../AGENTS.md), so that the reference stays a description of the
design rather than a list of accidents.

**Definitions live in one place.** A term used by several sections is defined by
the section that owns it, and the other sections link back from there. The
network document is defined once, in
[DATA-FLOW.md](ARCHITECTURE/DATA-FLOW.md#the-network-document--the-shared-contract);
the `job_id` ranges are defined once, in
[CONVENTIONS.md](ARCHITECTURE/CONVENTIONS.md#the-job_id-registry).

**Sections link instead of repeating.** A fact stated in two places is a fact
that will be correct in one of them.

**A change goes into the section that owns the subject.** A new module is
described in [MODULES.md](ARCHITECTURE/MODULES.md); a new data path in
[DATA-FLOW.md](ARCHITECTURE/DATA-FLOW.md); a new rule in
[CONVENTIONS.md](ARCHITECTURE/CONVENTIONS.md) — not appended to this file.