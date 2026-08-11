import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";
import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import { setupSelectableMock } from "../../ObjectStore/mockServices";

import SelectPreferredStore from "./SelectPreferredStore.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/composables/toast", () => {
    const toastInstance = { success: vi.fn(), error: vi.fn() };
    return {
        Toast: toastInstance,
        useToast: () => toastInstance,
    };
});

const { server, http } = useServerMock();

setupSelectableMock();

const localVue = getLocalVue(true);

const CONFIRM_BUTTON_SELECTOR = ".g-button.g-blue" as const;

const TEST_HISTORY_ID = "myTestHistoryId";

const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    preferred_object_store_id: null,
};

interface PutRequest {
    url: string;
    data: Record<string, unknown>;
}

let putRequests: PutRequest[] = [];

async function mountComponent(preferredObjectStoreId: string | null = null) {
    server.use(
        http.get("/api/configuration", ({ response }) => {
            return response(200).json({});
        }),
        http.get("/api/users/{user_id}/usage/{label}", ({ response }) => {
            return response(200).json({
                total_disk_usage: 0,
            });
        }),
        http.untyped.put(`/api/histories/${TEST_HISTORY_ID}`, async ({ request }) => {
            const data = (await request.json()) as Record<string, unknown>;
            putRequests.push({ url: request.url, data });
            return HttpResponse.json({}, { status: 202 });
        }),
    );

    const wrapper = mount(SelectPreferredStore as object, {
        propsData: {
            preferredObjectStoreId: preferredObjectStoreId,
            history: TEST_HISTORY,
            showModal: true,
        },
        localVue,
    });

    await flushPromises();

    return wrapper;
}

const PREFERENCES = ROOT_COMPONENT.preferences;

describe("SelectPreferredStore.vue", () => {
    beforeEach(async () => {
        putRequests = [];
        vi.clearAllMocks();
    });

    it("updates object store to default on selection null", async () => {
        const wrapper = await mountComponent("object_store_1");
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "__null__" }).selector,
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();

        const okButton = wrapper.find(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(putRequests.length).toBe(1);
        expect(putRequests[0]?.data.preferred_object_store_id).toEqual(null);

        const emitted = wrapper.emitted();
        expect(emitted["updated"]?.[0]?.[0]).toEqual(null);
    });

    it("updates object store to on non-null selection", async () => {
        const wrapper = await mountComponent();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);
        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "object_store_2" }).selector,
        );
        expect(galaxyDefaultOption.exists()).toBeTruthy();
        await galaxyDefaultOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();

        const okButton = wrapper.find(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(putRequests.length).toBe(1);
        expect(putRequests[0]?.data.preferred_object_store_id).toEqual("object_store_2");

        const emitted = wrapper.emitted();
        expect(emitted["updated"]?.[0]?.[0]).toEqual("object_store_2");
    });

    it("keeps the modal open and shows a toast when the storage update request fails", async () => {
        server.use(
            http.untyped.put(`/api/histories/${TEST_HISTORY_ID}`, () => {
                return HttpResponse.json({ err_msg: "failed to update" }, { status: 500 });
            }),
        );

        const wrapper = mount(SelectPreferredStore as object, {
            propsData: {
                preferredObjectStoreId: null,
                history: TEST_HISTORY,
                showModal: true,
            },
            localVue,
        });

        await flushPromises();

        const galaxyDefaultOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "object_store_2" }).selector,
        );
        await galaxyDefaultOption.trigger("click");
        await flushPromises();

        const okButton = wrapper.find(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(wrapper.emitted("close")).toBeFalsy();
        expect(Toast.error).toHaveBeenCalledWith("failed to update", "Failed to update history storage location");
    });
});
