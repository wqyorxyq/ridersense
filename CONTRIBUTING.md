# Contributing

Use Python 3.12. Create a virtual environment and install `requirements-dev.txt`. Run `python -m pytest -q`, `node --check static/app.js`, and `node tests/ui_smoke.cjs` from the repository root. Use the default hardware-disabled mode. Tests inject fake devices and must never open a serial port or camera or download weights.

Open an issue with reproduction steps, expected/actual results, OS, Python version and dependency versions. Remove pairing tokens, personal footage, device identifiers, private addresses, and logs containing secrets. Include only media you have permission to publish.

Pull requests should explain the user-visible problem, behavior change, and validation. Preserve rear-camera coordinates, four-dot rules, simulation/live isolation, bounded vibration, stale-input shutdown, stop-all behavior, and the 30-second thermal maximum. Add regression tests for changes to these behaviors. Do not claim physical validation based on mocks or serial writes returning.

Contributions are licensed under AGPL-3.0-only. Confirm you have rights to contribute them. Keep third-party code, weights and assets out unless their exact provenance and licenses have been reviewed and all notices are retained. Update notices and model hashes when dependency identities change. No contributor license agreement is currently required.
