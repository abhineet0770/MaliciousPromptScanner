"""
Patch: Add core dangerous phrases to keywords.json
These are fundamental harmful phrases that should always be detected.
"""
import json
from pathlib import Path

keywords_path = Path("data/keywords.json")
data = json.load(open(keywords_path, 'r'))

# Core dangerous phrases that must ALWAYS be detected
core_violence = [
    'how to kill', 'how to murder', 'how to hurt someone', 'how to harm someone',
    'how to kill someone', 'how to kill a person', 'how to murder someone',
    'kill someone', 'murder someone', 'hurt someone', 'harm someone',
    'how to attack someone', 'how to assault someone', 'attack someone',
    'how to stab', 'how to strangle', 'how to suffocate',
    'how to poison someone', 'how to stalk someone',
    'make someone disappear', 'get rid of someone',
    'how to beat someone', 'how to kidnap', 'kidnap someone',
    'torture someone', 'how to torture',
]

core_illegal = [
    'how to steal', 'how to rob', 'how to shoplift',
    'how to steal something', 'how to steal from',
    'steal from someone', 'rob someone', 'rob a bank', 'rob a store',
    'how to pickpocket', 'how to burglarize', 'how to break into a house',
    'how to hotwire', 'how to forge', 'how to counterfeit',
    'how to commit fraud', 'how to evade taxes', 'how to blackmail',
    'how to bribe', 'how to smuggle', 'how to traffic',
    'how to make drugs', 'how to cook meth', 'how to grow weed illegally',
    'how to make a bomb', 'how to build a weapon',
    'buy drugs online', 'buy weapons illegally',
]

core_hacking = [
    'how to hack', 'hack someone', 'hack into',
    'how to hack wifi', 'how to hack a phone', 'how to hack an account',
    'how to hack instagram', 'how to hack facebook', 'how to hack email',
    'crack a password', 'crack someone password',
    'how to spy on someone', 'spy on someone phone',
    'how to ddos', 'how to dos attack',
]

core_self_harm = [
    'how to kill myself', 'how to hurt myself',
    'ways to die', 'best way to die',
    'how to commit suicide', 'how to end my life',
    'painless ways to die', 'how to self harm',
]

# Merge without duplicates
for phrase in core_violence:
    if phrase not in data.get('violence', []):
        data.setdefault('violence', []).append(phrase)

for phrase in core_illegal:
    if phrase not in data.get('illegal', []):
        data.setdefault('illegal', []).append(phrase)

for phrase in core_hacking:
    if phrase not in data.get('hacking', []):
        data.setdefault('hacking', []).append(phrase)

for phrase in core_self_harm:
    if phrase not in data.get('self_harm', []):
        data.setdefault('self_harm', []).append(phrase)

# Save
with open(keywords_path, 'w') as f:
    json.dump(data, f, indent=2)

print("[OK] Core dangerous phrases added to keywords.json")

# Verify
for test in ['how to kill someone', 'how to steal something', 'how to hack wifi', 'how to kill myself']:
    prompt_lower = test.lower()
    found = False
    for cat, kws in data.items():
        for kw in kws:
            if kw in prompt_lower:
                found = True
                print(f"  [OK] '{test}' -> matched '{kw}' [{cat}]")
                break
        if found:
            break
    if not found:
        print(f"  [FAIL] '{test}' -> NOT DETECTED")
