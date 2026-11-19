# Spike (throwaway): narrator test for Azure "Lewis Multilingual" (owner's pick) on two Timeless Compass openings.
# Near-natural pace (-4%), pauses only where a human narrator would breathe or build tension.
# Usage: python -I azure_lewis_test.py
import pathlib, subprocess

HERE = pathlib.Path(__file__).parent
env = dict(l.strip().split('=', 1) for l in pathlib.Path('C:/Users/User/capitalcode/.env.local').read_text().splitlines()
           if '=' in l and not l.startswith('#'))
KEY, REGION = env['AZURE_SPEECH_KEY'].strip('"'), env['AZURE_SPEECH_REGION'].strip('"')
VOICE = 'en-US-LewisMultilingualNeural'

SCRIPTS = {
  # HISTORY: cold open of "The Trap at Salamis"
  'salamis': """
    At dawn, the King of Persia sat on a golden throne <break time="200ms"/> high above the sea. <break time="500ms"/>
    He had come to watch the Greeks die. <break time="700ms"/>
    Below him, more than a thousand warships waited in the dark water. <break time="400ms"/>
    Athens was already in ashes. <break time="300ms"/> Sparta was too far away. <break time="300ms"/>
    And the last Greek fleet was trapped in a narrow strait, <break time="200ms"/> with nowhere left to run. <break time="800ms"/>
    By noon, <break time="300ms"/> Xerxes would be watching something else entirely. <break time="600ms"/>
    Because the night before, <break time="200ms"/> one man had sent him a message. <break time="500ms"/>
    And every word of it <break time="300ms"/> was a lie.""",
  # SECRET GOVERNMENT PROJECT: cold open of "Project A119"
  'a119': """
    In 1958, <break time="200ms"/> inside a guarded office in Chicago, <break time="200ms"/> a small group of scientists were given a secret assignment. <break time="600ms"/>
    It had no public name. <break time="300ms"/> Just a number. <break time="400ms"/> A one-one-nine. <break time="700ms"/>
    The United States was losing the space race, <break time="200ms"/> and the military wanted something the whole world would see. <break time="500ms"/>
    Something so bright, <break time="200ms"/> it could be watched from every city on Earth. <break time="800ms"/>
    Their plan <break time="300ms"/> was to detonate a nuclear bomb <break time="300ms"/> on the Moon. <break time="700ms"/>
    For more than forty years, <break time="200ms"/> almost no one knew it had ever existed."""
}
outs = []
for name, body in SCRIPTS.items():
    (HERE / 'az_body.xml').write_text(f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US"><voice name="{VOICE}">'
        f'<prosody rate="-4%">{body}</prosody></voice></speak>', encoding='utf-8')
    out = HERE / f'lewis_{name}.mp3'
    code = subprocess.run(['curl', '-s', '-o', str(out), '-w', '%{http_code}', '--max-time', '120',
        '-H', f'Ocp-Apim-Subscription-Key: {KEY}', '-H', 'Content-Type: application/ssml+xml',
        '-H', 'X-Microsoft-OutputFormat: audio-48khz-192kbitrate-mono-mp3', '-H', 'User-Agent: tc-spike',
        '--data-binary', f'@{HERE / "az_body.xml"}',
        f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'], capture_output=True, text=True).stdout
    print(name, code); outs.append(out)
