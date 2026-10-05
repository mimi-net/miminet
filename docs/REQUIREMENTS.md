# REQUIREMENTS.md — Miminet specification

This document specifies Miminet: how it is built, what problems it solves, and
which rules it lives by. It covers both the frontend and the backend.

The specification is **maintained as work proceeds**. No section has to be written
in one go: new requirements are recorded as they become clear, together with
everything already implemented that deserves a description.

## Contents

- [Sections](#sections)
- [Principles](#principles)
- [Related documents](#related-documents)

---

## Sections

| Section | Description | Status |
|---|---|---|
| [SEO.md](REQUIREMENTS/SEO.md) | Search engine optimization: indexing, meta tags, `sitemap.xml`, `robots.txt` | in progress |
| | | |

### SEO.md — search engine optimization

Goals and boundaries: which pages get indexed and which do not.

Current state: `title`, `description`, Open Graph, `robots.txt`, `sitemap.xml`,
analytics; a map of the public pages.

---

## Principles

**The specification states requirements, not development history.** The document
answers "what should be" and "why this way". It does not narrate how a task was
solved.

**Fact is separated from plan.** Current state and known gaps belong in the
"Current state" and "Issue registry" sections. The desired state belongs in
"Planned changes". An issue stops being an issue once it is fixed — the entry is
removed from the registry rather than marked resolved.

**A requirement is verifiable.** "Should be convenient" is not a requirement.
"Every public page has a non-empty `title`" is.

**Code references are exact.** Every claim about the implementation is accompanied
by a `path:line` reference. When the code changes the reference goes stale — that
is a reason to update the section, not to drop the claim.

**Definitions live in one place.** A term used by several sections is defined by
the section that owns it, and the other sections link back from there.

**Fixes belong to the section that owns the subject.** A new requirement about
routes goes into the section about routes, not at the end of the shared file.

## Related documents

Documents outside the scope of the specification:

| Document | Description |
|---|---|
| [GIT.md](GIT.md) | Branch and commit naming rules |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Running the tests on a rootless Linux host, without Docker |
| [BACKEND_TESTS.md](BACKEND_TESTS.md) | Backend test inventory |
| [FUNCTIONAL_TESTS.md](FUNCTIONAL_TESTS.md) | Functional test inventory |
| [../AGENTS.md](../AGENTS.md) | Instructions for agents working on the project |
| [../README.md](../README.md) | Project overview, deployment, architecture |