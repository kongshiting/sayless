from nrclex import NRCLex

text = "my dad left me"

emotion = NRCLex(text)
print(emotion.affect_frequencies)  # emotion scores
