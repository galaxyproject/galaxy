import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import DatasetActions from "./DatasetActions.vue";
import ExportForGalaxyLink from "@/components/History/Content/ExportForGalaxyLink.vue";

function hasGalaxyLink(item: Record<string, unknown>) {
    const wrapper = shallowMount(DatasetActions as object, {
        localVue: getLocalVue(),
        propsData: {
            item: { id: "d1", history_id: "h1", purged: false, visible: true, state: "ok", ...item },
            itemUrls: { edit: "", showDetails: null },
            writable: true,
            showHighlight: false,
        },
    });
    return wrapper.findComponent(ExportForGalaxyLink).exists();
}

describe("DatasetActions", () => {
    it("offers a link for another Galaxy on a visible dataset that is ok", () => {
        expect(hasGalaxyLink({})).toBe(true);
    });

    it("offers no link for a hidden dataset, which the other Galaxy would import out of sight", () => {
        expect(hasGalaxyLink({ visible: false })).toBe(false);
    });

    it("offers no link for a dataset in error, which has no data to move", () => {
        expect(hasGalaxyLink({ state: "error" })).toBe(false);
    });
});
