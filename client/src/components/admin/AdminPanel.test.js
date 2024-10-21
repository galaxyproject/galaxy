import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { useConfig } from "@/composables/config";

import MountTarget from "./AdminPanel.vue";

const localVue = getLocalVue(true);

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: { value: { enable_quotas: true, tool_shed_urls: ["tool_shed_url"], version_major: "1.0.1" } },
        isConfigLoaded: true,
    })),
}));

jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({})),
}));

function createTarget(propsData = {}) {
    return mount(MountTarget, {
        localVue,
        propsData,
        stubs: {
            routerLink: true,
        },
    });
}

describe("AdminPanel", () => {
    it("ensure section visibility with config changes", async () => {
        const options = [
            {
                name: "tool_shed_urls",
                elementId: "#admin-link-toolshed",
                value: ["toolshed_url"],
            },
            {
                name: "enable_quotas",
                elementId: "#admin-link-quotas",
                value: true,
            },
        ];
        for (const available of [true, false]) {
            for (const option of options) {
                const props = {};
                props[option.name] = available ? option.value : undefined;
                useConfig.mockImplementation(() => ({
                    config: { value: { ...props, version_major: "1.0.1" } },
                    isConfigLoaded: true,
                }));
                const wrapper = createTarget();
                expect(wrapper.find(option.elementId).exists()).toBe(available);
            }
        }
    });
});
