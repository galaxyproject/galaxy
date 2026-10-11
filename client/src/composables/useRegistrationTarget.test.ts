import { setupMockConfig } from "@tests/vitest/mockConfig";
import { describe, expect, it } from "vitest";

import { useRegistrationTarget } from "./useRegistrationTarget";

const OKTA = { end_user_registration_endpoint: "https://okta.example.org/register" };
const KEYCLOAK = { end_user_registration_endpoint: "https://keycloak.example.org/register" };

function targetFor(config: object) {
    setupMockConfig(config);
    return useRegistrationTarget().registrationTarget.value;
}

describe("useRegistrationTarget", () => {
    it("leads to the local registration form where local accounts are on", () => {
        expect(targetFor({ allow_local_account_creation: true, oidc: { okta: OKTA } })).toEqual({
            external: false,
            url: "/register/start",
        });
    });

    it("offers nothing where no one can register", () => {
        expect(targetFor({ allow_local_account_creation: false, oidc: { plain: {} } })).toBeUndefined();
        expect(targetFor({})).toBeUndefined();
    });

    it("goes straight to a single OIDC provider's registration", () => {
        expect(targetFor({ allow_local_account_creation: false, oidc: { okta: OKTA } })).toEqual({
            external: true,
            url: OKTA.end_user_registration_endpoint,
        });
    });

    it("lets the form pick among several OIDC providers", () => {
        expect(targetFor({ allow_local_account_creation: false, oidc: { okta: OKTA, keycloak: KEYCLOAK } })).toEqual({
            external: false,
            url: "/register/start",
        });
    });
});
