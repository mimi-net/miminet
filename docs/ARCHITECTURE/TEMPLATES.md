# TEMPLATES.md — template structure

How the Jinja2 templates and the client-side scripts are composed. It is a
section of the architecture reference, see
[ARCHITECTURE.md](../ARCHITECTURE.md). What each template and asset file *is* is
in [MODULES.md](MODULES.md#templates-and-static-assets); the SEO requirements for
`title`/`description`/Open Graph are in
[REQUIREMENTS/SEO.md](../REQUIREMENTS/SEO.md).

## Contents

- [The shell](#the-shell)
- [Conventions](#conventions)
- [Route → template map](#route--template-map)

---

## The shell

`base.html` is the only page shell. It defines five blocks:

| Block | Purpose |
|---|---|
| `description` | `<meta name="description">` — SEO-relevant, see [REQUIREMENTS/SEO.md](../REQUIREMENTS/SEO.md) |
| `title` | `<title>` |
| `og` | Open Graph tags and page-specific `<link>`/`<style>` |
| `content` | The page body |
| `network` | Scripts and modals that only make sense on an editor page |

`base.html` also renders the navbar, the network-settings / delete / copy /
no-jobs / too-many-hosts modals, and the shared script tags. Vendor libraries
are loaded once here: jQuery, jQuery UI, Cytoscape (+ canvas and edgehandles
plugins), Ace, lodash, then the theme and Bootstrap from
`static/assets/vendor/`.

---

## Conventions

- **Page templates extend `base.html`; snippet templates do not.** Files that
  start with `<script src=…` and have no `{% extends %}` are includes, not
  pages: `quiz/practiceTask.html`, `quiz/textTask.html` (both pulled into
  `quiz/sessionQuestion.html`), and `quiz/_result_answer_assets.html`,
  `quiz/_result_cards.html` (pulled into both result pages).
- **Macros live in `_`-prefixed templates.** `quiz/_result_cards.html` defines
  `render_answer_items` and is included for its macro, not its markup.
- **A second-level base exists for the quiz workspace.** `quiz/networkBase.html`
  is a standalone `<html>` document — it does not extend `base.html`, it
  duplicates the shell. `quiz/sessionQuestion.html` extends it. Extending
  `base.html` twice is not possible in Jinja, so a page needing a different shell
  gets its own base.
- **`mimishark_nav` suppresses the navbar.** `base.html` wraps the navbar in
  `{% if mimishark_nav is not defined %}`, so editor and MimiShark views pass
  `mimishark_nav=1` and render their own chrome.
- **`network` in the context is a feature flag, not just data.** The whole
  modal cluster in `base.html` is behind `{% if network %}`. Any template that
  should get the network modals must receive a `network` object.
- **JSON reaches JavaScript through `tojson`, never raw interpolation.**
  `base.html:330` and `base.html:336` are the reference pattern:
  `{{ current_user.is_authenticated|tojson }}`, and user config is parsed
  defensively on the client because the column is a text field that may hold
  either a JSON string or an object.
- **Editor state is bootstrapped as named variables.** `web_network` and
  `web_network_shared` pass `nodes`, `edges`, `jobs`, `packets`, `pcaps`,
  `network_config` and `simulating` to the template; `netfront.js` and
  `miminet_animation.js` read them as globals.
- **`static_url_path=""`** means `url_for('static', filename=…)` produces a
  root-absolute path, so templates and JS can hardcode `/…` without knowing the
  mount point.
- **`/config.js` is a route, not a file.** `url_for('static', filename='config.js')`
  resolves to `/config.js`, which the explicit `@app.route("/config.js")` wins
  over the catch-all static rule. The route reads the template by absolute path
  (`front/src/app.py:543`) and renders it with `EXTERNAL_BASE_URL`, so it has no
  working-directory dependency.

---

## Route → template map

| Route | View | Template |
|---|---|---|
| `/` | `app.index` | `index.html` |
| `/home` | `app.home` | `home.html` |
| `/course` | `app.course` | `course.html` |
| `/examples` | `app.examples` | `examples.html` |
| `/information/consent` | `app.cookie_consent` | `cookie_consent.html` |
| `/web_network` | `miminet_network.web_network` | `network.html` |
| `/web_network_shared` | `miminet_network.web_network_shared` | `network_shared.html` |
| `/auth/login.html` | `miminet_auth.login_index` | `auth/login.html` |
| `/user/profile.html`, `/profile` | `miminet_auth.user_profile` | `auth/profile.html` |
| `/profile/<int:user_id>` | `miminet_auth.user_profile_view` | `auth/profile_readonly.html` |
| `/quiz/test/all` | `quiz.controller.test_controller.get_all_tests_endpoint` | `quiz/quizzes.html` |
| `/quiz/session/question/json` | `quiz_session_controller.get_session_question_json` | `quiz/sessionQuestion.html` |
| `/quiz/session/result` | `quiz_session_controller.session_result_endpoint` | `quiz/sessionResult.html` or `quiz/noResult.html` |
| `/quiz/user/session/result` | `quiz_session_controller.get_result_by_session_guid_endpoint` | `quiz/userSessionResult.html` |
| `/ai-testing` | `ai_interview.controller.interview_page` | `ai_interview/interview.html` |
| `/host/mimishark` and siblings | `miminet_shark.mimishark_page` | `mimishark.html` |
| `/sitemap.xml` | `app.sitemap` | `sitemap_template.xml` |
| `/admin/…` | `miminet_admin.*` views | `admin/*.html` |

All routes are registered in `front/src/app.py`; see
[CONVENTIONS.md](CONVENTIONS.md#adding-things) for what to do when adding one.