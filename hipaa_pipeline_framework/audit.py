"""PHI access audit logging: append-only JSON-lines audit trail.

Every governed or quarantined record writes one audit entry with a
reason, so nothing disappears without a trace. Entries carry a UTC
timestamp so the trail can be reviewed in order, and entries() reads
the trail back for review. This is a pattern, not a compliant audit
system on its own — production use needs retention, access control,
and review processes around it.
"""

import json
from datetime import datetime, timezone
from pathlib import Path


class AuditLog:
    def __init__(self, path):
        self.path = Path(path)

    def write(self, action, member_hash, reason=None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "member_hash": member_hash,
            "reason": reason,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def entries(self):
        """Read the trail back as a list of dicts, in written order.

        Returns [] when the trail does not exist yet, so a fresh
        pipeline run can review before any entry is written.
        """
        if not self.path.exists():
            return []
        return [json.loads(line) for line in
                self.path.read_text().splitlines() if line.strip()]
