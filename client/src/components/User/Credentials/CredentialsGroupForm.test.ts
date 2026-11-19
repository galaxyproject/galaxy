import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { reactive } from "vue";

import type { ServiceCredentialGroupPayload, ServiceCredentialsDefinition } from "@/api/userCredentials";
import { SECRET_PLACEHOLDER } from "@/stores/userToolsServiceCredentialsStore";

import CredentialsGroupForm from "./CredentialsGroupForm.vue";

const SERVICE_DEFINITION = {
    name: "service",
    version: "1.0",
    label: "Service",
    description: "A test service",
    optional: false,
    multiple: false,
    variables: [{ name: "server", label: "Server", description: "Server URL", optional: false }],
    secrets: [{ name: "token", label: "Token", description: "API token", optional: false }],
} as unknown as ServiceCredentialsDefinition;

function mountForm(name = "default", token: string | null = SECRET_PLACEHOLDER) {
    const groupPayload = reactive({
        name,
        variables: [{ name: "server", value: "https://example.org" }],
        secrets: [{ name: "token", value: token }],
    }) as ServiceCredentialGroupPayload;
    const wrapper = mount(CredentialsGroupForm as object, {
        props: {
            groupData: { groupId: "g1", isNewGroup: false, groupPayload },
            serviceDefinition: SERVICE_DEFINITION,
        },
        global: getLocalVue(),
    });
    return { wrapper, groupPayload };
}

const VALIDATION_DEFINITION = {
    ...SERVICE_DEFINITION,
    variables: [
        { name: "token", label: "Token name", description: "Token name", optional: false },
        { name: "port", label: "Port", description: "Server port", optional: true },
    ],
    secrets: [{ name: "token", label: "Token", description: "Token value", optional: false }],
} as unknown as ServiceCredentialsDefinition;

const NEUTRAL = { ariaInvalid: undefined, stateClasses: [] };
const INVALID = { ariaInvalid: "true", stateClasses: ["g-invalid"] };
const VALID = { ariaInvalid: undefined, stateClasses: ["g-valid"] };

function mountValidationForm(value: string) {
    return mount(CredentialsGroupForm as object, {
        props: {
            groupData: {
                groupId: "g1",
                isNewGroup: true,
                groupPayload: reactive({
                    name: "My Group",
                    variables: VALIDATION_DEFINITION.variables.map(({ name }) => ({ name, value })),
                    secrets: VALIDATION_DEFINITION.secrets.map(({ name }) => ({ name, value })),
                }),
            },
            serviceDefinition: VALIDATION_DEFINITION,
        },
        global: getLocalVue(),
    });
}

function validationState(wrapper: VueWrapper, name: string, type: string) {
    const input = wrapper.get(`input#g1-${name}-${type}-input`);
    return {
        ariaInvalid: input.attributes("aria-invalid"),
        stateClasses: input.classes().filter((cls) => cls === "g-invalid" || cls === "g-valid"),
    };
}

describe("CredentialsGroupForm.vue", () => {
    it("renders the group name, variable and secret in GFormInput fields", () => {
        const { wrapper } = mountForm();
        const name = wrapper.get("input#g1-name-input");
        const server = wrapper.get("input#g1-server-variable-input");
        const token = wrapper.get("input#g1-token-secret-input");
        for (const input of [name, server, token]) {
            expect(input.classes()).toContain("g-form-input");
        }
        expect(server.attributes("required")).toBeDefined();
        expect(token.attributes("type")).toBe("password");
        expect(token.attributes("autocomplete")).toBe("off");
        expect((server.element as HTMLInputElement).value).toBe("https://example.org");
    });

    it("writes the trimmed group name and the typed variable into the payload", async () => {
        const { wrapper, groupPayload } = mountForm();
        await wrapper.get("input#g1-name-input").setValue("  my group ");
        await wrapper.get("input#g1-server-variable-input").setValue("https://other.org");
        expect(groupPayload.name).toBe("my group");
        expect(groupPayload.variables[0]!.value).toBe("https://other.org");
    });

    it("shows the group name error while the name is too short", async () => {
        const { wrapper } = mountForm("ab");
        const name = wrapper.get("input#g1-name-input");
        expect(name.attributes("aria-invalid")).toBe("true");
        expect(wrapper.get("#g1-name .invalid-feedback").text()).toBe("Group name must be at least 3 characters");
        // The group state drives the invalid feedback, so it must be shown explicitly
        expect(wrapper.get("#g1-name .invalid-feedback").classes()).toContain("d-block");

        await name.setValue("abc");
        expect(name.attributes("aria-invalid")).toBeUndefined();
        expect(wrapper.find("#g1-name .invalid-feedback").exists()).toBe(false);
    });

    it("clears the secret placeholder on focus and restores it on blur when left empty", async () => {
        const { wrapper, groupPayload } = mountForm();
        const token = wrapper.get("input#g1-token-secret-input");
        await token.trigger("focus");
        expect(groupPayload.secrets[0]!.value).toBe("");
        await token.trigger("blur");
        expect(groupPayload.secrets[0]!.value).toBe(SECRET_PLACEHOLDER);
    });

    it("marks an empty required secret invalid after blur", async () => {
        const { wrapper } = mountForm("default", "");
        const token = wrapper.get("input#g1-token-secret-input");
        expect(token.attributes("aria-invalid")).toBeUndefined();
        await token.trigger("blur");
        expect(token.attributes("aria-invalid")).toBe("true");
    });

    it.each([
        ["an empty required variable", "token", "variable", "", INVALID],
        ["an empty optional variable", "port", "variable", "", NEUTRAL],
        ["a filled required variable", "token", "variable", "my-token", VALID],
        ["an empty required secret", "token", "secret", "", INVALID],
    ])("validates %s once it loses focus", async (_case, name, type, value, expected) => {
        const wrapper = mountValidationForm(value);

        expect(validationState(wrapper, name, type)).toEqual(NEUTRAL);

        await wrapper.get(`input#g1-${name}-${type}-input`).trigger("blur");

        expect(validationState(wrapper, name, type)).toEqual(expected);
    });

    it("tracks a variable and a secret of the same name separately", async () => {
        const wrapper = mountValidationForm("");

        await wrapper.get("input#g1-token-secret-input").trigger("blur");

        expect(validationState(wrapper, "token", "variable")).toEqual(NEUTRAL);
    });
});
