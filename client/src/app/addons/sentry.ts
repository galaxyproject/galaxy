import * as Sentry from "@sentry/vue";
import Vue from "vue";
import type VueRouter from "vue-router";

interface GalaxyConfig {
    sentry_dsn_public?: string;
    version_major: string;
    version_minor?: string;
}

interface GalaxyInstance {
    config: GalaxyConfig;
    user?: { get(attr: string): string | undefined };
}

export function initSentry(Galaxy: GalaxyInstance, router: VueRouter): void {
    const config = Galaxy.config;
    if (!config.sentry_dsn_public) {
        return;
    }

    const email = Galaxy.user?.get("email");
    let release = config.version_major;
    if (config.version_minor) {
        release += `.${config.version_minor}`;
    }

    Sentry.init({
        Vue,
        dsn: config.sentry_dsn_public,
        integrations: [Sentry.browserTracingIntegration({ router })],
        release,
        beforeSend(event, hint) {
            const error = hint.originalException;
            if (error instanceof Error && ["AdminRequired", "RegisteredUserRequired"].includes(error.name)) {
                return null;
            }
            return event;
        },
    });

    if (email) {
        Sentry.setUser({ email });
    }
}
