# Security reports

Use this repository's GitHub **Security → Report a vulnerability** private reporting channel when available: https://github.com/wqyorxyq/ridersense/security/advisories/new . If unavailable, open a minimal issue asking to arrange private disclosure; do not include exploit details, credentials, private footage, or tokens in a public issue. There is no dedicated response team or guaranteed response time.

Only the current default branch is maintained. The application is a local research prototype. Keep it on loopback; the optional phone gateway should be used only on a trusted private network. Do not expose it to the public internet. Pairing tokens grant API access, including physical control when enabled. Rotate them by restarting the server and remove any persistent RIDER_TOKEN override if compromised. Generated TLS keys remain local and must not be shared.

Report unbounded outputs, stale-input failures, authentication bypass, source leakage, unsafe file handling, and model-download integrity failures. Hardware emergencies require the physical controller power switch; an issue report is not an emergency stop.
