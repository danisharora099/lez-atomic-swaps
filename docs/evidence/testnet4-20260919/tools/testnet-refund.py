"""Both legs lock, the Taker never claims, both legs refund — on the public networks
(official LEZ testnet + Bitcoin testnet4, our own Bitcoin Core), through the two
Nodes' owner APIs. No mining and no Maker action: the Maker's refund is left to its
Node. The Taker's refund is a request by design; it is sent once the later refund
time has passed and the same request id is replayed until the swap is refunded.
Usage: testnet-refund.py <node-e2e.py> <direction> [sat]"""
import importlib.util, json, sys, time
E2E, DIRECTION = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("e2e", E2E)
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
e.NODES = {"maker": ("lez-testnet-maker-node", "/run/lez/maker/node.sock"),
           "taker": ("lez-testnet-taker-node", "/run/lez/taker/node.sock")}
e.FOREIGN_UNITS = int(sys.argv[3]) if len(sys.argv) > 3 else 10_000   # sat
e.LEZ_UNITS = e.FOREIGN_UNITS // 1000                                   # 1 LEZ per 1,000 sat
e.mine = lambda blocks: None
e.ROUTE["direction"] = DIRECTION
e.REVERSE = DIRECTION == "TakerSellsLez"
now = lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
stamp = "refund-" + str(int(time.time()))
print("START refund", DIRECTION, now(), flush=True)
offer = e.publish_offer(stamp)
swap_id, _ = e.take(offer, stamp)
taken = time.time()
print("SWAP", swap_id, flush=True)
print("LOCK", e.lock(swap_id), flush=True)
view = e.wait_taker(swap_id, {"claim_available"}, timeout=10 * 3600)
terms = view.get("terms") or {}
later = int(terms.get("later_refund_earliest_unix_seconds") or taken + 32400)
print("BOTH_LOCKED", now(), "the Taker never claims; later refund time", time.strftime("%H:%M:%SZ", time.gmtime(later)),
      "bitcoin refund height", terms.get("bitcoin_refund_height"), flush=True)
last, attempt, deadline = None, 0, time.time() + 80 * 3600
while time.time() < deadline:
    taker, maker = e.taker_view(swap_id), e.maker_phase(swap_id)
    state = (taker["state"], maker)
    if state != last:
        print("STATE", now(), "taker", taker["state"], "gen", taker["progress_generation"], "| maker", maker, flush=True)
        last = state
    if taker["state"] == "refunded" and maker in {"refunded", "completed", "terminal"}:
        break
    if taker["state"] in {"completed", "attention_required"}:
        raise SystemExit(f"FAILED: taker ended in {taker['state']}")
    if time.time() > later + 120 and taker["state"] != "refunded":
        attempt += 1
        reply = e.rpc("taker", "taker_swap_refund_v1", {"schema_version": 1, "request_id": f"e2e-{stamp}",
                      "swap_id": swap_id, "expected_generation": taker["progress_generation"]}, timeout=300)
        what = "admitted" if "result" in reply and not reply["result"].get("was_replay") else \
               "replayed" if "result" in reply else (reply["error"].get("data") or {}).get("category")
        if attempt == 1 or what == "admitted" or attempt % 12 == 0:
            print("TAKER_REFUND_REQUEST", now(), "attempt", attempt, what, flush=True)
    time.sleep(600)
else:
    raise SystemExit("FAILED: not refunded within 80 h")
print("BOTH_REFUNDED", now(), flush=True)
