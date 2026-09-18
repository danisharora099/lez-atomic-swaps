"""One forward swap on the public networks through the Node API, no mining,
no manual Maker claim: it only waits, so the Maker's follow-up is unattended."""
import importlib.util, sys, time, json
spec = importlib.util.spec_from_file_location("e2e", "/Users/mandrigin/Desktop/las-logos/lez-atomic-swaps-testnet/deploy/scripts/node-e2e.py")
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
e.NODES = {"maker": ("lez-testnet-maker-node", "/run/lez/maker/node.sock"),
           "taker": ("lez-testnet-taker-node", "/run/lez/taker/node.sock")}
e.FOREIGN_UNITS = 10_000
e.LEZ_UNITS = 10
e.mine = lambda blocks: None
stamp = str(int(time.time()))
offer = e.publish_offer(stamp)
swap_id, _ = e.take(offer, stamp)
print("SWAP", swap_id, flush=True)
txid = e.lock(swap_id)
print("LOCK", txid, flush=True)
view = e.wait_taker(swap_id, {"claim_available"}, timeout=6*3600)
print("CLAIM_AVAILABLE gen", view["progress_generation"], flush=True)
e.claim(swap_id, stamp)
print("TAKER_CLAIM_REQUESTED", flush=True)
e.wait_taker(swap_id, {"completed"}, timeout=6*3600)
print("TAKER_COMPLETED", flush=True)
