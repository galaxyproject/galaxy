import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import BasicSelectionDialog from "./BasicSelectionDialog.vue";
import DataDialogSearch from "./DataDialogSearch.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const entries = Array.from({ length: 30 }, (_, index) => ({
    id: `w${index + 1}`,
    name: `workflow ${index + 1}`,
    update_time: "2026-10-17T09:30:00",
}));

function mountDialog(getData: () => Promise<object[] | undefined>) {
    return mount(BasicSelectionDialog as object, {
        props: { getData, labelKey: "name", title: "Workflows" },
        global: getLocalVue(),
    });
}

function rowLabels(wrapper: ReturnType<typeof mount>) {
    return wrapper.findAll("td[id^='g-table-cell-label-']").map((cell) => cell.text());
}

describe("BasicSelectionDialog.vue", () => {
    it("pages the loaded entries", async () => {
        const wrapper = mountDialog(async () => entries);
        await flushPromises();
        expect(rowLabels(wrapper)).toHaveLength(25);
        expect(wrapper.findAll("td[id^='g-table-cell-time-']")).toHaveLength(25);

        await wrapper.find("[aria-label='Go to page 2']").trigger("click");
        expect(rowLabels(wrapper)).toEqual(["workflow 26", "workflow 27", "workflow 28", "workflow 29", "workflow 30"]);
    });

    it("searches the loaded entries", async () => {
        const wrapper = mountDialog(async () => entries);
        await flushPromises();

        wrapper.findComponent(DataDialogSearch).vm.$emit("input", "workflow 2");
        await flushPromises();
        expect(rowLabels(wrapper)).toHaveLength(11);
        expect(rowLabels(wrapper)[0]).toBe("workflow 2");
    });

    it("emits the clicked entry", async () => {
        const wrapper = mountDialog(async () => entries.slice(0, 2));
        await flushPromises();
        await wrapper.find("tbody tr[aria-rowindex='2']").trigger("click");
        expect((emittedArg(wrapper, "onOk") as { id: string }).id).toBe("w2");
    });

    it("shows a failed load", async () => {
        const wrapper = mountDialog(() => Promise.reject(new Error("Bad error")));
        await flushPromises();
        expect(wrapper.findComponent(GAlert).text()).toBe("Bad error");
    });
});
