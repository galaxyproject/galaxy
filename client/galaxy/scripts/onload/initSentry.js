import Raven from "libs/raven";

/**
 * Initializes raven/sentry, one of the few functions that should actually be
 * in a global init. Transplanted here from js-app.mako
 *
 * @param {object} config Galaxy configuration object
 */
export const initSentry = (galaxy, config) => {
    console.log("initSentry");

    if (config.sentry) {
        let { sentry_dsn_public, email } = config.sentry;
        Raven.config(sentry_dsn_public).install();
        if (email) {
            Raven.setUser({ email });
        }
    }
};
