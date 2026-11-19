# `tc next <job>`: the agent's compass. Reads the job's stage ledger and says, for the next unfinished stage:
# what to do, which command records it, and which owner rules apply (so feedback is never forgotten).
from tc import jobs
from tc.cli import register
from tc.learning import list_rules

GUIDE = {
    "topic": ("Pick 6-10 seed topics in History or Secret Government Projects; score them; show the owner the top 3",
              'python -m tc topics {id} "seed one" "seed two" ...   then   python -m tc topics {id} --pick N'),
    "packaging": ("Write 10+ titles (<=60 chars, curiosity hook) + 3 thumbnail concepts that serve the picked topic; owner picks",
                  "python -m tc packaging {id} --titles jobs/{id}/titles.txt --thumbs jobs/{id}/thumbs.txt --pick N"),
    "research": ("Research with WebSearch; save every fact's source in jobs/{id}/sources.json as {{id: {{title, url, quote}}}}",
                 "python -m tc mark {id} research --note \"N sources\""),
    "script": ("Write jobs/{id}/script.md in the film structure (spec 6.0 + section 3); owner approves",
               "python -m tc script {id}   then after the owner's yes:   python -m tc script {id} --approve"),
    "voice": ("Narrate the approved script with the configured narrator", "python -m tc voice {id}"),
    "align": ("Time every line in voice.wav (plain python, not -I)", "python -m tc align {id}"),
    "shots": ("Write jobs/{id}/shots.json: every line shown literally, era-correct, 3-7 s shots, film camera moves, no captions",
              "python -m tc shots {id}"),
}


def next_action(job: jobs.Job) -> dict:
    stage = jobs.next_stage(job)
    if stage is None:
        return {"stage": None, "do": "Plan 1 stages complete: continue with library/build (Plan 2)", "command": "", "rules": []}
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
