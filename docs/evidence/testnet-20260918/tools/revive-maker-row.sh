#!/bin/sh
# Re-queues the one Maker scheduler row that the recover/drive command mismatch
# marked failed (swap 158065f1), which is what a correct Requeue would have done.
docker exec -i lez-testnet-maker-node python3 - <<'PY'
import sqlite3,time
c=sqlite3.connect("/var/lib/lez/maker/maker.sqlite3",timeout=30)
now=int(time.time())
n=c.execute("""UPDATE maker_actor_processes SET schedule_state='queued', next_attempt_at=?, last_failure_class=NULL,
  lease_owner=NULL, leased_at=NULL, child_pid=NULL, child_start_ticks=NULL, updated_at=?
  WHERE swap_id LIKE '158065f1%' AND schedule_state='failed'""",(now,now)).rowcount
c.commit(); print("revived rows:",n)
PY
