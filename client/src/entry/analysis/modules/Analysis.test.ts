import { createTestingPinia } from "@pinia/testing";
import { createTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { defineComponent, h, onMounted } from "vue";

import Analysis from "./Analysis.vue";

vi.mock("@/components/ActivityBar/ActivityBar.vue", () => ({ default: { name: "ActivityBar", render: () => null } }));
vi.mock("@/components/History/Index.vue", () => ({ default: { name: "HistoryIndex", render: () => null } }));
vi.mock("@/components/GalaxyAI.vue", () => ({ default: { name: "GalaxyAI", render: () => null } }));
vi.mock("@/components/GalaxyAI/ChatPanel.vue", () => ({ default: { name: "ChatPanel", render: () => null } }));
vi.mock("@/components/Upload/DragAndDropModal.vue", () => ({
    default: { name: "DragAndDropModal", render: () => null },
}));
vi.mock("@/entry/analysis/modules/CenterFrame.vue", () => ({
    default: { name: "CenterFrame", render: () => null },
}));

function countingPage(name: string, mounts: string[]) {
    return defineComponent({
        name,
        setup() {
            onMounted(() => mounts.push(name));
            return () => h("div", name);
        },
    });
}

async function mountAnalysis() {
    const mounts: string[] = [];
    const router = createTestRouter([
        { path: "/tools/list", component: countingPage("ToolsList", mounts) },
        { path: "/other", component: countingPage("Other", mounts) },
    ]);
    await router.push("/tools/list?search=fastqc");
    mount(Analysis, {
        global: {
            plugins: [router, createTestingPinia({ createSpy: vi.fn })],
            stubs: { FlexPanel: true, GButton: true },
        },
    });
    await flushPromises();
    return { mounts, router };
}

describe("Analysis", () => {
    it("keeps the tools list mounted while only its query changes", async () => {
        const { mounts, router } = await mountAnalysis();
        expect(mounts).toEqual(["ToolsList"]);

        await router.push("/tools/list?tag=collection_ops");
        await router.push("/tools/list");
        await flushPromises();
        expect(mounts).toEqual(["ToolsList"]);
    });

    it("mounts other pages afresh when their query changes", async () => {
        const { mounts, router } = await mountAnalysis();

        await router.push("/other?x=1");
        await router.push("/other?x=2");
        await flushPromises();
        expect(mounts).toEqual(["ToolsList", "Other", "Other"]);
    });
});
