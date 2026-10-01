import { computed } from "vue";

import { getOIDCIdpsWithRegistration } from "@/components/User/ExternalIdentities/ExternalIDHelper";
import { useConfig } from "@/composables/config";

/** Where registering leads; `external` is an OIDC provider's own endpoint, outside the app's router */
export interface RegistrationTarget {
    external: boolean;
    url: string;
}

/**
 * Where "Register" leads, or nothing where the instance registers no one. An instance that creates no local
 * accounts still registers through OIDC, and a single provider offering it is gone to directly.
 */
export function useRegistrationTarget() {
    const { config } = useConfig();

    const registrationTarget = computed<RegistrationTarget | undefined>(() => {
        if (config.value?.allow_local_account_creation) {
            return { external: false, url: "/register/start" };
        }
        const endpoints = Object.values(getOIDCIdpsWithRegistration(config.value?.oidc ?? {})).map(
            (idp) => idp.end_user_registration_endpoint,
        );
        const [first, ...others] = endpoints;
        if (!first) {
            return undefined;
        }
        // several providers need the form to pick one, a single one does not
        return others.length ? { external: false, url: "/register/start" } : { external: true, url: first };
    });

    return { registrationTarget };
}
