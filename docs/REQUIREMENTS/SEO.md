# SEO.md — search engine optimization

This document specifies how Miminet must be indexed by search engines and records
the current state of the implementation. It is a section of the specification,
see [REQUIREMENTS.md](../REQUIREMENTS.md).

The audit was performed against `main` at commit `1628286`. Every claim was
verified by reading the source; references use the `path:line` form.

## Contents

- [Purpose](#purpose)
- [Current state](#current-state)
  - [Title and description](#title-and-description)
  - [Open Graph](#open-graph)
  - [robots.txt](#robotstxt)
  - [sitemap.xml](#sitemapxml)
  - [Analytics](#analytics)
- [Public page map](#public-page-map)

---

## Purpose

Miminet is a web emulator of computer networks for educational purposes. Organic
traffic is expected to come mostly from the Russian internet, so the priority
search engines are Yandex and Google.

SEO is treated not as a one-off task but as **a requirement for every new public
page**: any page reachable by an anonymous visitor must carry a meaningful
`title`, `description`, Open Graph tags, and appear in `sitemap.xml` with a
correct `canonical`.

### What should be indexed

| Category | Example | In sitemap |
|---|---|---|
| Landing | `/` | yes |
| Courses | `/course` | yes |
| Network examples | `/examples` | yes |
| Publicly shared networks | `/web_network_shared?guid=<guid>` | no, per-URL at most |
| Dashboards, profiles, author's own networks | `/home`, `/profile`, `/web_network?guid=<guid>` | no |
| APIs, actions, static assets | `/quiz/*`, `/host/*_save_config`, `/config.js` | no |

Personal networks (`/web_network?guid=`) must never reach the index: they are
reachable by their author only. Publicly shared networks are low priority — there
is no meaningful search query behind them, and promoting them through `/examples`
is the better lever.

---

## Current state

### Title and description

The base blocks are declared in `front/src/templates/base.html:17-20`:

```html
<meta name="description" content="{% block description %}{% endblock %}">
<meta name="author" content="Илья Зеленчук, Зинаида Романова">

<title>{% block title %}{% endblock %}</title>
```

**The blocks are empty by default** — a value exists only if a child template
overrides it. A page that forgets the override emits an empty `<title>` and an
empty `description` rather than a fallback.

### Open Graph

The `{% block og %}` block is declared in `front/src/templates/base.html:22` and is
likewise empty by default. A complete tag set exists only on the network pages
(`front/src/templates/network.html:4-13` and
`front/src/templates/network_shared.html:4-13`):

```html
<meta property="og:type" content="website">
<meta property="og:site_name" content="Miminet">
<meta property="og:title" content="{{ network.title }}">
<meta property="og:description" content="Эмуляция компьютерной сети в вебе">
<meta property="og:url" content="https://miminet.ru{{ url_for(request.endpoint, guid=network.guid) }}">
<meta property="og:locale" content="ru_RU">
<meta property="og:image" content="https://miminet.ru/images/preview/{{ network.preview_uri }}">
```

This is the only place in the project where OG tags are filled in meaningfully.
The dynamic `og:title` comes from `network.title`, the dynamic `og:image` from
`network.preview_uri` (model `front/src/miminet_model.py:63`, default value
`first_network.jpg`, `nullable=False`).

Every other page has no OG tags. In `mimishark.html:5-7` the `og` block is put to
another use — a `<link rel="stylesheet">` sits where the OG meta tags belong.

### robots.txt

`front/src/static/robots.txt` is correct:

```
User-agent: *
Allow: /
Sitemap: https://miminet.ru/Sitemap.xml
Disallow: /auth/
```

### sitemap.xml

Generated on the fly in `front/src/app.py:615-666` from `app.url_map`. The logic:

1. iterate over every rule in `app.url_map.iter_rules()`;
2. skip the paths listed in `skip_pages` (`app.py:620-645`);
3. skip any path containing `admin/`;
4. keep the rule if it has a `GET` method and `len(rule.arguments) == 0`.

Rendered through `front/src/templates/sitemap_template.xml`:

```xml
<url>
    <loc>{{page[0]|safe}}</loc>
    <lastmod>{{page[1]}}</lastmod>
    <changefreq>monthly</changefreq>
</url>
```

`lastmod` is the same date for every URL — `zero_days_ago`
(`front/src/app.py:275`), computed once at process start. So `lastmod` does not
reflect real changes, and `changefreq=monthly` is the same for every page.

**Result: 34 URLs in the sitemap, of which 3 are public content pages.**

| Category | Count | URLs |
|---|---|---|
| Public content | 3 | `/`, `/course`, `/examples` |
| JSON APIs | 14 | `/refresh_access`, `/emulation_queue/size`, `/emulation_queue/time`, `/quiz/test/owner`, `/quiz/test/all`, `/quiz/test/get`, `/quiz/section/test/all`, `/quiz/question/all`, `/quiz/session/question/json`, `/quiz/session/question`, `/quiz/session/result`, `/quiz/user/session/result`, `/ai-testing/api/state`, `/ai-testing/api/result` |
| Server actions | 4 | `/host/router_save_config`, `/host/server_save_config`, `/host/textbox_save_config`, `/edge/save_config` |
| MimiShark duplicates | 5 | `/host/mimishark`, `/router/mimishark`, `/server/mimishark`, `/hub/mimishark`, `/switch/mimishark` |
| Static asset | 1 | `/config.js` |
| Auth / OAuth | 2 | `/auth/login.html`, `/auth/vk_login` |
| Private pages | 3 | `/profile`, `/create_network`, `/ai-testing` |
| Redirect aliases | 2 | `/web_network`, `/web_network_shared` |

The five MimiShark routes (`app.py:355-359`) are all registered against the
**same** `mimishark_page` view function and differ only in path. In the sitemap
they appear as five separate URLs carrying identical content.

### Analytics

Google Tag Manager `GTM-KT5XZVF` is loaded in
`front/src/templates/base.html:6-11` with its noscript variant in
`base.html:35-38`. Events and goals are not regulated by this document.

---

## Public page map

| URL | Template | `title` | `description` | OG |
|---|---|---|---|---|
| `/` | `index.html:2-3` | yes | yes | no |
| `/course` | `course.html:2-3` | yes | yes | no |
| `/examples` | `examples.html:2-3` | yes | yes | no |
| `/home` | `home.html:2-3` | yes | yes | no |
| `/web_network?guid=` | `network.html:2-13` | yes, dynamic | yes | yes |
| `/web_network_shared?guid=` | `network_shared.html:2-13` | **no** (commented out) | yes | yes |
| `/auth/login.html` | `auth/login.html:2-3` | yes | yes | no |
| `/host/mimishark` and 4 more | `mimishark.html:3-7` | yes | yes | no (block misused) |
| `/information/consent` | `cookie_consent.html:2-3` | yes | yes | no |
| `/ai-testing` | `ai_interview/interview.html:2-3` | yes | yes | no |
| `/profile`, `/user/profile.html` | `auth/profile.html:3` | yes | **no** | no |
| `/profile/<int:user_id>` | `auth/profile_readonly.html:3-4` | yes | **no** | no |
| `/quiz/...` | `quiz/quiz.html:2-3` | yes, dynamic | yes | no |
| `/quiz/session/question` | `quiz/sessionQuestion.html:2-3` | **empty** | yes | no |

`front/src/templates/quiz/networkBase.html:25-30` duplicates the `<head>` from
`base.html` with the same empty blocks.

---
