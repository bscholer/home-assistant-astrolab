"""Constants."""

DOMAIN = "astrolab"
CONF_URL = "url"

SCAN_INTERVAL_S = 30

# Slower things are fetched at most this often (seconds). The forecast asks an outside weather
# service, and the nightly report and tonight's list only change a few times a day.
WEATHER_TTL_S = 30 * 60
MORNING_TTL_S = 10 * 60
TONIGHT_TTL_S = 15 * 60
SYSTEM_TTL_S = 60
