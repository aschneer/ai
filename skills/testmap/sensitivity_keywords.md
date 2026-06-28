# Sensitivity Keywords

When scoring triage signal 4.1.3, match symbol names and file paths against the keywords below. A match raises the symbol's risk score. Categories explain the risk context — use them to judge borderline matches and partial-word hits.

## Authentication & Authorization
- `auth`, `authn`, `authz`
- `login`, `logout`, `signin`, `signout`
- `password`, `passwd`, `pwd`
- `credential`, `credentials`
- `token`, `access_token`, `refresh_token`, `bearer`
- `session`, `cookie`
- `permission`, `permissions`, `privilege`, `role`, `roles`, `acl`
- `grant`, `revoke`
- `oauth`, `jwt`, `saml`, `sso`

**Risk:** Authentication and authorization bugs directly enable unauthorized access. A weak assertion here may silently miss a privilege escalation.

## Cryptography & Secrets
- `encrypt`, `decrypt`, `cipher`
- `hash`, `digest`, `checksum`
- `sign`, `verify`, `signature`
- `key`, `secret`, `private_key`, `public_key`, `api_key`
- `hmac`, `aes`, `rsa`, `sha`, `md5`, `bcrypt`, `pbkdf`
- `salt`, `nonce`, `iv`, `entropy`
- `certificate`, `cert`, `tls`, `ssl`

**Risk:** Cryptographic functions are easy to misuse. A test that only checks "it ran" may miss subtle bugs (wrong key size, missing padding, timing attack surface).

## Injection & Sanitization
- `sql`, `query`, `execute`, `cursor`
- `sanitize`, `sanitise`, `escape`, `unescape`
- `encode`, `decode`
- `serialize`, `deserialize`, `marshal`, `unmarshal`
- `parse`, `render` (in templating/HTML contexts)
- `shell`, `exec`, `subprocess`, `command`
- `eval`, `compile`

**Risk:** Injection vulnerabilities (SQLi, XSS, command injection, deserialization attacks) arise from unsanitized input reaching execution contexts. These symbols sit on that boundary.

## Input Validation & Boundaries
- `validate`, `validation`, `validator`
- `check`, `verify`, `assert` (production assertions, not test assertions)
- `boundary`, `limit`, `max`, `min`, `clamp`
- `allow`, `deny`, `block`, `reject`, `filter`
- `whitelist`, `blacklist`, `allowlist`, `denylist`

**Risk:** Validation logic defines the trust boundary. Gaps here can let malformed or malicious input propagate into the system.

## Data Integrity & Persistence
- `save`, `persist`, `commit`, `flush`
- `delete`, `remove`, `drop`, `purge`, `wipe`
- `migrate`, `migration`
- `transaction`, `rollback`
- `backup`, `restore`

**Risk:** Incorrect data mutation or deletion is often irreversible. Tests must verify both the happy path and failure/rollback behavior.

## Payments & Financial
- `payment`, `pay`, `charge`, `refund`
- `invoice`, `billing`
- `price`, `amount`, `total`, `balance`
- `currency`, `money`
- `card`, `stripe`, `paypal`

**Risk:** Financial logic errors have direct monetary consequences and are often difficult to reverse.

## Privacy & PII
- `pii`, `personal`, `gdpr`, `ccpa`
- `email`, `phone`, `address`
- `ssn`, `dob`, `birthdate`
- `anonymize`, `redact`, `mask`

**Risk:** Incorrect handling of personal data may violate regulations or leak sensitive user information.

## Network & External I/O
- `request`, `response`, `http`, `https`
- `fetch`, `send`, `receive`
- `upload`, `download`
- `webhook`, `callback`
- `redirect`, `forward`
- `proxy`, `tunnel`

**Risk:** Network-facing code is exposed to untrusted input and network-level failures. Tests should cover error paths and malformed responses.

## Rate Limiting & Abuse Prevention
- `rate_limit`, `ratelimit`, `throttle`
- `quota`, `limit`
- `captcha`, `bot`
- `ban`, `suspend`, `lockout`

**Risk:** Missing or broken rate limiting exposes systems to abuse, DoS, and brute-force attacks.
