# Spike (throwaway): voice the Salamis test script with Azure Speech, 3 voices, to compare with ElevenLabs.
# Comedy timing is written in SSML: <break> = pause before a punchline, <prosody> = slower/faster/pitch,
# <mstts:express-as> = a speaking style (whispering, cheerful...) on voices that support it.
# Usage: python -I azure_voice_test.py
import pathlib, subprocess

HERE = pathlib.Path(__file__).parent
ENV = pathlib.Path('C:/Users/User/capitalcode/.env.local')     # borrow the Azure key (never printed)
env = dict(l.strip().split('=', 1) for l in ENV.read_text().splitlines() if '=' in l and not l.startswith('#'))
KEY, REGION = env['AZURE_SPEECH_KEY'].strip('"'), env['AZURE_SPEECH_REGION'].strip('"')

def ssml(voice, styled):
    # styled=True uses speaking styles (only some voices have them)
    w = (lambda style, t: f'<mstts:express-as style="{style}">{t}</mstts:express-as>') if styled else (lambda style, t: t)
    body = f"""
      So. <break time="350ms"/> Themistocles has a plan.
      <break time="500ms"/> A really <break time="400ms"/> <prosody rate="-15%" pitch="+8%">great</prosody> plan.
      <break time="500ms"/> He sends his own servant <break time="250ms"/> to the King of Persia <break time="250ms"/> with a secret message.
      <break time="450ms"/> {w('whispering', '<prosody rate="-10%">Psst. The Greeks are running away.</prosody>')}
      <break time="600ms"/> Which <break time="300ms"/> they were <prosody pitch="+12%" rate="-20%">not.</prosody>
      <break time="600ms"/> And Xerxes? <break time="500ms"/> {w('cheerful', 'Xerxes believes him.')}
      <break time="400ms"/> He's so sure he's about to win <break time="250ms"/> he has a golden throne carried up a hill <break time="300ms"/>
      so he can sit back <break time="300ms"/> and <prosody rate="-25%">watch.</prosody>
      <break time="900ms"/> {w('serious', '<prosody rate="-12%" pitch="-6%">He was about to watch the worst day of his life.</prosody>')}"""
    return f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
      <voice name="{voice}">{body}</voice></speak>"""

VOICES = [
    ('az_andrew_hd', 'en-US-Andrew:DragonHDLatestNeural', False),   # newest HD voice: most human, no styles
    ('az_davis', 'en-US-DavisNeural', True),                        # supports whispering / cheerful / serious-ish styles
    ('az_brian_ml', 'en-US-BrianMultilingualNeural', False),        # natural conversational narrator
]
for name, voice, styled in VOICES:
    out = HERE / f'{name}.mp3'
    (HERE / 'az_body.xml').write_text(ssml(voice, styled), encoding='utf-8')
    # curl (Python's own HTTP client hung earlier on this machine)
    code = subprocess.run(['curl', '-s', '-o', str(out), '-w', '%{http_code}', '--max-time', '120',
        '-H', f'Ocp-Apim-Subscription-Key: {KEY}', '-H', 'Content-Type: application/ssml+xml',
        '-H', 'X-Microsoft-OutputFormat: audio-48khz-192kbitrate-mono-mp3', '-H', 'User-Agent: tc-spike',
        '--data-binary', f'@{HERE / "az_body.xml"}',
        f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'], capture_output=True, text=True).stdout
    print(name, code)
