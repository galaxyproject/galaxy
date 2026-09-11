# OIDC authentication and account confirmation

Galaxy 25.1 has two authentication implementations. `AuthnzManager` routes
Keycloak, CILogon, and Custos to `OIDCAuthnzBase` in `custos_authnz.py`; other
providers use `PSAAuthnz`. Only the legacy OIDC implementation supports deferred
account creation on this release. It stores associations in `CustosAuthnzToken`,
using the provider's subject as `external_user_id`. This backport does not migrate
those associations or add a confirmation pipeline to python-social-auth.

## Request flow

1. **Start authentication.** `OIDCAuthnzBase.authenticate` creates the provider
   redirect and saves the nonce hash and optional PKCE verifier in `FlowState`.
   OAuth state identifies a record bound to the browser's Galaxy session and the
   canonical provider name. These values no longer rely on separate cookies.
2. **Handle the callback.** `callback` consumes authentication state before the
   code exchange. It restores the PKCE verifier and supplies the consumed state
   to `OAuth2Session`, which checks the callback URL's state during the exchange.
   A failed exchange or identity check requires a new login attempt.
3. **Establish identity.** `_process_token` reads the ID token returned directly
   by the configured token endpoint and checks the nonce, issuer, audience,
   expiry, subject, and authorized party when present. If it needs UserInfo for
   the email address, UserInfo's subject must match the ID token's subject.
   As in the legacy backend, trust in the token response relies on the direct
   exchange with the configured endpoint, rather than local signature
   verification. Production providers require HTTPS with certificate
   verification enabled. The callback never accepts a browser-supplied ID token.
4. **Defer creation.** When a new account requires confirmation, the callback
   saves the established identity, provider tokens, and their original expiration
   times in a server-side confirmation record. It redirects to
   `login/start?confirm=true&provider=...&confirmation_id=...`. The URL contains
   no provider credentials. Existing-account login, explicit linking, and
   `fixed_delegated_auth` retain their legacy paths.
5. **Confirm or cancel.** `NewUserConfirmation.vue` sends a form-encoded POST to
   `/authnz/{provider}/create_user` or `/authnz/{provider}/cancel_user_creation`,
   with `confirmation_id` and `session_csrf_token` in the body. Both actions
   enforce POST, CSRF protection, and anonymous registration context, including
   through generic controller routes. Legacy token and JSONP parameters are
   rejected. Confirmation consumes the record, rejects existing email or subject
   associations, and creates through `UserManager`, preserving activation policy.
   Cancellation consumes the record without creating an account.
6. **Refresh browser state.** Successful confirmation logs in the user and
   returns JSON containing `redirect_uri`. The client performs a full navigation
   to reload user and CSRF state. Cancellation returns an empty JSON object and
   the client returns to login. Responses use `Cache-Control: no-store`.

## State and failure boundaries

`FlowState` stores records in the existing `PSAPartial` table under a namespace
and negative step numbers separate from resumable python-social-auth pipelines.
No database migration is needed. Each record is bound to the Galaxy session,
canonical provider, and purpose (`authentication` or `confirmation`). Records
expire after at most ten minutes; confirmation expiry is also bounded by the ID
token's expiry. A new attempt replaces pending state for that browser/provider.

Consumption uses a conditional database delete, checks that the Galaxy session
is still valid, and requires exactly one affected row. Do not replace this with
an unconditional delete following a read: two workers could reuse the same
record. Consumption commits before account-creation helpers, which can commit
independently. A subsequent exchange, account-creation, or association failure
must not make the record reusable. Email and subject checks reject associations
created while the confirmation page was open; database uniqueness constraints
also guard concurrent inserts.

Confirmation never decodes tokens or recomputes identity from client input. It
preserves the callback's subject and token expiration times. Token refresh,
association persistence, and provider logout continue through the legacy
backend. In-flight cookie-based logins and old confirmation links must be
restarted after upgrading.

## Regression coverage

`test/integration/oidc/test_auth_oidc.py` uses real Docker Keycloak and a Galaxy
server. Its confirmation class enables PKCE and covers POST/CSRF, account
creation, session refresh, cancellation, browser isolation, and callback replay.
The other classes cover legacy login, account linking, logout, bearer tokens,
and the independent PSA path. Run these using:

```console
./run_tests.sh -integration test/integration/oidc/test_auth_oidc.py
```

`test/unit/authnz/test_flow_state.py` covers persistence, expiry, purpose and
provider binding, invalidated sessions, and concurrent consumption. The
PostgreSQL unit-test workflow also runs it against PostgreSQL.
`test_custos_confirmation.py` covers forged browser credentials, identity
validation, activation policy, collision checks, and failures after consumption.
`test_authnz_controller.py` tests HTTP guards. The Jest Login component tests
cover confirmation bodies, cancellation, errors, duplicate submission, legacy
links, and full navigation after login, including applications under a URL prefix.
