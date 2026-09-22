import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { useHistoryStore } from "@/stores/historyStore";

import UploadMethodView from "./UploadMethodView.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: ref({}), isConfigLoaded: ref(true) }),
}));

vi.mock("./uploadMethodRegistry", async (importOriginal: () => Promise<Record<string, unknown>>) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getUploadMethod: () => ({
            id: "local-file",
            name: "Upload from Computer",
            requiresTargetHistory: true,
            component: { render: (h: never) => h("div") },
        }),
    };
});

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

server.use(http.get("/api/configuration", ({ response }) => response(200).json({})));

const TargetHistorySelectorStub = {
    name: "TargetHistorySelector",
    render(h: (tag: string) => unknown) {
        return h("div");
    },
};

function seedHistories(historyStore: ReturnType<typeof useHistoryStore>) {
    historyStore.setHistory({ id: "hist-a", name: "History A" } as never);
    historyStore.setHistory({ id: "hist-b", name: "History B" } as never);
    historyStore.setCurrentHistoryId("hist-a");
}

function mountView() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const historyStore = useHistoryStore();
    seedHistories(historyStore);

    const wrapper = mount(UploadMethodView as object, {
        propsData: { methodId: "local-file" },
        localVue,
        pinia,
        router,
        stubs: {
            GTip: true,
            TargetHistorySelector: TargetHistorySelectorStub,
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

        historyStore.setHistory({ id: "hist-c", name: "History C" } as never);
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
