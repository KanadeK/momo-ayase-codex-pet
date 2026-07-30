# Research record

Research date: **2026-07-30** (Asia/Shanghai).

This file separates observed facts, project decisions, and limits. Search
results can change after the recorded date.

## Character reality and popularity

Momo Ayase is an existing lead character, not a generated name or invented
franchise. Primary identity source:

- [Official DANDADAN character page](https://anime-dandadan.com/en/character/)
- In a [MANGA Plus creator interview](https://mangaplus.shueisha.co.jp/web_pages/1769/),
  Yukinobu Tatsu identifies Momo as his favorite character.

One recent audience signal ranked Momo fourth among 2025 female anime
characters (7.54% of 24,797 participating voters):

- [Anime Corner 2025 female character ranking](https://animecorner.me/best-female-character-of-the-year-ranking-2025-anime-awards/)

This poll is evidence of an active audience, not a population-wide popularity
measurement and not a promise of repository traffic.

## Duplicate search

Searches covered repository names, descriptions, and code for combinations of:

- `"Momo Ayase" codex pet`
- `DANDADAN codex pet`
- `momo-ayase-codex-pet`
- `Momo Ayase` within major public pet aggregators and pet repositories
- exact code searches for `"Momo Ayase" pet.json`,
  `Dandadan spritesheet.webp`, and `"Momo Ayase" spriteVersionNumber`

The sampled lists included:

- [legeling/awesome-codex-pet](https://github.com/legeling/awesome-codex-pet)
- [crafter-station/petdex](https://github.com/crafter-station/petdex)
- [chenxin-dlut/codex-anime-pets](https://github.com/chenxin-dlut/codex-anime-pets)

No Momo Ayase implementation was found in the searched repository and code
indexes on 2026-07-30.

Exact GitHub repository searches for `"codex pet" accessibility audit`,
`"codex pet" reduced motion compiler`, `petease codex pet`, and
`"codex pet" flicker analyzer` also returned no repositories on that date.

Popular alternatives were rejected because implementations already existed in
the search results:

| Candidate | Result |
| --- | --- |
| Frieren | Existing dedicated Codex pet |
| Maomao | Existing dedicated Codex pet |
| Bocchi | Existing dedicated Codex pet |
| Anya Forger | Multiple existing pets |
| Hatsune Miku | Existing pet |
| Kasane Teto | Existing dedicated pet |

Absence from search is not mathematical proof that no private, unindexed,
deleted, or newly created project exists. The repository therefore states the
search date instead of claiming permanent global uniqueness.

## Local-project collision check

The local project inventory was checked before implementation. Existing work
already covered:

- generic v2 package validation, installation, repair, and preview;
- session trace and animation replay;
- screenshot-oriented visual regression;
- v2-to-web dual-atlas compilation.

PetEase was chosen to avoid those scopes. Its defining behavior is
**motion-accessibility analysis plus deterministic reduced-motion
transformation**, with SARIF, provenance, safe installation, and reproducible
archives.

## Product hypothesis

The project combines two independently useful reasons to visit:

1. a popular, currently unrepresented anime character with a complete v2 pet;
2. a reusable tool that works on any valid Codex v2 pet.

The second part prevents the repository from becoming a one-character shell.
It also gives maintainers a reason to link the project from CI, accessibility,
and pet-authoring discussions.

## Success signals

Stars and views cannot be guaranteed. Measurable, honest signals after release
are:

- successful CI runs across Windows, macOS, and Linux;
- release download count;
- clones and unique visitors visible to the maintainer;
- issues from other pet authors using PetEase;
- inclusion in community pet indexes.

No automated starring, artificial traffic, impersonation, or spam outreach is
part of this project.
