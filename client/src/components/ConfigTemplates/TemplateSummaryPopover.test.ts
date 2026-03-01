import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { STANDARD_FILE_SOURCE_TEMPLATE } from "./test_fixtures";

import TemplateSummaryPopover from "./TemplateSummaryPopover.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

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
        const popover = wrapper.findComponent(GPopover);
        expect(popover.props("target")).toEqual("popover-target");
    });
});
