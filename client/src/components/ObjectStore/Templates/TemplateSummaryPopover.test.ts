import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { STANDARD_OBJECT_STORE_TEMPLATE } from "@/components/ConfigTemplates/test_fixtures";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";

const localVue = getLocalVue(true);

describe("TemplateSummaryPopover", () => {
    it("should render a popover", async () => {
        const wrapper = shallowMount(TemplateSummaryPopover, {
            propsData: {
                target: "test-target-1",
                template: STANDARD_OBJECT_STORE_TEMPLATE,
            },
            localVue,
        });
        const configPopover = wrapper.find("[target='test-target-1']");
        expect(configPopover.exists()).toBeTruthy();
    });
});
