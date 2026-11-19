# Spike (throwaway): can free Azure voices act short CHARACTER lines?
# 3 characters x 2 takes (a voice with emotion styles vs the HD voice), joined into one file with gaps.
# Usage: python -I azure_character_test.py
import pathlib, subprocess

HERE = pathlib.Path(__file__).parent
env = dict(l.strip().split('=', 1) for l in pathlib.Path('C:/Users/User/capitalcode/.env.local').read_text().splitlines()
           if '=' in l and not l.startswith('#'))
KEY, REGION = env['AZURE_SPEECH_KEY'].strip('"'), env['AZURE_SPEECH_REGION'].strip('"')

def styled(voice, style, degree, inner):
    return f'<voice name="{voice}"><mstts:express-as style="{style}" styledegree="{degree}">{inner}</mstts:express-as></voice>'
def plain(voice, inner):
    return f'<voice name="{voice}">{inner}</voice>'

LINES = [
    # Leonidas, defiant, low and slow
    ('1_leonidas_davis', styled('en-US-DavisNeural', 'unfriendly', 2, '<prosody rate="-3%" pitch="-4%">Come <break time="250ms"/> and take them.</prosody>')),
    ('2_leonidas_hd', plain('en-US-Andrew:DragonHDLatestNeural', '<prosody rate="-3%" pitch="-8%">Come <break time="300ms"/> and take them.</prosody>')),
    # Themistocles, whispering a secret
    ('3_themis_davis', styled('en-US-DavisNeural', 'whispering', 2, '<prosody rate="-3%">Tell the King <break time="400ms"/> the Greeks are running.</prosody>')),
    ('4_themis_hd', plain('en-US-Andrew:DragonHDLatestNeural', '<prosody rate="-3%" volume="-30%">Tell the King <break time="400ms"/> the Greeks are running.</prosody>')),
    # 1958 general, cold and certain
    ('5_general_tony', styled('en-US-TonyNeural', 'unfriendly', 1.5, '<prosody rate="-3%" pitch="-8%">Gentlemen. <break time="600ms"/> We are going to hit the Moon.</prosody>')),
    ('6_general_hd', plain('en-US-Brian:DragonHDLatestNeural', '<prosody rate="-3%" pitch="-6%">Gentlemen. <break time="600ms"/> We are going to hit the Moon.</prosody>')),
]
outs = []
for name, voice_xml in LINES:
    (HERE / 'az_body.xml').write_text(f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">{voice_xml}</speak>', encoding='utf-8')
    out = HERE / f'charN_{name}.wav'
    code = subprocess.run(['curl', '-s', '-o', str(out), '-w', '%{http_code}', '--max-time', '120',
        '-H', f'Ocp-Apim-Subscription-Key: {KEY}', '-H', 'Content-Type: application/ssml+xml',
        '-H', 'X-Microsoft-OutputFormat: riff-48khz-16bit-mono-pcm', '-H', 'User-Agent: tc-spike',
        '--data-binary', f'@{HERE / "az_body.xml"}',
        f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'], capture_output=True, text=True).stdout
    print(name, code); outs.append(out)

# join: each take followed by 1.2 s of silence
args, fc = [], ''
for i, o in enumerate(outs):
    args += ['-i', str(o)]; fc += f'[{i}]apad=pad_dur=1.2[a{i}];'
fc += ''.join(f'[a{i}]' for i in range(len(outs))) + f'concat=n={len(outs)}:v=0:a=1[out]'
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *args, '-filter_complex', fc, '-map', '[out]', str(HERE / 'character_voices_natural.mp3')])
print('joined ->', HERE / 'character_voices_natural.mp3')
