import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import HistoryStorageOperationsIndicator from "./HistoryStorageOperationsIndicator.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

vi.mock("@/composables/useStorageRunWatcher", () => ({
    useStorageHistoryRunsWatcher: () => ({ startPolling: vi.fn(), stopPolling: vi.fn() }),
}));

describe("HistoryStorageOperationsIndicator", () => {
    it("lets keyboard users reach the link in the storage helper popover", () => {
        const wrapper = mount(HistoryStorageOperationsIndicator as object, {
            props: { historyId: "history_id", showSelection: false, activeStorageRunCount: 1 },
            global: withPlugins(getLocalVue(), createTestingPinia({ createSpy: vi.fn })),
        });

        const popover = wrapper.findComponent(GPopover);
        expect(popover.props("interactive")).toBe(true);
        expect(popover.props("ariaLabel")).toBe("Background storage operations");
        expect(wrapper.find("#history-storage-operations-history_id").attributes("aria-label")).toBe(
            "Background operations are running",
        );

        wrapper.unmount();
    });
});
