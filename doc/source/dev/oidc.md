# OIDC authentication and account confirmation

Galaxy's OIDC and OAuth2 login flows use `AuthnzManager` and `PSAAuthnz` to run
the python-social-auth pipeline. A provider can enable
`require_create_confirmation` to defer creating a new Galaxy account until the
user confirms in the browser. Confirmation uses the identity established by the
provider callback; the browser supplies only an opaque confirmation identifier.

## Request flow

1. **Start authentication.** `PSAAuthnz.authenticate` creates the provider redirect
   and saves the strategy session using `FlowState`. This preserves OAuth state
   and the PKCE verifier when enabled across requests and workers. The OIDC
   backend persists its nonce separately through python-social-auth storage.
2. **Handle the callback.** `PSAAuthnz.callback` consumes the authentication record
   bound to the browser's `GalaxySession` and provider, restores the strategy
   session, and runs the provider's code exchange and authentication pipeline.
   Authentication state is consumed before the exchange, so a failed callback
   requires a fresh login attempt.
3. **Defer account creation when required.** The
   `check_user_creation_confirmation` pipeline step runs before user creation.
   For a new account requiring confirmation, it saves the authenticated identity
   and provider response in a confirmation record and redirects to
   `login/start?confirm=true&provider=...&confirmation_id=...`. Provider tokens
   stay on the server. Existing-account login and linking continue through their
   usual pipeline paths.
4. **Confirm or cancel.** `NewUserConfirmation.vue` sends a form-encoded POST to
   `/authnz/{provider}/create_user` or
   `/authnz/{provider}/cancel_user_creation`, with `confirmation_id` and
   `session_csrf_token` in the body. The controller enforces POST, CSRF protection,
   and an anonymous registration context. It rejects legacy token and JSONP
   parameters. Confirmation consumes the saved identity, checks for an existing
   email or provider association, and creates the account through `UserManager`,
   preserving activation policy. Cancellation consumes the record without
   creating an account.
5. **Refresh browser state.** Successful confirmation logs in the new user and
   returns JSON containing `redirect_uri`. The client performs a full navigation
   to reload user and CSRF state after the session changes. Cancellation returns
   an empty JSON object and the client returns to login. Both responses use
   `Cache-Control: no-store`.

## State and validation boundaries

`FlowState`, in `lib/galaxy/authnz/flow_state.py`, stores records in `PSAPartial`
under a separate namespace from ordinary python-social-auth partials. Records
are bound to the Galaxy session, canonical provider, and purpose
(`authentication` or `confirmation`). They expire after at most ten minutes;
OIDC confirmation expiry is also bounded by the ID token's expiry. Starting
another attempt replaces the pending flow for that browser session and provider.

Consumption uses a conditional database delete and requires exactly one affected
row. The delete also checks that the Galaxy session is still valid. Keep this
operation atomic: reading a record and later deleting it unconditionally would
allow concurrent requests to reuse it. Consumption commits before account
creation helpers, which can commit independently; failure later in account
creation must not make the confirmation reusable.

The provider backend validates OIDC tokens during the callback, including the
nonce. The confirmation pipeline uses those validated claims and additionally
checks that UserInfo's subject matches the ID token's subject. Do not validate
the nonce a second time during confirmation. Preserve the backend's chosen UID
(Google may use email), and support OAuth2 providers that have no ID token.

## Regression coverage

`test/integration/oidc/test_auth_oidc.py` runs real Keycloak exchanges against a
Galaxy server. `TestOIDCAccountConfirmationIntegration` enables confirmation and
PKCE to cover deferred creation, POST/CSRF enforcement, session refresh,
cancellation, browser isolation, and callback replay. The other classes cover
ordinary login and account linking.

The tests in `test/unit/authnz/` retain state persistence and concurrency
(`test_flow_state.py`), identity validation, provider-specific behavior, activation,
and account-creation failures (`test_deferred_user_creation.py`), and HTTP guards
(`test_authnz_controller.py`). These run without a Galaxy server. The PostgreSQL
unit-test workflow also exercises flow-state consumption against PostgreSQL.
The Login component tests cover browser UI submission, cancellation, errors,
and navigation after login.
