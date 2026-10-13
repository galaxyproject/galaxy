import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { AnyFetchTarget } from "@/api/tools";

import FetchGrid from "./FetchGrid.vue";
import DataFetchRequestParameter from "@/components/JobParameters/DataFetchRequestParameter.vue";

vi.mock("ag-grid-vue3", () => ({
    AgGridVue: defineComponent({
        name: "AgGridVue",
        props: { rowData: { type: Array, default: () => [] }, columnDefs: { type: Array, default: () => [] } },
        emits: ["cellValueChanged"],
        render() {
            return h("div", JSON.stringify(this.rowData));
        },
    }),
}));

const localVue = getLocalVue(true);

const { server, http } = useServerMock();
beforeEach(() => {
    server.use(
        http.get("/api/configuration", ({ response }) => response(200).json({})),
        http.get("/api/genomes", ({ response }) => response(200).json([])),
        http.get("/api/datatypes", ({ response }) => response(200).json([])),
    );
});

function urlTarget(url: string): AnyFetchTarget {
    return {
        destination: { type: "hdas" },
        elements: [{ src: "url", url, ext: "txt" }],
    } as unknown as AnyFetchTarget;
}

describe("FetchGrid", () => {
    it("drops edited rows when replaced by an unsupported target and recovers for supported targets", async () => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        const wrapper = mount(FetchGrid, {
            props: { target: urlTarget("http://example.com/a.txt") },
            global: withPlugins(localVue, pinia),
            attachTo: document.body,
        });
        await flushPromises();
        await vi.waitFor(() => expect(wrapper.findComponent({ name: "AgGridVue" }).exists()).toBe(true));
        const oldGrid = wrapper.findComponent({ name: "AgGridVue" });
        expect(oldGrid.exists()).toBe(true);
        const rows = oldGrid.props("rowData");
        oldGrid.vm.$emit("cellValueChanged", {});
        await flushPromises();
        const unsupported = {
            destination: { type: "hdas" },
            elements_from: "https://example.com/archive.zip",
            src: "url",
        } as unknown as AnyFetchTarget;
        await wrapper.setProps({ target: unsupported });
        await flushPromises();
        expect(wrapper.findComponent({ name: "AgGridVue" }).exists()).toBe(false);
        expect(wrapper.findComponent(DataFetchRequestParameter).props("parameterValue")).toEqual(unsupported);
        // Even a late event from the discarded table must never serialize its old URLs.
        oldGrid.vm.$emit("cellValueChanged", {});
        expect((wrapper.vm as unknown as { asTarget: () => AnyFetchTarget }).asTarget()).toEqual(unsupported);
        await wrapper.setProps({ target: urlTarget("http://example.com/new.txt") });
        await flushPromises();
        await vi.waitFor(() => expect(wrapper.text()).toContain("http://example.com/new.txt"));
        expect(wrapper.text()).not.toContain("http://example.com/a.txt");
        expect(wrapper.findComponent({ name: "AgGridVue" }).props("rowData")).not.toBe(rows);
        wrapper.unmount();
    });
    it("shows the rows of each new target", async () => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        const wrapper = mount(FetchGrid, {
            props: { target: urlTarget("http://example.com/a.txt") },
            global: withPlugins(localVue, pinia),
            attachTo: document.body,
        });
        await flushPromises();
        await vi.waitFor(() => expect(wrapper.text()).toContain("http://example.com/a.txt"));

        for (const url of ["http://example.com/b.txt", "http://example.com/c.txt"]) {
            await wrapper.setProps({ target: urlTarget(url) });
            await flushPromises();
            await vi.waitFor(() => expect(wrapper.text()).toContain(url));
        }
        wrapper.unmount();
    });
});
