"""PHI access audit logging: append-only JSON-lines audit trail.

Every governed or quarantined record writes one audit entry with a
reason, so nothing disappears without a trace. This is a pattern,
not a compliant audit system on its own — production use needs
retention, access control, and review processes around it.
"""

import json
from pathlib import Path


class AuditLog:
    def __init__(self, path):
        self.path = Path(path)

    def write(self, action, member_hash, reason=None):
        entry = {"action": action, "member_hash": member_hash, "reason": reason}
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")
