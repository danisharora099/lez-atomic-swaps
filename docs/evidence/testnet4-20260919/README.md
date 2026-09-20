# Happy paths and refunds in both directions on public networks, 2026-09-19/20

Five BTC↔LEZ swaps between one Maker Node and one Taker Node on the **official
LEZ testnet** (v0.2.4) and **Bitcoin testnet4**, with Bitcoin served by **our own
Bitcoin Core 31.1** (no RPC provider; the provider route is recorded in
[`testnet3-provider-20260918`](../testnet3-provider-20260918/README.md)). No block
was mined by us and **no Maker action was ever requested**: `maker_actor_manual_actions`
holds no row for any of these swaps.

| # | Swap | Direction | Size | Outcome |
|---|---|---|---|---|
| 1 | [`b3bacad1…`](swaps/b3bacad10110.json) | TakerSellsLez | 10,000 sat / 10 LEZ | **completed** on both Nodes, 3 h 52 min |
| 2 | [`92c78b98…`](swaps/92c78b9867f9.json) | TakerSellsForeign | 10,000 sat / 10 LEZ | **completed** on both Nodes, 5 h 36 min |
| 3 | [`46bc2860…`](swaps/46bc286081d3.json) | TakerSellsForeign | 20,000 sat / 20 LEZ | both locked, Taker never claimed: **both legs refunded** |
| 4 | [`e5876dc7…`](swaps/e5876dc7869b.json) | TakerSellsLez | 10,000 sat / 10 LEZ | both locked, Taker never claimed: **both legs refunded** |
| 5 | [`0ffa32e3…`](swaps/0ffa32e3525b.json) | TakerSellsForeign | 10,000 sat / 10 LEZ | the Maker never locked; **Taker refund still open at this capture** (see below) |

Everything here was read from the two Nodes and the chains at the time in
`snapshot.json`. Every effect was sent exactly once (`attempt_count = 1` in both
actors' journals). The LEZ balances ended where they began (Maker 280, Taker 320):
two opposite trades and two refunds.

This run found **three defects and one profile mistake**, all fixed in the same pull
request (#88). They are the reason this folder is worth reading.

## What created what

"Node" means the role's Node acting on its own. A **request** is an owner-API call;
on the Taker side locking, claiming and asking for a refund are requests by design
(the drivers in [`tools/`](tools) send them). The Maker side is meant to need none,
and needed none.

### 1. `b3bacad1…` — Taker sells LEZ, completed

| Transaction | Chain | Created by | Trigger |
|---|---|---|---|
| Taker lock `5cf3ce65…` | LEZ, block 15,001 | Taker Node | request `taker_swap_lock_v1` |
| Maker lock [`cdbdbf35…`](https://mempool.space/testnet4/tx/cdbdbf35e71bc05631cf70feee70be8e11e433e73e4fd69db56ab731e7888e78) | Bitcoin, block 153,029 | Maker Node | none — unattended. Fee 3,100 sat (the #75 fallback rate; the same lock paid 56,064 sat in the run the review flagged) |
| Revealing claim [`c78702a9…`](https://mempool.space/testnet4/tx/c78702a982f92e4e732e517cf9134f61144048b58a301c6d64e951558027d5a5) | Bitcoin, block 153,032 | Taker Node | request `taker_swap_claim_v1`; key-path spend, 9,000 sat out |
| Follow-up claim `16409739…` | LEZ, block 15,177 | Maker Node | none — unattended |

### 2. `92c78b98…` — Taker sells BTC, completed

| Transaction | Chain | Created by | Trigger |
|---|---|---|---|
| Taker lock [`e18889a5…`](https://mempool.space/testnet4/tx/e18889a5525ab0afd749f239452f3ef5f2be78e4581ad374e67b0c238b6d6378) | Bitcoin, block 153,070 | Taker Node | request `taker_swap_lock_v1` |
| Escrow init `5056d5b7…`, Maker lock `0c734976…` | LEZ, blocks 15,653 / 15,717 | Maker Node | none — unattended |
| Revealing claim `c380283c…` | LEZ, block 15,784 | Taker Node | request `taker_swap_claim_v1` |
| Follow-up claim [`0ab53be3…`](https://mempool.space/testnet4/tx/0ab53be33505988aba014d123e4887d61ae654657b7c9d8524c317f7353c363d) | Bitcoin, block 153,100 | **Maker Node** | **none — unattended**; key-path spend, 9,000 sat out |

About three of its five and a half hours were spent waiting for a testnet4 block
that carried transactions: for long stretches every block there is coinbase-only.

### 3. `46bc2860…` — Taker sells BTC, both refunded

| Transaction | Chain | Created by | Trigger |
|---|---|---|---|
| Taker lock [`bea2d7a2…`](https://mempool.space/testnet4/tx/bea2d7a2cf3e10fc22257624d525714bbd186de003e3c34d51907e8b920c710a) | Bitcoin, block 153,052 | Taker Node | request `taker_swap_lock_v1` |
| Escrow init `a0334ecc…`, Maker lock `d8fa8555…` | LEZ, blocks 15,515 / 15,579 | Maker Node | none — unattended (finalized 28 minutes after the cutoff: the late-lock path of #68 projected it) |
| Maker refund `cc1970ee…` | LEZ, block 15,854 | **Maker Node** | **none — unattended**, once the earlier refund time was final |
| Taker refund [`ccd4f6a6…`](https://mempool.space/testnet4/tx/ccd4f6a66d7e417ed4d6e90f80fdf61ab2cf1b5c11ac3006c2dbb80fd110437d) | Bitcoin, block 153,198 | Taker Node | request `taker_swap_refund_v1` (admitted at 16:31:16Z on the 19th, replayed every ten minutes); the Node sent it at 07:03:38Z on the 20th, the moment it was eligible. Script-path spend (three-item witness), 19,000 sat out |

The Taker reads `refunded`. **The Maker's row is still open** (`maker_leg_refunded`,
waiting to see the Taker's refund): see defect B — the Maker has not been given that
fix yet, so as not to replace its image while swap 5 is open.

### 4. `e5876dc7…` — Taker sells LEZ, both refunded

| Transaction | Chain | Created by | Trigger |
|---|---|---|---|
| Taker lock `34ae69f3…` | LEZ, block 15,437 | Taker Node | request `taker_swap_lock_v1` |
| Maker lock [`e3399635…`](https://mempool.space/testnet4/tx/e3399635d8b9d4d5f3498e32edec8e5760dd1b6b59126b04ff891d3dce0605ca) | Bitcoin, block 153,058 | Maker Node | none — unattended |
| Maker refund [`dad58282…`](https://mempool.space/testnet4/tx/dad582823a79d06f5205ba82b4d98a6d3f8be12a919249c520427f44fa37fd8d) | Bitcoin, block 153,204 | **Maker Node** | **none — unattended**: `Immature` 2,330 times, `Eligible` once at 07:39:25Z on the 20th, sent in the same second. Script-path spend, 9,000 sat out |
| Taker refund `9d042341…` | LEZ, block 16,902 | Taker Node | request `taker_swap_refund_v1`: refused as `taker_action_unavailable` 92 times from 16:29Z on the 19th, **admitted at 07:49:54Z on the 20th**, six minutes after the Taker Node saw the Maker's refund confirmed |

Those 92 refusals are the design: once the claim window is closed and both legs are
locked, the Taker Node offers its refund only after the Maker's leg is refunded. But
see defect C: on chain, nothing held the Taker's LEZ back for those 15 hours.

### 5. `0ffa32e3…` — the Maker never locked (open)

| Transaction | Chain | Created by | Trigger |
|---|---|---|---|
| Taker lock [`04ecab7a…`](https://mempool.space/testnet4/tx/04ecab7ab5c0f1fc11f3aece54dc9df68e42beef312e4ace8143ec96b6980c97) | Bitcoin, block 153,052 | Taker Node | request `taker_swap_lock_v1` |
| Taker refund | Bitcoin | — | request `taker_swap_refund_v1` admitted 10:17:58Z on the 19th; **not sent yet** (profile mistake D) |

This was meant to be the happy swap and became a refund run because of defect A.

## What this run found

**A. A Maker accepted a swap it could not serve (fixed, `92d6a19`).** Swaps 3 and 5
were started five minutes apart: an operator mistake that exposed a real gap. A Maker prepares its
LEZ escrows one at a time and each waits out LEZ finality, about two hours here. It
served swap 3, could not reach swap 5 before its cutoff, and had accepted it anyway:
the Taker locked 10,000 sat for a Maker lock that could not come. A Maker now
refuses such a reservation before the Taker commits anything. Swap 2 was then
started alone.

**B. A reorganisation made a lock unrefundable (fixed, `d36fac7`).** testnet4 had a
nine-block reorg at 08:38:46Z on the 19th. Swap 3's lock, planned at anchor 153,053,
was mined at 153,052, and the adapter treated a confirmation below the anchor as
impossible: `FundingAnchorMismatch`, "uncertain: no send", for good. The refund now
waits for the height both roles signed instead. It was deployed to the Taker only
(intervention 1); without it `ccd4f6a6…` would never have been sent. The Maker still
runs the old code and shows the same error 5,643 times in
[`maker-actor-trace.txt`](maker-actor-trace.txt) while it looks for that refund —
which is why its row for swap 3 is open. Its own funds are long back.

**C. Nothing checked the order of the two refunds (fixed, `cfd0657`).** This run
used the profile of the first public runs: LEZ refunds at 6 and 9 hours, one Bitcoin
refund delay of 144 blocks for both directions. In swap 4 the Taker's LEZ refund was
therefore open on chain from 16:20Z on the 19th while the Maker's Bitcoin refund
matured only at block 153,202, fifteen hours later — and a Bitcoin claim has no
deadline. Our Taker Node refuses (the 92 refusals above); a modified one could have
refunded its LEZ and still claimed the Bitcoin. The delay is now per direction and a
Node refuses to load a profile whose block counts break the order its times promise.
The corrected testnet profile is 96 / 37 blocks with the later refund at 16 hours.

**D. The testnet profile holds swap 5's refund back (fixed, `4fba3fc`, configuration).**
A Taker whose Maker never locked refunds only once its whole LEZ discovery window is
finalized; that is what proves the lock absent. The profile kept the 2,048-block
default, 34 hours at this network's block a minute. Swap 5's Bitcoin refund has been
`Eligible` since 07:39Z on the 20th ([`taker-actor-trace.txt`](taker-actor-trace.txt))
and waits for LEZ block 17,413 to be final, about 18:00Z. Nothing is at risk while it
waits — the Node sends nothing — and it is left to resolve on its own; this folder
will be updated when it does. New swaps use 480 blocks.

## Every intervention

1. **Taker Node image replaced at 20:49Z on the 19th** (`v024-stack2` → `v024-stack3`,
   source `d36fac7`) to deploy fix B. No swap state was touched and the image
   authorises no transaction. The Taker container's earlier log went with it, so
   `taker-actor-trace.txt` starts there. The Maker container ran untouched from
   before swap 1 to this capture.
2. **One probe request**, `taker_swap_refund_v1` with id `probe-e5876dc7-status`, sent
   by hand on the 19th to read swap 4's refusal. It was refused like the driver's.
3. **Drivers restarted.** Swap 5's driver was the happy-path one; when the swap
   turned into a refund run it was replaced by
   [`tools/testnet-refund-resume.py`](tools/testnet-refund-resume.py) (`RESUMED` in its
   log), which only asks for the Taker's refund.
4. **A first attempt at swap 3 moved no funds**
   ([`testnet4-refund-TakerSellsForeign-refused-by-fee-policy.txt`](testnet4-refund-TakerSellsForeign-refused-by-fee-policy.txt)):
   at 10,000 sat the Taker's wallet had only unconfirmed change to spend, the lock
   priced at 4,240 sat, and the #75 fee policy refused a fee above 40% of the value.
   The driver shows only `initiation_execution_unavailable`; the reason was read in
   the Taker Node's log, which intervention 1 discarded. It was retried at 20,000 sat.

## Verification

`bitcoin_verification` in each record is `getrawtransaction` on our Core: block,
inputs, outputs and witness size. Claims spend with a **one-item witness** (Taproot
key path, the adaptor-signature claim); refunds with **three items** (script path,
after the CSV delay). `lez_verification` looks every LEZ transaction up on the public
sequencer (`testnet.lez.logos.co` through the local proxy; the SHA-256 of the returned
bytes is kept) and on the finalized indexer: all are found on both.

## Files, and what wrote each

| File | Written by |
|---|---|
| `swaps/*.json`, `snapshot.json` | [`tools/collect.py`](tools/collect.py), read-only: the Taker's view, the Maker's monitor, scheduler and manual-action rows, both actors' evidence kinds and effect journals (SQLite opened `mode=ro` inside each Node container), then the Bitcoin lookups. [`tools/verify-lez.py`](tools/verify-lez.py) adds `lez_verification`. No key, nonce, adaptor secret or evidence payload is read |
| `maker-actor-trace.txt`, `taker-actor-trace.txt` | `docker logs -t` of each Node container through [`tools/trace.py`](tools/trace.py): the actors' `LEZ_BTC_ACTOR_TRACE` events with hashes and per-attempt clocks elided, a repeated event collapsed to its first and last timestamp (UTC) and a count |
| `testnet4-*.txt` | stdout of the drivers (bracketed timestamps are local, UTC+2; the others UTC) |
| `tools/testnet-swap.py`, `testnet-refund.py`, `testnet-refund-resume.py` | the drivers. They import the helpers of `deploy/scripts/node-e2e.py`, mine nothing and never call a Maker action. The refund driver lets both roles lock, never claims, and asks for the Taker's refund every ten minutes from the later refund time on |
| `provenance.json`, `SHA256SUMS` | generated at the end of the capture |
