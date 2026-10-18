# iPhone camera over local HTTPS

This is a browser gateway, not native iOS support. Actual iPhone certificate installation and camera capture are unverified for this release.

Start the desktop server on its default loopback port **8765**. Install `requirements-iphone.txt`. Find the computer's private Wi-Fi IPv4 address using OS network settings or `ipconfig`; pass that address explicitly:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-iphone.txt
.venv\Scripts\python.exe scripts/iphone_access.py --ip YOUR_PRIVATE_IPV4
```

The gateway binds only the supplied private address: HTTPS **8766**, certificate bootstrap HTTP **8767**. It forwards to the same server on 8765, so models and devices are not duplicated. The script does not change firewall rules or create a public tunnel. If your network blocks it, consult local policy; any manual firewall allowance should be private-network/local-subnet only. Do not port-forward these services.

1. Connect phone and computer to the same trusted Wi-Fi. On Safari open the printed certificate setup address on port 8767.
2. Download the RiderSense Demo CA profile. Install it under Settings → General → VPN & Device Management (or Profile Downloaded).
3. Under Settings → General → About → Certificate Trust Settings, enable full trust for RiderSense Demo CA. The certificate bootstrap is HTTP: install only from your own computer on a trusted network.
4. Open the printed HTTPS address on port 8766. On the desktop dashboard click **Copy pairing token**; enter it manually on the phone and click **Pair**. Never share it in issues, screenshots, or logs.
5. Load models from the computer, then start the browser camera on the phone. Allow camera permission and keep Safari in the foreground. Only one browser should upload at a time.

The gateway blocks `/api/session`, including normalized encoded paths. Phone clients cannot retrieve the desktop pairing token. API calls require the paired token; the token is regenerated when the main server restarts unless explicitly configured. Local certificates last seven days. The CA signing key is not saved; the server private key is generated into ignored `certs/` and must stay private.

Afterward click **Stop all feedback**, stop the gateway with Ctrl+C, and stop the main server. Remove the RiderSense profile from the phone's VPN & Device Management settings (and its trust). With the services stopped, delete only the generated project `certs/` directory if you no longer need it. Remove any firewall rule you manually created. Clear the phone's site data if you want to remove stored pairing information. Changing networks/address or certificate expiry requires regenerating and trusting the new certificate. No certificates or private keys are included in this repository.
