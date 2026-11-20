# `tc next <job>`: the agent's compass. Reads the job's stage ledger and says, for the next unfinished stage:
# what to do, which command records it, and which owner rules apply (so feedback is never forgotten).
from tc import jobs
from tc.cli import register
from tc.learning import list_rules

# One line per stage: what the agent does on its own, and the command that checks it (rule r20: no owner gates).
GUIDE = {
    "topic": ("Brainstorm 6-10 History / Secret Government Projects seeds; draft a 5-line story pitch for each; score "
              "demand AND story potential (r25); pick the best", 'python -m tc topics {id} "seed one" ...   then   --pick N'),
    "packaging": ("Write 10+ titles (<=60 chars, honest curiosity hook) + 3 thumbnail concepts (r21); choose the best pair",
                  "python -m tc packaging {id} --titles jobs/{id}/titles.txt --thumbs jobs/{id}/thumbs.txt --pick N"),
    "research": ("Research with WebSearch: every fact in jobs/{id}/sources.json, plus the era sheet jobs/{id}/era.json (r32)",
                 "python -m tc era {id}   then   python -m tc mark {id} research --note \"N sources\""),
    "story": ("Design the story page jobs/{id}/story.md from docs/SCRIPT_BIBLE.md (r24, r33), self-score it",
              "python -m tc story {id}   and   python -m tc qa {id} story jobs/{id}/qa/story_answers.json"),
    "script": ("Write jobs/{id}/script.md from the story page with character dialogue (r1, r12); passes the checker",
               "python -m tc script {id}"),
    "viewer": ("Write the viewer packet; ONE fresh subagent reads it with docs/VIEWER_BRIEF.md; record its verdict (r27). "
               "NO-GO -> rewrite the script", "python -m tc viewer {id} --packet   then   --record jobs/{id}/qa/verdict.json"),
    "voice": ("Narrate the script; voice every character line in its own Fish voice (r26)",
              "python -m tc voice {id}   and   python -m tc dialogue {id}"),
    "align": ("Time every word in the voice (plain python, not -I)", "python -m tc align {id}"),
    "artdir": ("Write the art direction for this video (palette per act, places, light plan) - never like recent videos (r17)",
               "python -m tc artdir {id}"),
    "cast": ("Load or create every character sheet the story needs; new ones pass the character check (r19)",
             "python -m tc cast {id}"),
    "shots": ("Write the shot plan: word-anchored beats, camera, grade, transition, era items per shot (r28-r34)",
              "python -m tc shots {id}"),
    "draw": ("Draw every set and shot fresh in film/ (one set per place in this video, r23)", "python -m tc draw {id}"),
    "stills": ("Render every key frame; measured checks + self-score each still >= 90 (r18)",
               "python -m tc still <png> --json <json>   and   python -m tc qa {id} still <answers.json> --subject <shot>"),
    "motion": ("Animate per the plan with natural flow (r29); check clips around each key word",
               "python -m tc motion <clip.mp4> --beats ...   and   python -m tc qa {id} motion <answers.json>"),
    "thumbnail": ("Draw 2 fresh thumbnails (r21); self-score each", "python -m tc qa {id} thumbnail <answers.json> --subject a"),
    "render": ("Render the video in parts on GitHub + Kaggle and join them", "python -m tc film render <comp> --frames N --parts P"),
    "mix": ("Mix narrator + characters + sfx in every scene + music only at peaks (r26)", "python -m tc mix {id}"),
    "pack": ("Write the upload pack into packs/{id}/ with READY.md (r22)", "python -m tc pack {id}"),
    "archive": ("Free the laptop: delete local renders once the pack is complete (r8)", "python -m tc archive {id}"),
    "results": ("For 30 days after upload: read public stats and turn what they show into rules", "python -m tc results {id}"),
}


def next_action(job: jobs.Job) -> dict:
    stage = jobs.next_stage(job)
    if stage is None:
        return {"stage": None, "do": "All stages finished for this job", "command": "", "rules": []}
    do, cmd = GUIDE[stage]
    return {"stage": stage, "do": do.format(id=job.id), "command": cmd.format(id=job.id),
            "rules": [r["id"] for r in list_rules(stage)]}


@register("next", "what to do next on a job (+ the owner rules for it)", lambda p: p.add_argument("job"))
def _cmd_next(args) -> int:
    a = next_action(jobs.load_job(args.job))
    print(f"next stage: {a['stage']}\ndo: {a['do']}\ncommand: {a['command']}")
    if a["stage"]:
        for r in list_rules(a["stage"]):
            print(f"rule {r['id']}: {r['text']}")
    return 0
