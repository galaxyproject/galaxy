import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import type { HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";
import type { NewUploadItem } from "@/composables/upload/uploadItemTypes";
import { useHistoryStore } from "@/stores/historyStore";

import UploadFileRow from "./UploadFileRow.vue";
import CopyToClipboard from "@/components/CopyToClipboard.vue";

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

server.use(http.get("/api/configuration", ({ response }) => response(200).json({})));

const HISTORY: HistorySummary = {
    id: "hist-a",
    name: "History A",
    archived: false,
    deleted: false,
    annotation: "",
    count: 0,
    model_class: "History",
    published: false,
    purged: false,
    tags: [],
    update_time: "2024-01-01T00:00:00Z",
    url: "/api/histories/hist-a",
};

function urlRowItem<T extends NewUploadItem>(item: T) {
    return { ...item, id: "upload-1", status: "queued" as const, progress: 0, createdAt: 0 };
}

describe("UploadFileRow source URL", () => {
    it("renders the source URL from the item display info", () => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        const historyStore = useHistoryStore();
        historyStore.setHistory(HISTORY);
        historyStore.setCurrentHistoryId(HISTORY.id);

        const wrapper = mount(UploadFileRow as object, {
            propsData: { file: urlRowItem(makeUrlItem()) },
            localVue,
            pinia,
            router,
            stubs: {
                CopyToClipboard: true,
                FontAwesomeIcon: true,
                SwitchToHistoryLink: true,
                UtcDate: true,
            },
        });

        const url = wrapper.find(".source-url-text");
        expect(url.exists()).toBe(true);
        expect(url.text()).toContain("http://example.com/file.txt");
        expect(url.attributes("title")).toBe("http://example.com/file.txt");

        const copyIcon = wrapper.findComponent(CopyToClipboard);
        expect(copyIcon.exists()).toBe(true);
        expect(copyIcon.props("text")).toBe("http://example.com/file.txt");
    });
});
