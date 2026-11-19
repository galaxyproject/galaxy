import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ServiceCredentialsDefinition } from "@/api/userCredentials";

import CredentialsGroupForm from "./CredentialsGroupForm.vue";

const localVue = getLocalVue();

const GROUP_ID = "test-group";

const SERVICE_DEFINITION: ServiceCredentialsDefinition = {
    name: "test-service",
    version: "1.0",
    label: "Test Service",
    description: "A service used for testing",
    optional: false,
    variables: [
        { name: "token", label: "Token name", description: "Token name", optional: false },
        { name: "port", label: "Port", description: "Server port", optional: true },
    ],
    secrets: [{ name: "token", label: "Token", description: "Token value", optional: false }],
};

const NEUTRAL = { ariaInvalid: undefined, stateClasses: [] };
const INVALID = { ariaInvalid: "true", stateClasses: ["is-invalid"] };
const VALID = { ariaInvalid: undefined, stateClasses: ["is-valid"] };

function mountComponent(value: string) {
    return mount(CredentialsGroupForm as object, {
        localVue,
        propsData: {
            groupData: {
                groupId: GROUP_ID,
                isNewGroup: true,
                groupPayload: {
                    name: "My Group",
                    variables: SERVICE_DEFINITION.variables.map(({ name }) => ({ name, value })),
                    secrets: SERVICE_DEFINITION.secrets.map(({ name }) => ({ name, value })),
                },
            },
            serviceDefinition: SERVICE_DEFINITION,
        },
    });
}

function findInput(wrapper: Wrapper<Vue>, name: string, type: string) {
    return wrapper.find(`#${GROUP_ID}-${name}-${type}-input`);
}

function validationState(input: ReturnType<typeof findInput>) {
    return {
        ariaInvalid: input.attributes("aria-invalid"),
        stateClasses: input.classes().filter((cls) => cls === "is-invalid" || cls === "is-valid"),
    };
}

describe("CredentialsGroupForm", () => {
    it.each([
        ["an empty required variable", "token", "variable", "", INVALID],
        ["an empty optional variable", "port", "variable", "", NEUTRAL],
        ["a filled required variable", "token", "variable", "my-token", VALID],
        ["an empty required secret", "token", "secret", "", INVALID],
    ])("validates %s once it loses focus", async (_case, name, type, value, expected) => {
        const input = findInput(mountComponent(value), name, type);

        expect(validationState(input)).toEqual(NEUTRAL);

        await input.trigger("blur");

        expect(validationState(input)).toEqual(expected);
    });

    it("tracks a variable and a secret of the same name separately", async () => {
        const wrapper = mountComponent("");

        await findInput(wrapper, "token", "secret").trigger("blur");

        expect(validationState(findInput(wrapper, "token", "variable"))).toEqual(NEUTRAL);
    });
});
