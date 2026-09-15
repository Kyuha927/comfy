SAMPLE_SCORE = """X:1
T:
M:4/4
L:1/32
Q:1/4=120
V: Vocal clef=treble name=\"Vocal Melody\" snm=\"Vocal\"
V: Ins clef=treble name=\"Ins Melody\" snm=\"Inst.\"
K:C
% Verse
V: Vocal
\"C\"C8 D8 E8 G8|\"Am\"A8 G8 E8 D8|
V: Ins
C16 G16|A16 E16|
% Chorus
V: Vocal
\"F\"F8 A8 G8 E8|\"G\"G8 A8 G8 D8|
V: Ins
F16 C16|G16 D16|
"""

SAMPLE_JAZZ_SCORE = SAMPLE_SCORE.replace('"C"', '"Cmaj7"').replace(
    '"Am"', '"Am7"'
).replace('"F"', '"Fmaj7"').replace('"G"', '"G7"')

SAMPLE_STYLE = "Korean, cinematic piano pop, warm adult lead vocal, 120 BPM"
SAMPLE_LYRICS = """[Verse]
별빛이 닿지 않는 골목 끝에서
나는 오래된 이름을 천천히 불러

[Chorus]
다시 오는 계절을 기다리며
작은 숨결 하나를 노래해
"""
