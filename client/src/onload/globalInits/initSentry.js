import * as Sentry from "@sentry/vue";
import Vue from "vue";

/**
 * Initializes Sentry, one of the few functions that should actually be
 * in a global init. Transplanted here from js-app.mako
 *
 * @param {object} config Galaxy configuration object
 */
export const initSentry = (galaxy, config) => {
    console.log("initSentry");
    if (config.sentry) {
        const router = galaxy.router;
        const { sentry_dsn_public, email } = config.sentry;
        let release = galaxy.config.version_major;
        if (galaxy.config.version_minor) {
            release += `.${galaxy.config.version_minor}`;
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
        galaxy.Sentry = Sentry;
    }
};
