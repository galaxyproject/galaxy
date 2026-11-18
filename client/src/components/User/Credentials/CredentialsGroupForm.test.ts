import { mount, type Wrapper } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

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
        { name: "server", label: "Server", description: "Server URL", optional: false },
        { name: "port", label: "Port", description: "Server port", optional: true },
    ],
    secrets: [{ name: "password", label: "Password", description: "Account password", optional: false }],
};

function mountComponent(values: { server?: string; port?: string; password?: string } = {}) {
    return mount(CredentialsGroupForm as object, {
        localVue,
        propsData: {
            groupData: {
                groupId: GROUP_ID,
                isNewGroup: true,
                groupPayload: {
                    name: "My Group",
                    variables: [
                        { name: "server", value: values.server ?? "" },
                        { name: "port", value: values.port ?? "" },
                    ],
                    secrets: [{ name: "password", value: values.password ?? "" }],
                },
            },
            serviceDefinition: SERVICE_DEFINITION,
        },
    });
}

function findInput(wrapper: Wrapper<Vue>, name: string, type: "variable" | "secret") {
    return wrapper.find(`#${GROUP_ID}-${name}-${type}-input`);
}

function expectNeutral(input: ReturnType<typeof findInput>) {
    expect(input.attributes("aria-invalid")).toBeUndefined();
    expect(input.classes()).not.toContain("is-invalid");
    expect(input.classes()).not.toContain("is-valid");
}

function expectInvalid(input: ReturnType<typeof findInput>) {
    expect(input.attributes("aria-invalid")).toBe("true");
    expect(input.classes()).toContain("is-invalid");
}

function expectValid(input: ReturnType<typeof findInput>) {
    expect(input.attributes("aria-invalid")).toBeUndefined();
    expect(input.classes()).toContain("is-valid");
}

describe("CredentialsGroupForm", () => {
    it("marks an empty required variable invalid once it loses focus", async () => {
        const wrapper = mountComponent();
        const input = findInput(wrapper, "server", "variable");

        expectNeutral(input);

        await input.trigger("blur");

        expectInvalid(input);
    });

    it("keeps an empty optional variable neutral after it loses focus", async () => {
        const wrapper = mountComponent();
        const input = findInput(wrapper, "port", "variable");

        await input.trigger("blur");

        expectNeutral(input);
    });

    it("marks a filled required variable valid once it loses focus", async () => {
        const wrapper = mountComponent({ server: "https://example.org" });
        const input = findInput(wrapper, "server", "variable");

        expectNeutral(input);

        await input.trigger("blur");

        expectValid(input);
    });

    it("marks an empty required secret invalid once it loses focus", async () => {
        const wrapper = mountComponent();
        const input = findInput(wrapper, "password", "secret");

        expectNeutral(input);

        await input.trigger("blur");

        expectInvalid(input);
    });

    it("tracks variables and secrets of the same name separately", async () => {
        const wrapper = mount(CredentialsGroupForm as object, {
            localVue,
            propsData: {
                groupData: {
                    groupId: GROUP_ID,
                    isNewGroup: true,
                    groupPayload: {
                        name: "My Group",
                        variables: [{ name: "token", value: "" }],
                        secrets: [{ name: "token", value: "" }],
                    },
                },
                serviceDefinition: {
                    ...SERVICE_DEFINITION,
                    variables: [{ name: "token", label: "Token", description: "Token name", optional: false }],
                    secrets: [{ name: "token", label: "Token", description: "Token value", optional: false }],
                },
            },
        });

        await findInput(wrapper, "token", "secret").trigger("blur");

        expectInvalid(findInput(wrapper, "token", "secret"));
        expectNeutral(findInput(wrapper, "token", "variable"));
    });
});
