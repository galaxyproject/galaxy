import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { STANDARD_FILE_SOURCE_TEMPLATE } from "./test_fixtures";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";

const localVue = getLocalVue(true);

describe("TemplateSummaryPopover", () => {
    it("should render a secrets for for file source templates", async () => {
        const wrapper = shallowMount(TemplateSummaryPopover as object, {
            propsData: {
                template: STANDARD_FILE_SOURCE_TEMPLATE,
                target: "popover-target",
            },
            localVue,
        });
        const popover = wrapper.findComponent({ name: "BPopover" });
        expect(popover.attributes().target).toEqual("popover-target");
    });
});
