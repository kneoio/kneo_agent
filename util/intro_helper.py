import random

def get_random_ad_intro() -> str:
   ad_intros = [
       "And now, a word from our sponsors",
       "Let's take a quick commercial break",
       "Time to hear from our partners",
       "Here's a message from our supporters",
       "We'll be right back after this",
       "A quick message from our advertisers",
       "Now for something special from our sponsors",
       "Let's pause for our commercial partners",
       "Time for a brief sponsor message",
       "Here's an important message from our friends",
       "ADVERTISEMENT!!"
   ]
   return random.choice(ad_intros)