import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { computed, h, ref } from "vue";

import UploadMethodViewInline from "./UploadMethodViewInline.vue";

vi.mock("./uploadMethodRegistry", () => ({
    useFilteredUploadMethods: () =>
        computed(() => [
            {
                id: "paste-links",
                name: "Paste Links",
                description: "Paste URLs",
                icon: "link",
                component: { name: "PasteLinks", render: () => h("div", { class: "paste-links-method" }) },
            },
        ]),
}));

vi.mock("@/composables/history/useTargetHistoryUploadState", () => ({
    useTargetHistoryUploadState: () => ({ uploadBlockReason: ref(null) }),
}));

vi.mock("@/composables/upload/useUploadSubmission", () => ({
    useUploadSubmission: () => ({ submitPreparedUpload: vi.fn() }),
}));

const localVue = getLocalVue();

describe("UploadMethodViewInline", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("renders the selected method component without making it reactive", () => {
        const warn = vi.spyOn(console, "warn");

        const wrapper = mount(UploadMethodViewInline as object, {
            props: { config: { targetHistoryId: "history_id" } },
            global: { ...localVue, stubs: { ...localVue.stubs, GCard: true, GTip: true } },
        });

        expect(wrapper.find(".paste-links-method").exists()).toBe(true);
        const reactiveComponentWarnings = warn.mock.calls.filter((args) =>
            String(args[0]).includes("Vue received a Component that was made a reactive object"),
        );
        expect(reactiveComponentWarnings).toEqual([]);
    });
});
