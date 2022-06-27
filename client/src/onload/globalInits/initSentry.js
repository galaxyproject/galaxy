import * as Sentry from "@sentry/browser";

/**
 * Initializes Sentry, one of the few functions that should actually be
 * in a global init. Transplanted here from js-app.mako
 *
 * @param {object} config Galaxy configuration object
 */
export const initSentry = (galaxy, config) => {
    console.log("initSentry");

    if (config.sentry) {
        const { sentry_dsn_public, email } = config.sentry;
        const release = `${config.version_major}.${config.version_minor}`;
        Sentry.init({
            dsn: sentry_dsn_public,
            release: release,
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
