import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { UploadItem } from "@/composables/upload/uploadItemTypes";
import { useHistoryStore } from "@/stores/historyStore";

import UploadFileRow from "./UploadFileRow.vue";

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

server.use(http.get("/api/configuration", ({ response }) => response(200).json({})));

const SwitchToHistoryLinkStub = {
    name: "SwitchToHistoryLink",
    render(h: (tag: string) => unknown) {
        return h("div");
    },
};

function baseItem(overrides: Partial<UploadItem> = {}): UploadItem {
    return {
        id: "upload-1",
        uploadMode: "paste-links",
        name: "example data",
        size: 100,
        targetHistoryId: "hist-a",
        dbkey: "?",
        extension: "auto",
        spaceToTab: false,
        toPosixLines: false,
        autoDecompress: true,
        deferred: false,
        url: "https://example.org/data/file.tsv",
        status: "queued",
        progress: 0,
        createdAt: Date.now(),
        ...overrides,
    } as UploadItem;
}

function mountRow(file: UploadItem) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const historyStore = useHistoryStore();
    historyStore.setHistory({ id: "hist-a", name: "History A" } as never);
    historyStore.setCurrentHistoryId("hist-a");

    return mount(UploadFileRow as object, {
        propsData: { file },
        localVue,
        pinia,
        router,
        stubs: {
            FontAwesomeIcon: true,
            SwitchToHistoryLink: SwitchToHistoryLinkStub,
            UtcDate: true,
        },
    });
}

describe("UploadFileRow source URL", () => {
    it.each(["paste-links", "remote-files"] as const)("shows the URL for %s uploads", (uploadMode) => {
        const wrapper = mountRow(baseItem({ uploadMode }));

        const url = wrapper.find(".source-url");
        expect(url.exists()).toBe(true);
        expect(url.text()).toContain("https://example.org/data/file.tsv");
        expect(url.attributes("title")).toBe("https://example.org/data/file.tsv");
    });

    it("hides the URL for local-file uploads", () => {
        const wrapper = mountRow(baseItem({ uploadMode: "local-file", name: "local.txt" } as Partial<UploadItem>));

        expect(wrapper.find(".source-url").exists()).toBe(false);
    });
});
