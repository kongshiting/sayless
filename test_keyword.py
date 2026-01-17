from keyword_phrases import extract_key_phrases

tests = ["So today was really tiring. I woke up late and missed my alarm, so I had to rush to get ready. Then I realized I forgot my keys and had to run back home. It was raining too which made everything worse. By the time I reached the office I was completely stressed and exhausted."
]
for t in tests:
    print("\nINPUT:", t)
    print("OUTPUT:", extract_key_phrases(t))


# INPUT: omg let me tell you, my sister found out that her finance cheated on her yesterday my house was a ruckus and everyone was screaming because the wedding is literally the next day
# OUTPUT: ['let tell', 'sister', 'finance cheated', 'yesterday house', 'ruckus', 'everyone', 'screaming', 'wedding', 'next day']

# INPUT: work is so tiring today somewhere start raining after lunch, the weather so nice to sleep i wanted to go home so bad
# OUTPUT: ['work', 'tiring', 'raining after lunch', 'weather', 'sleep wanted', 'go home', 'bad']

# INPUT: i'm so sorry i just woke up i missed my alarm so i will be late. let me faster brush teeth and then run to the bus
# OUTPUT: ['sorry', 'woke', 'missed alarm', 'will late', 'faster brush teeth', 'run bus']