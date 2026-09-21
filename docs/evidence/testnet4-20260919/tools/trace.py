"""Filters `docker logs -t` of a Node to the actors' trace events and collapses
repeats: hashes and per-attempt clocks are elided, and an event that repeats
keeps its first and last timestamp (UTC) and a count."""
import re, sys

first, last, count, order = {}, {}, {}, []
for line in sys.stdin:
    stamp, _, rest = line.rstrip("\n").partition(" ")
    if '"event"' not in rest or '"effect_reconcile"' in rest:
        continue
    key = re.sub(r"[0-9a-f]{24,}", "<hash>", rest)
    key = re.sub(r"(height|timestamp_ms|max_blocks): \d+", r"\1: _", key)
    key = re.sub(r"finalized clock \d+", "finalized clock _", key)
    if key not in first:
        first[key] = stamp[:19] + "Z"
        order.append(key)
    last[key] = stamp[:19] + "Z"
    count[key] = count.get(key, 0) + 1
for key in order:
    span = first[key] if count[key] == 1 else f"{first[key]}..{last[key]} x{count[key]}"
    print(span, key)
