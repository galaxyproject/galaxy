import * as Sentry from "@sentry/vue";
import Vue from "vue";
import type VueRouter from "vue-router";

interface GalaxyConfig {
    sentry_dsn_public?: string;
    sentry_client_traces_sample_rate?: number;
    version_major: string;
    version_minor?: string;
}

interface GalaxyUser {
    get(attr: string): string | undefined;
    attributes?: {
        preferences?: {
            extra_user_preferences?: string;
        };
    };
}

interface GalaxyInstance {
    config: GalaxyConfig;
    user?: GalaxyUser;
}

function isReplayEnabled(user?: GalaxyUser): boolean {
    try {
        const prefsJson = user?.attributes?.preferences?.extra_user_preferences;
        if (!prefsJson) {
            return false;
        }
        const prefs = JSON.parse(prefsJson);
        const value = prefs["sentry_replay|enabled"];
        return value === true || value === "true";
    } catch {
        return false;
    }
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

    const replayEnabled = isReplayEnabled(Galaxy.user);
    const integrations = [Sentry.browserTracingIntegration({ router })];
    if (replayEnabled) {
        integrations.push(
            Sentry.replayIntegration({
                maskAllText: true,
                blockAllMedia: true,
            }),
        );
    }

    Sentry.init({
        Vue,
        dsn: config.sentry_dsn_public,
        integrations,
        release,
        tracesSampleRate: config.sentry_client_traces_sample_rate ?? 0,
        replaysSessionSampleRate: 0,
        replaysOnErrorSampleRate: replayEnabled ? 1.0 : 0,
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
