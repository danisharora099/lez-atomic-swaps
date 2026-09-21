"""One swap on the public networks (official LEZ testnet + Bitcoin testnet4) through
the two Nodes' owner APIs: no mining, no Maker action. Usage: testnet-swap.py <e2e> <direction>"""
import importlib.util, sys, time
E2E, DIRECTION = sys.argv[1], sys.argv[2]
spec = importlib.util.spec_from_file_location("e2e", E2E)
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
e.NODES = {"maker": ("lez-testnet-maker-node", "/run/lez/maker/node.sock"),
           "taker": ("lez-testnet-taker-node", "/run/lez/taker/node.sock")}
e.FOREIGN_UNITS = 10_000
e.LEZ_UNITS = 10
e.mine = lambda blocks: None
e.ROUTE["direction"] = DIRECTION
e.REVERSE = DIRECTION == "TakerSellsLez"
stamp = str(int(time.time()))
print("START", DIRECTION, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), flush=True)
offer = e.publish_offer(stamp)
swap_id, _ = e.take(offer, stamp)
print("SWAP", swap_id, flush=True)
print("LOCK", e.lock(swap_id), flush=True)
view = e.wait_taker(swap_id, {"claim_available"}, timeout=10 * 3600)
print("CLAIM_AVAILABLE gen", view["progress_generation"], flush=True)
e.claim(swap_id, stamp)
print("TAKER_CLAIM_REQUESTED", flush=True)
e.wait_taker(swap_id, {"completed"}, timeout=10 * 3600)
print("TAKER_COMPLETED", flush=True)
e.wait_completed(swap_id, timeout=10 * 3600)
print("BOTH_COMPLETED", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), flush=True)
