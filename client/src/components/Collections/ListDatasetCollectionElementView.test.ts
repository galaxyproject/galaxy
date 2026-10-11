import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { HDASummary } from "@/api";

import ListDatasetCollectionElementView from "./ListDatasetCollectionElementView.vue";

describe("List dataset actions", () => {
    it("renders read-only pairing choices as keyboard-operable native buttons", async () => {
        const element = { id: "a", hid: 1, name: "Dataset", extension: "txt" } as HDASummary;
        const wrapper = mount(ListDatasetCollectionElementView, {
            props: { element, notEditable: true },
            global: getLocalVue(),
        });
        expect(wrapper.element.tagName).toBe("BUTTON");
        expect(wrapper.attributes("type")).toBe("button");
        expect(wrapper.text()).toContain("Dataset");
        expect(wrapper.element.querySelector("button")).toBeNull();
        await wrapper.trigger("click");
        expect(wrapper.emitted("element-is-selected")?.[0]).toEqual([element]);
    });

    it("keeps selecting, renaming and removing independent", async () => {
        const element = { id: "a", hid: 1, name: "Dataset", extension: "txt" } as HDASummary;
        const wrapper = mount(ListDatasetCollectionElementView, {
            props: { element, hasActions: true, selected: false },
            global: getLocalVue(),
        });
        expect(wrapper.attributes("role")).toBeUndefined();
        const select = wrapper.get(".dataset-selection-button");
        expect(select.attributes("aria-label")).toContain("Dataset");
        expect(select.attributes("aria-pressed")).toBe("false");
        await select.trigger("click");
        expect(wrapper.emitted("element-is-selected")).toHaveLength(1);
        await wrapper.get(".click-to-edit-label").trigger("click");
        await wrapper.get("input").setValue("Renamed");
        await wrapper.get("input").trigger("keyup.enter");
        expect(wrapper.emitted("onRename")?.[0]).toEqual(["Renamed"]);
        expect(wrapper.emitted("element-is-selected")).toHaveLength(1);
        await wrapper.get("button.btn-sm").trigger("click");
        expect(wrapper.emitted("element-is-discarded")?.[0]).toEqual([element]);
        expect(wrapper.emitted("element-is-selected")).toHaveLength(1);
    });
});
