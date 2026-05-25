import sys

path = r'C:\Users\Violet\.claude\yukibot\data\full_archive.json'

with open(path, 'r', encoding='utf-8') as f:
    raw = f.read()

# Fix unescaped double quotes inside JSON string values using a state machine
def fix_json_strings(s):
    result = []
    i = 0
    in_string = False
    escape_next = False
    # Track if we're inside a key (to know when value strings start)
    # We'll just escape any bare " that appears inside a string, replacing with \"
    # But we need to NOT double-escape already-escaped ones

    while i < len(s):
        c = s[i]
        if escape_next:
            result.append(c)
            escape_next = False
            i += 1
            continue

        if c == '\\' and in_string:
            result.append(c)
            escape_next = True
            i += 1
            continue

        if c == '"':
            if not in_string:
                # Opening quote
                in_string = True
                result.append(c)
            else:
                # Could be closing quote or unescaped inner quote
                # Look ahead: if followed by whitespace then : or , or } or ]
                # it's likely a closing quote
                rest = s[i+1:].lstrip()
                if rest and rest[0] in ':,}]':
                    # Closing quote
                    in_string = False
                    result.append(c)
                elif rest == '' or rest[0] == '\n':
                    # End of value
                    in_string = False
                    result.append(c)
                else:
                    # Unescaped inner quote — escape it
                    result.append('\\')
                    result.append('"')
        else:
            result.append(c)
        i += 1

    return ''.join(result)

fixed = fix_json_strings(raw)

import json
try:
    data = json.loads(fixed)
    print(f"Fixed! Total entries: {len(data)}")
except json.JSONDecodeError as e:
    print(f"Still broken at line {e.lineno}, col {e.colno}: {e.msg}")
    lines = fixed.split('\n')
    print(repr(lines[e.lineno-1][max(0,e.colno-30):e.colno+30]))
    sys.exit(1)

# Save backup of original
with open(path + '.bak', 'w', encoding='utf-8') as f:
    f.write(raw)

# Filter to today and save
today = [e for e in data if str(e.get('ts', '')).startswith('2026-04-01')]
print(f"Today's entries: {len(today)} (was {len(data)} total)")

with open(path, 'w', encoding='utf-8') as f:
    json.dump(today, f, ensure_ascii=False, indent=2)
print("Done. Original backed up to full_archive.json.bak")
