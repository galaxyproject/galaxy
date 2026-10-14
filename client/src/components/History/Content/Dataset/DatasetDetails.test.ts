import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import DatasetDetails from "./DatasetDetails.vue";

const PEEK = '<table cellspacing="0" cellpadding="3"><tr><td>chr1</td><td>100</td></tr></table>';

describe("History DatasetDetails", () => {
    it("renders the dataset peek through v-sanitize-html", () => {
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const pinia = createTestingPinia({
            createSpy: vi.fn,
            initialState: { datasetStore: { storedDatasets: { abc: { id: "abc", state: "ok", peek: PEEK } } } },
        });

        const wrapper = shallowMount(DatasetDetails as object, {
            localVue: getLocalVue(),
            pinia,
            propsData: { id: "abc", itemUrls: {} },
        });

        expect(sanitizeHtml).toHaveBeenCalledWith(PEEK, "default");
        expect(wrapper.find("pre.dataset-peek .sanitized td").text()).toBe("chr1");
    });
});
