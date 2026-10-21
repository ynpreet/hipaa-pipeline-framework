"""Pipeline config templates with secure defaults.

A governed pipeline should fail closed: encryption at rest on, audit
logging on, failed records quarantined (never silently dropped), and
no PHI in logs. validate_config reports every insecure setting so a
caller can refuse to start an unsafe pipeline instead of guessing.
"""

# Secure defaults. Callers copy and override only non-security fields
# (e.g. audit path); validate_config rejects any override that would
# weaken a security default.
DEFAULT_CONFIG = {
    "encryption_at_rest": True,
    "audit_enabled": True,
    "quarantine_on_failure": True,
    "log_phi": False,
}


def default_pipeline_config():
    """Return a fresh copy of the secure-default config."""
    return dict(DEFAULT_CONFIG)


def validate_config(config):
    """Return a list of problems; empty list means secure to run."""
    errors = []
    if config.get("encryption_at_rest") is not True:
        errors.append("encryption_at_rest must be True")
    if config.get("audit_enabled") is not True:
        errors.append("audit_enabled must be True")
    if config.get("quarantine_on_failure") is not True:
        errors.append("quarantine_on_failure must be True")
    if config.get("log_phi") is not False:
        errors.append("log_phi must be False (never log PHI)")
    return errors


def is_secure(config):
    """True only when validate_config finds no problems."""
    return validate_config(config) == []
