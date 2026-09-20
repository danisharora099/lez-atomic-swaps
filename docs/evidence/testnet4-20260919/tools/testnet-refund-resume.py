"""Follows one already locked swap to its refund on the public networks: logs every
state change of both Nodes and, for the Taker, sends `taker_swap_refund_v1` (a request
by design) and replays the same request id until the swap reads refunded. No mining,
no Maker action. Usage: testnet-refund-resume.py <node-e2e.py> <swap_id> <label>"""
import importlib.util, sys, time
E2E, SWAP, LABEL = sys.argv[1:4]
spec = importlib.util.spec_from_file_location("e2e", E2E)
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
e.NODES = {"maker": ("lez-testnet-maker-node", "/run/lez/maker/node.sock"),
           "taker": ("lez-testnet-taker-node", "/run/lez/taker/node.sock")}
now = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
print("RESUMED for refund", LABEL, SWAP, now(), flush=True)
last, attempt, deadline = None, 0, time.time() + 80 * 3600
while time.time() < deadline:
    taker, maker = e.taker_view(SWAP), e.maker_phase(SWAP)
    state = (taker["state"], maker)
    if state != last:
        print("STATE", now(), "taker", taker["state"], "gen", taker["progress_generation"], "| maker", maker, flush=True)
        last = state
    if taker["state"] == "refunded":
        break
    if taker["state"] in {"completed", "attention_required"}:
        raise SystemExit(f"FAILED: taker ended in {taker['state']}")
    attempt += 1
    reply = e.rpc("taker", "taker_swap_refund_v1", {"schema_version": 1, "request_id": f"e2e-refund-{SWAP[:16]}",
                  "swap_id": SWAP, "expected_generation": taker["progress_generation"]}, timeout=300)
    what = "admitted" if "result" in reply and not reply["result"].get("was_replay") else \
           "replayed" if "result" in reply else (reply["error"].get("data") or {}).get("category")
    if attempt == 1 or what == "admitted" or attempt % 12 == 0:
        print("TAKER_REFUND_REQUEST", now(), "attempt", attempt, what, flush=True)
    time.sleep(600)
else:
    raise SystemExit("FAILED: not refunded within 80 h")
print("TAKER_REFUNDED", now(), flush=True)
