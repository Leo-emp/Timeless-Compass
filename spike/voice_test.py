# Spike (throwaway): voice the Salamis scene with ElevenLabs v3 using performance tags,
# so we can hear whether the narration sounds human and funny (pauses, stress, timing).
# Usage: python -I voice_test.py <voice_id> <out_name>
import json, sys, urllib.request, pathlib

HERE = pathlib.Path(__file__).parent
# read the key from the Timeless Compass .env without ever printing it
KEY = next(l.split('=', 1)[1].strip().strip('"') for l in open(HERE.parent / '.env') if l.startswith('ELEVENLABS_API_KEY'))

# The script. Comedy timing lives in the punctuation and tags:
#   ...        = a beat before the punchline
#   [tags]     = how to say the next words (v3 audio tags)
#   CAPS       = stress on that word
SCRIPT = """So. Themistocles has a plan.
[sarcastic] A really... GREAT plan.
He sends his own servant... to the King of Persia... with a secret message.
[whispers] "Psst. The Greeks are running away."
[short pause] Which... they were NOT.
And Xerxes? [chuckles] Xerxes believes him.
He's so sure he's about to win... he has a golden throne carried up a hill...
so he can sit back... and WATCH.
[pause] [serious] He was about to watch the worst day of his life."""

voice_id, name = sys.argv[1], sys.argv[2]
body = json.dumps({
    "text": SCRIPT,
    "model_id": "eleven_v3",
    "voice_settings": {"stability": 0.5},   # v3: 0 = creative, 0.5 = natural, 1 = robust
}).encode()
req = urllib.request.Request(
    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
    data=body, headers={"xi-api-key": KEY, "Content-Type": "application/json"})
out = HERE / f"voice_{name}.mp3"
out.write_bytes(urllib.request.urlopen(req, timeout=180).read())
print("saved", out)
