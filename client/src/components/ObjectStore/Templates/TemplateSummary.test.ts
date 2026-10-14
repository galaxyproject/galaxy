import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { STANDARD_OBJECT_STORE_TEMPLATE } from "@/components/ConfigTemplates/test_fixtures";

import TemplateSummary from "./TemplateSummary.vue";
import ObjectStoreBadges from "@/components/ObjectStore/ObjectStoreBadges.vue";

const localVue = getLocalVue(true);

describe("TemplateSummary", () => {
    it("shows badges without interactive popovers, since it is shown inside one", () => {
        const wrapper = shallowMount(TemplateSummary as object, {
            props: { template: STANDARD_OBJECT_STORE_TEMPLATE },
            global: localVue,
        });
        expect(wrapper.findComponent(ObjectStoreBadges).props("interactive")).toBe(false);
    });
});
