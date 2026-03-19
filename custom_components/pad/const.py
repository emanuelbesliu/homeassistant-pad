"""Constants for the PAD Romania integration."""

DOMAIN = "pad"
PLATFORMS = ["sensor", "binary_sensor"]

# API endpoint - padrom.ro XF-based AJAX verification
API_URL = "https://www.padrom.ro/pad/"

# Configuration keys
CONF_SERIE_POLITA = "serie_polita"
CONF_NUMAR_POLITA = "numar_polita"
CONF_CNP_CUI = "cnp_cui"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_POLICY_NAME = "policy_name"

# Defaults
DEFAULT_UPDATE_INTERVAL = 86400  # 24 hours (policy data doesn't change often)
MIN_UPDATE_INTERVAL = 3600  # 1 hour
MAX_UPDATE_INTERVAL = 604800  # 7 days

# Valid policy series (from padrom.ro dropdown)
VALID_SERIES = [
    "RA-002",
    "RA-005",
    "RA-007",
    "RA-008",
    "RA-009",
    "RA-010",
    "RA-013",
    "RA-017",
    "RA-020",
    "RA-021",
    "RA-023",
    "RA-025",
    "RA-029",
    "RA-035",
    "RA-036",
    "RA-039",
    "RA-046",
    "RA-047",
    "RA-053",
    "RA-054",
    "RA-057",
    "RA-059",
    "RA-061",
    "RA-065",
    "RA-067",
    "RA-068",
    "RX3740",
]

# API response data keys (only fields actually returned by padrom.ro)
ATTR_POLICY_SERIES = "policy_series"
ATTR_POLICY_NUMBER = "policy_number"
ATTR_VALID_UNTIL = "valid_until"
ATTR_LAST_CHECK = "last_check"
ATTR_POLICY_FOUND = "policy_found"
ATTR_RAW_RESPONSE = "raw_response"

# Alert thresholds (days before expiry to trigger alerts)
ALERT_THRESHOLDS = [60, 30, 14, 7]
# Below this threshold, alert every day (includes 0 and negative = expired)
ALERT_DAILY_THRESHOLD = 7

# Event type fired when policy is expiring/expired
EVENT_POLICY_EXPIRING = f"{DOMAIN}_policy_expiring"
