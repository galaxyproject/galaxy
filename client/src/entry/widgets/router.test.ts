import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";
import { createMemoryHistory, RouterView } from "vue-router";

import { getRouter } from "./router";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));

vi.mock("./HistoryGraph.vue", () => ({
    default: defineComponent({
        inheritAttrs: false,
        setup:
            (_, { attrs }) =>
            () =>
                h("pre", { class: "history-graph" }, JSON.stringify(attrs)),
    }),
}));

async function render(path: string) {
    const router = getRouter(createMemoryHistory());
    await router.push(path);
    const wrapper = mount(RouterView, { global: { plugins: [router] } });
    await vi.dynamicImportSettled();
    return wrapper;
}

describe("widget routes", () => {
    it("renders the history graph with its seed", async () => {
        const wrapper = await render("/histories/b2/graph?seed_src=hda&seed_id=c3");
        expect(JSON.parse(wrapper.find(".history-graph").text())).toEqual({
            historyId: "b2",
            seedSrc: "hda",
            seedId: "c3",
        });
    });

    it.each(["?seed_src=hda&seed_src=hdca&seed_id=", "?seed_src=&seed_id="])(
        "ignores repeated and empty seed values in %s",
        async (query) => {
            const wrapper = await render(`/histories/b2/graph${query}`);
            expect(JSON.parse(wrapper.find(".history-graph").text())).toEqual({ historyId: "b2" });
        },
    );

    it("does not read an analysis path as a history id", async () => {
        const wrapper = await render("/histories/view/graph");
        expect(wrapper.find(".history-graph").exists()).toBe(false);
        expect(wrapper.text()).toContain("This view does not exist.");
    });
});
