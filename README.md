# Timeless Compass — cinematic documentary agent

An agentic system that makes **animated, cinematic, movie-style documentaries** about history and secret
government projects: 3D characters in era-correct costume act out a serious narration, with real camera moves,
sound design, music and film grading. No AI-generated images, no stock footage — everything is built by code
from free, open tools (Blender, MakeHuman/MPFB CC0 humans, free motion capture).

- **Design:** [`docs/superpowers/specs/2026-11-19-cinematic-agent-design.md`](docs/superpowers/specs/2026-11-19-cinematic-agent-design.md)
- **Plan 1 (foundation, script, voice, shot list):** [`docs/superpowers/plans/2026-11-19-plan1-foundation-voice-shotlist.md`](docs/superpowers/plans/2026-11-19-plan1-foundation-voice-shotlist.md)
- **Plan 2 (3D library):** [`docs/superpowers/plans/2026-11-19-plan2-3d-library.md`](docs/superpowers/plans/2026-11-19-plan2-3d-library.md)

## Layout

| Path | What |
|---|---|
| `tc/` | the `tc` command-line tools the agent uses (`python -m tc --help`) |
| `tests/` | `python -m pytest` |
| `.claude/skills/timeless/SKILL.md` | the agent's playbook (`/timeless`) |
| `blender/` | the 3D library (characters, wardrobe, armour, sets, props) — see `blender/README.md` |
| `library/` | asset manifests (era, design source, licence, ratings) |
| `cloud/` + `.github/workflows/render-test.yml` | free cloud rendering (GitHub Actions CPU, Kaggle GPU) |
| `taste/` | owner rules the agent follows (`python -m tc rules`) |
| `spike/` | throwaway experiments and test renders |

## Pipeline (per video)

topic (by demand) → packaging (title + thumbnail first) → research (sourced) → script (film structure, owner
approves) → narration (Azure) → word timings → shot list (every line shown literally) → 3D library build →
stills review → cloud render → edit (sound, music, grade) → QA → package → archive.

Secrets live only in a git-ignored `.env`; the repo is public.
