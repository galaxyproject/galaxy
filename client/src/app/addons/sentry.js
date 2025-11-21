import * as Sentry from "@sentry/vue";
import Vue from "vue";

/**
 * Initializes Sentry, one of the few functions that should actually be
 * in a global init. Transplanted here from js-app.mako
 *
 * @param {object} config Galaxy configuration object
 */
export async function initSentry(Galaxy, router) {
    console.log("initSentry");
    const config = Galaxy.config;
    if (config.sentry_dsn_public) {
        const sentry_dsn_public = config.sentry_dsn_public;
        const email = Galaxy.user.get("email");
        let release = Galaxy.config.version_major;
        if (Galaxy.config.version_minor) {
            release += `.${Galaxy.config.version_minor}`;
        }
        Sentry.init({
            Vue,
            dsn: sentry_dsn_public,
            integrations: [Sentry.browserTracingIntegration({ router })],
            release: release,
            beforeSend(event, hint) {
                const error = hint.originalException;
                if (["AdminRequired", "RegisteredUserRequired"].includes(error?.name)) {
                    // ignore these error events
                    return null;
                }
                return event;
            },
        });
        if (email) {
            Sentry.configureScope((scope) => {
                scope.setUser({
                    email: email,
                });
            });
        }
        Galaxy.Sentry = Sentry;
    }
}
