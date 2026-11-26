import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount, shallowMount } from "@vue/test-utils";
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

    it("renders the database build as a button that asks to edit the dataset", async () => {
        const pinia = createTestingPinia({
            createSpy: vi.fn,
            initialState: {
                datasetStore: { storedDatasets: { abc: { id: "abc", state: "ok", peek: "", genome_build: "hg38" } } },
            },
        });
        const outerClick = vi.fn();

        const wrapper = mount(
            {
                components: { DatasetDetails },
                template: '<div @click="outerClick"><DatasetDetails v-bind="$attrs" /></div>',
                methods: { outerClick },
            },
            {
                attrs: { id: "abc", itemUrls: {} },
                global: {
                    ...withPlugins(getLocalVue(), pinia),
                    stubs: { DatasetActions: true, DatasetMiscInfo: true },
                },
            },
        );

        const dbkey = wrapper.find('.dbkey [data-label="Database/Build"]');
        expect(dbkey.element.tagName).toBe("BUTTON");
        expect(dbkey.classes()).toContain("value");
        expect(dbkey.text()).toBe("hg38");

        await dbkey.trigger("click");

        expect(wrapper.findComponent(DatasetDetails).emitted("edit")).toHaveLength(1);
        expect(outerClick).not.toHaveBeenCalled();
    });
});
