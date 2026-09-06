# Security

Threat model and controls for Smart Market Watchlist (Groww CODE 2026).

## Threat model (concise)

| Threat | Mitigation |
|--------|------------|
| Credential stuffing / brute force | Argon2id hashes; Redis-backed login rate limits (memory fallback) |
| IDOR on watchlists/events | Ownership checks; unknown IDs → **404** (no existence leak) |
| JWT theft | Short-lived access tokens; HTTPS in production; no secrets in frontend |
| XSS | JSON API; React escaping; `X-Content-Type-Options: nosniff` |
| Clickjacking | `X-Frame-Options: DENY` |
| CSRF | Bearer tokens (not cookie session for API) |
| Over-fetch / DoS | Rate limits; digest `top_k` capped at 20; mark-seen batch max 50 |
| Prompt injection via LLM | LLM never scores; templates are source of truth; `ENABLE_LLM` off by default |
| Live market API keys in demo | Replay/mock modes; no live keys required for judging |

## AuthN / AuthZ

- Register + login issue JWT (`sub` = `user_id`).
- All watchlist/digest/mark-seen routes require `Authorization: Bearer`.
- WebSocket: `?token=` validated before accept; wrong user → close 4401/4404.
- Passwords: Argon2id via `pwdlib` / passlib stack in `app.core.security`.

## Secrets

- Never commit `.env`. Use `.env.example` only.
- Rotate `JWT_SECRET` for any shared demo deployment.
- Postgres/Redis credentials are compose defaults for local only.

## Data integrity

- Attention scoring is deterministic from evidence; LLM is narration-only.
- Stale / conflicting prices lower **confidence**, which lowers attention.
- Event versions support optimistic mark-seen / escalation.

## Headers (API)

Applied in `app.main` middleware:

- `X-Request-ID`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: DENY`
- `Permissions-Policy` (camera/mic/geo disabled)
- `Strict-Transport-Security` when `APP_ENV=production`

## Reporting

For this hackathon demo: file issues in the project repo. No public bounty program.
