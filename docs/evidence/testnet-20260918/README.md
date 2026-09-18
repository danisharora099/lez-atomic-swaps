# Public-network swap evidence, 2026-09-15 → 2026-09-18

Five BTC↔LEZ swaps between one Maker Node and one Taker Node on the **official
LEZ testnet** (v0.2.4, channel `0101…01`, escrow program `c22d61fc…`) and
**Bitcoin testnet4**. Two completed during the recorded run, two hit the
late-Maker-lock failure and refunded on both chains, and a fifth — run to trace
the "Maker's follow-up claim does not fire" finding — completed with no manual
action.

Everything here was read from the two Nodes and from the chains on
2026-09-18 (`snapshot.json` has the capture time, the Bitcoin tip, and both
wallets). Nothing was reconstructed from memory: every transaction id below is
in a Node's own durable record **and** was confirmed against its chain.

| Swap | Direction | Size | Outcome |
|---|---|---|---|
| [`fed3bb4c…`](swaps/fed3bb4cf2d5.json) | TakerSellsForeign | 10,000 sat / 100 LEZ | completed (Maker claim under an open manual action) |
| [`3ceef033…`](swaps/3ceef033952a.json) | TakerSellsLez | 10,000 sat / 100 LEZ | completed (Maker claim under an open manual action) |
| [`54184a0e…`](swaps/54184a0ecd6d.json) | TakerSellsLez | 10,000 sat / 100 LEZ | refunded, both legs |
| [`de229f88…`](swaps/de229f888d75.json) | TakerSellsForeign | 10,000 sat / 100 LEZ | refunded, both legs |
| [`158065f1…`](swaps/158065f18765.json) | TakerSellsForeign | 10,000 sat / 10 LEZ | **completed, no manual action** |

## What created what

"Node" means the role's Node acting on its own (its observer or its supervised
actor). A **request** is an owner-API call someone made; the Node then builds,
signs and sends the transaction. Locking, claiming and asking for a refund are
requests by design on the Taker side. The Maker side is meant to need none.

### `158065f1…` — the traced swap (2026-09-17/18)

| Transaction | Chain | Created by | Trigger |
|---|---|---|---|
| Taker lock [`83fb4d15…`](https://mempool.space/testnet4/tx/83fb4d15ad954e04fc6d9852d6d74697465eb7369a0801a50f27710f961bee8a) | Bitcoin, block 152860 | Taker Node | request `taker_swap_lock_v1`, sent by [`tools/traced-swap.py`](tools/traced-swap.py) |
| Escrow init `4ff3636d…` | LEZ | Maker Node | none — unattended, after the Taker lock confirmed |
| Maker lock (fund) `6e95542b…` | LEZ | Maker Node | none — unattended, once the init finalized, before the 16:32Z cutoff |
| Revealing claim `96a73008…` | LEZ | Taker Node | request `taker_swap_claim_v1`, sent by the same script when the Taker reached `claim_available` |
| Follow-up claim [`c6f241d6…`](https://mempool.space/testnet4/tx/c6f241d6ee096a943a8f9424634f5ea0b21831699af3469db29de00b30f358ff) | Bitcoin, block 152882 | **Maker Node** | **none — unattended.** `maker_actor_manual_actions` holds no row for this swap; the trace shows the claim prepared and sent on the Maker's first attempt at revision 3 (19:21:12Z) |

Two interventions were made during this swap, neither of which sends or
authorises a transaction:

1. **Scheduler row re-queued (2026-09-17 ~18:20Z).** The Maker's lock was
   observed after its cutoff, its supervisor ran `recover`, and the bug fixed in
   #68 marked the swap `failed: actor_output_invalid` (trace, 17:23:51Z). The
   operator ran [`tools/revive-maker-row.sh`](tools/revive-maker-row.sh): one
   `UPDATE` setting that row back to `queued` — what a correct requeue would have
   left. It was used instead of `maker_actor_claim_v1` precisely so that the
   attempts at revision 3 stayed automatic.
2. **Logos node restarted (19:19Z).** The local follower of the public L1 froze
   its slot counter (every block "from a future slot") and the indexer's
   finalized height stalled for about two hours. A container restart cleared it.
   This delayed the swap; it touched no swap state.

### `fed3bb4c…` and `3ceef033…` — the recorded run (2026-09-16)

Locks and revealing claims: Taker Node on `taker_swap_lock_v1` /
`taker_swap_claim_v1`, requested by the desk runner (`ui-e2e.sh happy`). Maker
locks: Maker Node, unattended.

The Maker follow-up claims (`31450ab2…` Bitcoin, `1c5031d8…` LEZ) were sent by
the Maker Node's supervised actor, each **while an operator's
`maker_actor_claim_v1` was open** (queued 05:24Z and 13:26Z on 09-16; rows in
each record's `maker.manual_actions`). Each claim has `attempt_count = 1`, so it
was sent exactly once, but the Node keeps no send timestamp and the Maker could
not be traced then, so these two swaps cannot show whether the send preceded the
manual action. They are **not** evidence of unattended operation; `158065f1…`
is.

### `54184a0e…` — late Maker lock, refunded (2026-09-16/17)

| Transaction | Created by | Trigger |
|---|---|---|
| Taker lock `8a0fd978…` (LEZ) | Taker Node | request, desk runner |
| Maker lock [`e985ac09…`](https://mempool.space/testnet4/tx/e985ac091f84e2bc3d8a04d35196a8f14bf36c927adcde30aa99467c66a23d1b) (Bitcoin, block 152652) | Maker Node | unattended; included 449 s after the cutoff by block time, timely by median time |
| Maker refund [`87ed467b…`](https://mempool.space/testnet4/tx/87ed467b8932d38a33280758843967b83828bada7305821cfb7a6a8ebe935b84) (Bitcoin, block 152799) | Maker Node's actor | sent while an operator's `maker_actor_refund_v1` (queued 09-16 16:49Z) was open — not evidence of unattended operation |
| Taker refund `78f9be26…` (LEZ) | the Taker's actor binary, **invoked by hand** (`lez-btc-taker-actor … drive`, then `recover`) on 09-17 | the Node's observer was frozen by the bugs fixed in #64, so it never sent this itself |
| Terminal projection `refunded` | **Taker Node, unattended** | after the #64 build was deployed the observer accepted the refund it had been rejecting (`refund_found#4`) and projected generation 3 → 4 |

### `de229f88…` — late Maker lock, refunded (2026-09-16/18)

| Transaction | Created by | Trigger |
|---|---|---|
| Taker lock `550710c2…` (Bitcoin, block 152744) | Taker Node | request, desk runner |
| Escrow init `144c9fd6…`, Maker lock `b986d284…` (LEZ) | Maker Node | unattended |
| Maker refund `283c640a…` (LEZ) | **Maker Node, unattended** | no manual action row exists for this swap |
| Taker refund [`6fe2951c…`](https://mempool.space/testnet4/tx/6fe2951cdd0d59831ae53a550f68107ea9148007c1595f04b5a3cc479f79a27e) (Bitcoin, block 152898) | **Taker Node, unattended send** | the refund was *requested* once (`taker_swap_refund_v1`, request id `recover-de229f88-1`, 09-17) — a Taker request by design. The Node prepared it, polled the CSV (`Immature`) through a host crash and restart, broadcast it at 21:22Z when height 152886 arrived, and projected `refunded` |

### Maker-side projections left behind

The Maker's rows for `54184a0e…` and `de229f88…` read `failed:
actor_deployment_invalid` and its actors stop at `maker_leg_refunded` /
`both_legs_locked`. That is an artefact of this investigation, not of the swaps:
each Maker swap pins the SHA-256 of the actor binary it was created with, and
the Maker image was replaced with the trace build while they were open. Both
Maker legs had been refunded on chain before that; only the Maker's own
projection of the Taker's refund is missing. (That an actor fix can never reach
an open Maker swap is recorded in #67.)

## Verification

Each record's `bitcoin_verification` is `getrawtransaction` on our own Bitcoin
Core 31.1 (testnet4, `txindex`): confirmations, block, the outpoint spent and
the outputs. Every claim and refund spends exactly the lock it should: claims
are Taproot key-path spends (one witness item), refunds script-path CSV spends
(signature, script, control block), each returning 9,000 of the 10,000 sat
locked (1,000 sat fee). `lez_verification` looks each LEZ
transaction up twice — on the **public sequencer** (`testnet.lez.logos.co`,
through the local proxy; the SHA-256 of the returned bytes is recorded) and on
the **finalized indexer**. All 13 LEZ transactions are found on both.

`snapshot.json` has both wallets at capture time; the Taker holds 310 LEZ —
300 after the two refunds returned its principal, plus the 10 claimed in the
traced swap.

## Which software produced this

| Period | Nodes |
|---|---|
| Recorded run, 09-15/16 | `lez-{maker,taker}-node:testnet`, built from this branch at `aef7567` |
| 09-17, Taker only | the same plus the #64 fixes (late lock, observer, `refund_found#4`) |
| 09-17 13:30Z onward, both | the **trace build**: `aef7567` + [`diagnostic-build.patch`](diagnostic-build.patch) — the #64 fixes, the supervisor passing `LEZ_BTC_ACTOR_TRACE`/stderr to the Maker's actor, and trace notes naming why a claim attempt returned. It deliberately does **not** contain the #68 fix, which is why the strand reproduced |

Binary hashes and image ids are in [`provenance.json`](provenance.json). Side
services: Bitcoin Core 31.1 (`lez-bitcoin-core:local`), Logos Blockchain node
`:testnet`, LEZ v0.2.4 `indexer_service`, nginx proxy to the public sequencer —
launched as in `docs/testnet-run.md` §2–5.

## Files, and what wrote each

| File | Written by |
|---|---|
| `swaps/<id>.json` | [`tools/collect.py`](tools/collect.py), read-only: the Taker's `taker_swap_list_v1` view (state, effects, signed terms), the Maker's `maker_actor_monitor_v1`, the Maker's scheduler and manual-action rows, both actors' evidence kinds, effect journals and lock steps (SQLite opened `mode=ro` inside each Node container), then the chain lookups above. No key, nonce, adaptor secret or evidence payload is read |
| `snapshot.json` | the same run of `collect.py`: capture time, Bitcoin tip, both Nodes' `*_wallet_balances_v1` |
| `maker-actor-trace.txt`, `taker-actor-trace.txt` | `docker logs -t` of each Node container since the 09-17 13:30Z deploy, filtered to the actors' `LEZ_BTC_ACTOR_TRACE` events. Identical events are collapsed to their first timestamp (UTC) and a count; per-attempt block hashes are elided so repeats collapse. The Maker's covers `158065f1…` end to end |
| `traced-swap-driver.txt` | stdout of `tools/traced-swap.py`. Its last lines are its own 6-hour wait expiring; the swap completed after that, as the records show |
| `tools/traced-swap.py` | the driver for `158065f1…`: publishes one offer, takes it, requests the lock, waits, requests the claim, waits. It imports the helpers of `deploy/scripts/node-e2e.py`, mines nothing and never calls a Maker action |
| `tools/revive-maker-row.sh` | the one intervention on Node state, verbatim |
| `diagnostic-build.patch` | `git diff aef7567 -- crates/` in the worktree the trace build was compiled from |
| `provenance.json`, `SHA256SUMS` | generated at the end of the capture |
