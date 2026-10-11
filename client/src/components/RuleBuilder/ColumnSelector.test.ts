import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ColumnSelector from "./ColumnSelector.vue";
import SelectBasic from "./SelectBasic.vue";

const localVue = getLocalVue();

const COL_HEADERS = ["A", "B", "C"];

interface MountProps {
    target: number | number[];
    multiple?: boolean;
    ordered?: boolean;
    orderedEdit?: boolean;
    valueAsList?: boolean;
}

function mountColumnSelector(props: MountProps) {
    return mount(ColumnSelector, {
        props: { colHeaders: COL_HEADERS, ...props },
        global: localVue,
    });
}

function orderedTargets(wrapper: ReturnType<typeof mountColumnSelector>) {
    return wrapper.findAll(".rule-column-selector-target").map((li) => li.text());
}

describe("ColumnSelector", () => {
    it("emits the selected column index", async () => {
        const wrapper = mountColumnSelector({ target: 0 });
        wrapper.findComponent(SelectBasic).vm.$emit("input", 2);
        expect(wrapper.emitted("update:target")).toEqual([[2]]);
    });

    it("emits a single selection as a list when valueAsList is set", async () => {
        const wrapper = mountColumnSelector({ target: [0], valueAsList: true });
        wrapper.findComponent(SelectBasic).vm.$emit("input", 1);
        expect(wrapper.emitted("update:target")).toEqual([[[1]]]);
    });

    it("emits all selected indices when multiple is set", async () => {
        const wrapper = mountColumnSelector({ target: [], multiple: true });
        wrapper.findComponent(SelectBasic).vm.$emit("input", [0, 2]);
        expect(wrapper.emitted("update:target")).toEqual([[[0, 2]]]);
    });

    describe("ordered list", () => {
        const ordered = { multiple: true, ordered: true };

        it("lists the selected columns in order", () => {
            const wrapper = mountColumnSelector({ ...ordered, target: [1, 0] });
            expect(orderedTargets(wrapper)).toEqual(["B", "A"]);
        });

        it("emits a new list without the removed column", async () => {
            const target = [1, 0];
            const wrapper = mountColumnSelector({ ...ordered, target });
            await wrapper.findAll(".rule-column-selector-target-remove")[0]!.trigger("click");
            expect(wrapper.emitted("update:target")).toEqual([[[0]]]);
            expect(target).toEqual([1, 0]);
            await wrapper.setProps({ target: [0] });
            expect(orderedTargets(wrapper)).toEqual(["A"]);
        });

        it("emits a reordered list when moving a column up or down", async () => {
            const target = [1, 0, 2];
            const wrapper = mountColumnSelector({ ...ordered, target });
            await wrapper.findAll(".rule-column-selector-up")[1]!.trigger("click");
            await wrapper.findAll(".rule-column-selector-down")[0]!.trigger("click");
            expect(wrapper.emitted("update:target")).toEqual([[[1, 2, 0]], [[0, 1, 2]]]);
            expect(target).toEqual([1, 0, 2]);
            await wrapper.setProps({ target: [0, 1, 2] });
            expect(orderedTargets(wrapper)).toEqual(["A", "B", "C"]);
        });

        it("opens the column picker and emits the added column", async () => {
            const target = [1];
            const wrapper = mountColumnSelector({ ...ordered, target });
            await wrapper.find(".rule-column-selector-target-add i").trigger("click");
            expect(wrapper.emitted("update:orderedEdit")).toEqual([[true]]);

            await wrapper.setProps({ orderedEdit: true });
            const picker = wrapper.find(".rule-column-selector-target-select").findComponent(SelectBasic);
            expect(picker.props("options")).toEqual([
                { id: 0, text: "A" },
                { id: 2, text: "C" },
            ]);
            picker.vm.$emit("input", 2);
            expect(wrapper.emitted("update:target")).toEqual([[[1, 2]]]);
            expect(wrapper.emitted("update:orderedEdit")).toEqual([[true], [false]]);
            expect(target).toEqual([1]);
        });

        it("hides the add control once every column is assigned", () => {
            const wrapper = mountColumnSelector({ ...ordered, target: [0, 1, 2] });
            expect(wrapper.find(".rule-column-selector-target-add").exists()).toBe(false);
        });
    });
});
