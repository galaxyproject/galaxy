import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";
import { createMemoryHistory, RouterLink, RouterView } from "vue-router";

import { getRouter } from "./router";

vi.mock("@/onload/loadConfig", () => ({ getAppRoot: () => "/galaxy/" }));

function stub(className: string) {
    return {
        default: defineComponent({
            inheritAttrs: false,
            setup:
                (_, { attrs }) =>
                () =>
                    h("pre", { class: className }, JSON.stringify(attrs)),
        }),
    };
}

vi.mock("./HistoryGraph.vue", () => stub("history-graph"));
vi.mock("@/components/Page/PageView.vue", () => stub("page"));
vi.mock("@/components/Workflow/Published/WorkflowPublished.vue", () => stub("workflow"));

async function render(path: string) {
    const router = getRouter(createMemoryHistory("/galaxy/"));
    await router.push(path);
    const wrapper = mount(RouterView, { global: { plugins: [router] } });
    await vi.dynamicImportSettled();
    return { router, wrapper };
}

function propsOf(wrapper: Awaited<ReturnType<typeof render>>["wrapper"], className: string) {
    return JSON.parse(wrapper.find(`.${className}`).text());
}

describe("widget routes", () => {
    it("renders the history graph with its seed", async () => {
        const { wrapper } = await render("/widgets/histories/b2/graph?seed_src=hda&seed_id=c3");
        expect(propsOf(wrapper, "history-graph")).toEqual({
            historyId: "b2",
            seedSrc: "hda",
            seedId: "c3",
        });
    });

    it.each(["?seed_src=hda&seed_src=hdca&seed_id=", "?seed_src=&seed_id="])(
        "ignores repeated and empty seed values in %s",
        async (query) => {
            const { wrapper } = await render(`/widgets/histories/b2/graph${query}`);
            expect(propsOf(wrapper, "history-graph")).toEqual({ historyId: "b2" });
        },
    );

    it("does not read an analysis path as a history id", async () => {
        const { wrapper } = await render("/widgets/histories/view/graph");
        expect(wrapper.find(".history-graph").exists()).toBe(false);
        expect(wrapper.text()).toContain("This view does not exist.");
    });

    it("renders a page in embed mode", async () => {
        const { wrapper } = await render("/widgets/pages/a1?heading=false");
        expect(propsOf(wrapper, "page")).toEqual({ pageId: "a1", showHeading: false, embed: true });
    });

    it("renders a workflow in embed mode with its view parameters", async () => {
        const { wrapper } = await render(
            "/widgets/workflows/b2?version=1&zoom=0.5&buttons=false&about=false&heading=true&minimap=false&zoom_controls=false&initialX=10&initialY=-5",
        );
        expect(propsOf(wrapper, "workflow")).toEqual({
            id: "b2",
            version: 1,
            zoom: 0.5,
            showButtons: false,
            showAbout: false,
            showHeading: true,
            showMinimap: false,
            showZoomControls: false,
            initialX: 10,
            initialY: -5,
            embed: true,
        });
    });

    it("passes the workflow version as a number", async () => {
        const { wrapper } = await render("/widgets/workflows/b2?version=3");
        expect(propsOf(wrapper, "workflow").version).toBe(3);
    });

    it.each(["2abc", "abc", "-1", "1.5"])("ignores the malformed workflow version %s", async (version) => {
        const { wrapper } = await render(`/widgets/workflows/b2?version=${version}`);
        expect(propsOf(wrapper, "workflow").version).toBeUndefined();
    });

    it.each(["?heading=false&heading=true", "?heading="])(
        "ignores repeated and empty page values in %s",
        async (query) => {
            const { wrapper } = await render(`/widgets/pages/a1${query}`);
            expect(propsOf(wrapper, "page")).toEqual({ pageId: "a1", embed: true });
        },
    );

    it("ignores repeated and empty workflow values", async () => {
        const { wrapper } = await render("/widgets/workflows/b2?zoom=1&zoom=2&version=&initialX=");
        expect(propsOf(wrapper, "workflow")).toEqual({ id: "b2", embed: true });
    });

    it("shows the missing view message for an unknown widget", async () => {
        const { wrapper } = await render("/widgets/unknown");
        expect(wrapper.text()).toContain("This view does not exist.");
    });
});

describe("links in widgets", () => {
    it("resolve Galaxy pages at the Galaxy root", async () => {
        const { router } = await render("/widgets/pages/a1");
        const link = mount(RouterLink, {
            props: { to: "/workflows/list_published?owner=user" },
            global: { plugins: [router] },
        });
        expect(link.attributes("href")).toBe("/galaxy/workflows/list_published?owner=user");
    });

    it("navigate between widgets in place", async () => {
        const { router, wrapper } = await render("/widgets/pages/a1");
        await router.push("/widgets/pages/a1?heading=false");
        await vi.dynamicImportSettled();
        expect(router.currentRoute.value.fullPath).toBe("/widgets/pages/a1?heading=false");
        expect(propsOf(wrapper, "page")).toEqual({ pageId: "a1", showHeading: false, embed: true });
    });

    it("show the missing view message outside the widgets", async () => {
        const { wrapper } = await render("/histories/list");
        expect(wrapper.text()).toContain("This view does not exist.");
    });
});
