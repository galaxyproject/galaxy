import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/jest/helpers";
import { shallowMount } from "@vue/test-utils";

import { useConfig } from "@/composables/config";

import ToolSuccess from "./ToolSuccess.vue";
import ToolSuccessMessage from "./ToolSuccessMessage.vue";
import ToolRecommendation from "@/components/ToolRecommendation.vue";

jest.mock("@/composables/config", () => ({ useConfig: jest.fn() }));

const localVue = getLocalVue();
const router = injectTestRouter(localVue);

describe("ToolSuccess recommendations", () => {
    it.each([
        ["anonymous", { isAnonymous: true }, true, true],
        ["unloaded", null, true, true],
        ["registered", { id: "user-id", email: "user@example.org" }, true, true],
        ["disabled", { id: "user-id", email: "user@example.org" }, false, false],
    ])("handles %s users/configuration", (_label, currentUser, enabled, expected) => {
        jest.mocked(useConfig).mockReturnValue({
            config: { value: { enable_tool_recommendations: enabled } },
        } as ReturnType<typeof useConfig>);
        const pinia = createTestingPinia({
            createSpy: jest.fn,
            initialState: {
                userStore: { currentUser },
                jobStore: {
                    latestResponse: {
                        jobDef: { tool_id: "cat1" },
                        jobResponse: { jobs: [], outputs: [], output_collections: [] },
                        toolName: "Concatenate",
                    },
                },
            },
        });
        const wrapper = shallowMount(ToolSuccess, { localVue, router, pinia });
        expect(wrapper.findComponent(ToolRecommendation).exists()).toBe(expected);
        expect(wrapper.findComponent(ToolSuccessMessage).exists()).toBe(true);
        wrapper.destroy();
    });
});
