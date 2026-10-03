import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http, HttpResponse } from "msw";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { h, nextTick, ref } from "vue";

import type { HistorySummary } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import type { PreparedUpload } from "@/components/Panels/Upload/types";
import { makeUrlItem } from "@/composables/upload/testHelpers/uploadFixtures";
import { useHistoryStore } from "@/stores/historyStore";
import { buildPreparedUpload } from "@/utils/upload";

import { useUploadState } from "./uploadState";

import UploadMethodView from "./UploadMethodView.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: ref({}), isConfigLoaded: ref(true) }),
}));

const methodComponent = vi.hoisted(() => ({ prepared: null as PreparedUpload | null }));

vi.mock("./uploadMethodRegistry", async (importOriginal: () => Promise<Record<string, unknown>>) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getUploadMethod: () => ({
            id: "paste-links",
            name: "Paste Links",
            requiresTargetHistory: true,
            component: {
                render: () => h("div"),
                mounted(this: { $emit: (event: string, ready: boolean) => void }) {
                    this.$emit("ready", true);
                },
                methods: {
                    prepareUpload: () => methodComponent.prepared,
                },
            },
        }),
    };
});

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const { server } = useServerMock();

server.use(http.get("/api/configuration", () => HttpResponse.json({})));

function makeHistory(id: string, name: string): HistorySummary {
    return {
        id,
        name,
        archived: false,
        deleted: false,
        annotation: "",
        count: 0,
        model_class: "History",
        published: false,
        purged: false,
        tags: [],
        update_time: "2024-01-01T00:00:00Z",
        url: `/api/histories/${id}`,
    };
}

function seedHistories(historyStore: ReturnType<typeof useHistoryStore>) {
    historyStore.setHistory(makeHistory("hist-a", "History A"));
    historyStore.setHistory(makeHistory("hist-b", "History B"));
    historyStore.setCurrentHistoryId("hist-a");
}

function mountView() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const historyStore = useHistoryStore();
    seedHistories(historyStore);

    const wrapper = mount(UploadMethodView as object, {
        propsData: { methodId: "paste-links" },
        localVue,
        pinia,
        router,
        stubs: {
            GTip: true,
            TargetHistorySelector: true,
            TargetObjectStoreSelector: true,
        },
    });

    return { wrapper, historyStore };
}

function mismatchAlert(wrapper: ReturnType<typeof mount>) {
    return wrapper.find('[data-test-id="upload-history-mismatch-alert"]');
}

describe("UploadMethodView history mismatch alert", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("hides the alert when target and current histories match", () => {
        const { wrapper } = mountView();

        expect(mismatchAlert(wrapper).exists()).toBe(false);
    });

    it("shows the alert with both history names after the current history changes", async () => {
        const { wrapper, historyStore } = mountView();

        historyStore.setCurrentHistoryId("hist-b");
        await nextTick();

        const alert = mismatchAlert(wrapper);
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("History A");
        expect(alert.text()).toContain("History B");
        expect(alert.findComponent(GAlert).props("dismissible")).toBe(true);
    });

    it("dismisses the alert and shows it again after another history change", async () => {
        const { wrapper, historyStore } = mountView();

        historyStore.setHistory(makeHistory("hist-c", "History C"));
        historyStore.setCurrentHistoryId("hist-b");
        await nextTick();
        expect(mismatchAlert(wrapper).exists()).toBe(true);

        await mismatchAlert(wrapper).find("button.close").trigger("click");
        expect(mismatchAlert(wrapper).exists()).toBe(false);

        historyStore.setCurrentHistoryId("hist-c");
        await nextTick();
        expect(mismatchAlert(wrapper).exists()).toBe(true);
    });

    it("hides the alert when the histories match again", async () => {
        const { wrapper, historyStore } = mountView();

        historyStore.setCurrentHistoryId("hist-b");
        await nextTick();
        expect(mismatchAlert(wrapper).exists()).toBe(true);

        historyStore.setCurrentHistoryId("hist-a");
        await nextTick();
        expect(mismatchAlert(wrapper).exists()).toBe(false);
    });
});

describe("UploadMethodView start", () => {
    const unhandledRejections: unknown[] = [];
    const recordUnhandledRejection = (reason: unknown) => unhandledRejections.push(reason);

    beforeEach(() => {
        unhandledRejections.length = 0;
        process.on("unhandledRejection", recordUnhandledRejection);
        useUploadState().clearAll();
    });

    afterEach(() => {
        process.off("unhandledRejection", recordUnhandledRejection);
        useUploadState().clearAll();
    });

    it("records a rejected upload request in the upload state without leaving an unhandled rejection", async () => {
        server.use(
            http.get("/api/object_stores", () => HttpResponse.json([])),
            http.post("/api/tools/fetch", () =>
                HttpResponse.json(
                    { err_msg: "Action requires account activation.", err_code: 403007 },
                    { status: 403 },
                ),
            ),
        );
        const item = makeUrlItem({ name: "remote.txt", targetHistoryId: "hist-a" });
        methodComponent.prepared = buildPreparedUpload([item]);
        const { wrapper } = mountView();
        await flushPromises();

        await wrapper.find('[data-test-id="start-upload"]').trigger("click");
        await flushPromises();
        await new Promise((resolve) => setTimeout(resolve, 0));

        const [upload] = useUploadState().activeItems.value;
        expect(upload?.status).toBe("error");
        expect(upload?.error).toBe("Action requires account activation.");
        expect(unhandledRejections).toEqual([]);
    });
});
