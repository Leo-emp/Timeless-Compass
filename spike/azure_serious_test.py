# Spike (throwaway): the Salamis moment as a SERIOUS cinematic documentary, voiced by 3 Azure voices.
# Tension comes from slow pace, low pitch and long pauses before the reveal.
# Usage: python -I azure_serious_test.py
import pathlib, subprocess

HERE = pathlib.Path(__file__).parent
env = dict(l.strip().split('=', 1) for l in pathlib.Path('C:/Users/User/capitalcode/.env.local').read_text().splitlines()
           if '=' in l and not l.startswith('#'))
KEY, REGION = env['AZURE_SPEECH_KEY'].strip('"'), env['AZURE_SPEECH_REGION'].strip('"')

BODY = """<prosody rate="-8%">
  September, 480 BC. <break time="700ms"/>
  The largest army the world had ever seen <break time="250ms"/> had just burned Athens to the ground. <break time="900ms"/>
  The Greek fleet was trapped in a narrow strait <break time="300ms"/> and its commanders wanted to flee. <break time="800ms"/>
  But one man <break time="400ms"/> had a different plan. <break time="900ms"/>
  That night, Themistocles sent his most trusted servant <break time="300ms"/> across the water <break time="300ms"/> to the Persian king. <break time="600ms"/>
  The message was simple. <break time="500ms"/>
  <prosody rate="-15%" pitch="-4%">The Greeks are about to run. <break time="400ms"/> Strike now.</prosody> <break time="1000ms"/>
  Xerxes believed every word. <break time="800ms"/>
  At dawn <break time="300ms"/> he took his seat on a golden throne above the strait <break time="400ms"/> to watch his victory. <break time="1100ms"/>
  <prosody rate="-18%" pitch="-8%">It was a trap.</prosody>
</prosody>"""

VOICES = [
    ('serious_andrew_hd', 'en-US-Andrew:DragonHDLatestNeural'),
    ('serious_davis', 'en-US-DavisNeural'),
    ('serious_brian_ml', 'en-US-BrianMultilingualNeural'),
]
for name, voice in VOICES:
    (HERE / 'az_body.xml').write_text(f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"
      xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="{voice}">{BODY}</voice></speak>""", encoding='utf-8')
    code = subprocess.run(['curl', '-s', '-o', str(HERE / f'{name}.mp3'), '-w', '%{http_code}', '--max-time', '120',
        '-H', f'Ocp-Apim-Subscription-Key: {KEY}', '-H', 'Content-Type: application/ssml+xml',
        '-H', 'X-Microsoft-OutputFormat: audio-48khz-192kbitrate-mono-mp3', '-H', 'User-Agent: tc-spike',
        '--data-binary', f'@{HERE / "az_body.xml"}',
        f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'], capture_output=True, text=True).stdout
    print(name, code)
