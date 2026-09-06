# Web Push (browser closed alerts)

This demo uses **Web Push with VAPID** — the standard browser equivalent of FCM for web clients.

## What it does

- User grants notification permission in **Settings → Enable push**
- Service worker: `frontend/public/sw.js`
- Subscriptions stored in `push_subscriptions`
- Engine alerts also trigger Web Push
- Works when the **tab is closed** (desktop Chrome/Edge usually need the browser process alive)

## Setup

Set in `.env`:

```env
ENABLE_WEB_PUSH=true
VAPID_PUBLIC_KEY=...
VAPID_PRIVATE_KEY=...
VAPID_SUBJECT=mailto:you@example.com
```

Generate keys:

```powershell
python -c "from cryptography.hazmat.primitives.asymmetric import ec; from cryptography.hazmat.primitives import serialization; import base64; priv=ec.generate_private_key(ec.SECP256R1()); pub=priv.public_key(); print(base64.urlsafe_b64encode(pub.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)).decode().rstrip('=')); print(base64.urlsafe_b64encode(priv.private_numbers().private_value.to_bytes(32,'big')).decode().rstrip('='))"
```

Then: `pip install pywebpush` and `alembic upgrade head`.

## Honest limits

| Capability | This build |
|------------|------------|
| Web Push, tab closed | Yes |
| Native Android FCM SDK | Later (Groww app) |
| Native iOS APNs | Later (Groww app) |

See also: **Info** tab in the app.
