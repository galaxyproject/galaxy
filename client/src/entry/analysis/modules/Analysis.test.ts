import { createTestingPinia } from "@pinia/testing";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { expect, it, vi } from "vitest";
import { defineComponent, h } from "vue";
import { createMemoryHistory, createRouter } from "vue-router";

import Analysis from "./Analysis.vue";

vi.mock("./CenterFrame.vue", () => ({ default: {} }));
vi.mock("@/components/ActivityBar/ActivityBar.vue", () => ({ default: {} }));
vi.mock("@/components/GalaxyAI.vue", () => ({ default: {} }));
vi.mock("@/components/GalaxyAI/ChatPanel.vue", () => ({ default: {} }));
vi.mock("@/components/History/Index.vue", () => ({ default: {} }));
vi.mock("@/components/Panels/FlexPanel.vue", () => ({ default: {} }));
vi.mock("@/components/Upload/DragAndDropModal.vue", () => ({ default: {} }));

it("remounts routes that have not opted into query reuse, such as legacy invocation reports", async () => {
    let mounts = 0;
    const Page = defineComponent({
        name: "SelectionTestPage",
        setup() {
            const instance = ++mounts;
            return () => h("div", { "data-page-instance": instance });
        },
    });
    const router = createRouter({
        history: createMemoryHistory(),
        routes: [{ path: "/workflows/invocations/report", component: Page }],
    });
    await router.push("/workflows/invocations/report?id=first");
    const wrapper = shallowMount(Analysis, {
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn }), router],
            stubs: { RouterView: false, SelectionTestPage: false },
        },
    });
    const instance = () => wrapper.get("[data-page-instance]").attributes("data-page-instance");
    await flushPromises();
    const firstReportInstance = instance();
    await router.push("/workflows/invocations/report?id=second");
    await flushPromises();
    expect(instance()).not.toBe(firstReportInstance);
    wrapper.unmount();
});
