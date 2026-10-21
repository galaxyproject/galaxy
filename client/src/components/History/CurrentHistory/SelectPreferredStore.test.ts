import { emittedArg, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, disposePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import type { UpdateHistoryPayload } from "@/api/histories";
import { Toast } from "@/composables/toast";
import { ROOT_COMPONENT } from "@/utils/navigation/schema";

import { setupSelectableMock } from "../../ObjectStore/mockServices";

import SelectPreferredStore from "./SelectPreferredStore.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

vi.mock("@/composables/toast");

const { server, http } = useServerMock();

setupSelectableMock();

const localVue = getLocalVue(true);

const CONFIRM_BUTTON_SELECTOR = ".g-modal-confirm-buttons .g-button.g-blue" as const;

const TEST_HISTORY_ID = "myTestHistoryId";

const TEST_HISTORY = {
    id: TEST_HISTORY_ID,
    preferred_object_store_id: null,
};

interface PutRequest {
    url: string;
    data: UpdateHistoryPayload;
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
            const data = (await request.json()) as UpdateHistoryPayload;
            putRequests.push({ url: request.url, data });
            return HttpResponse.json({}, { status: 202 });
        }),
    );

    const pinia = createPinia();
    onTestFinished(() => disposePinia(pinia));
    const wrapper = mount(SelectPreferredStore, {
        props: {
            preferredObjectStoreId,
            history: TEST_HISTORY,
            show: true,
        },
        global: withPlugins(localVue, pinia),
    });

    await flushPromises();

    return wrapper;
}

const PREFERENCES = ROOT_COMPONENT.preferences;

describe("SelectPreferredStore.vue", () => {
    beforeEach(() => {
        putRequests = [];
        vi.mocked(Toast.error).mockClear();
    });
    enableAutoUnmount(afterEach);

    it("updates object store to default on selection null", async () => {
        const wrapper = await mountComponent("object_store_1");
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);
        const selectedOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "__null__" }).selector,
        );
        expect(selectedOption.exists()).toBeTruthy();
        await selectedOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();

        const okButton = wrapper.get(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(putRequests.length).toBe(1);
        expect(putRequests[0]?.data.preferred_object_store_id).toEqual(null);

        expect(emittedArg(wrapper, "updated")).toEqual(null);
    });

    it("updates object store to a non-null selection", async () => {
        const wrapper = await mountComponent();
        const els = wrapper.findAll(PREFERENCES.object_store_selection.option_cards.selector);
        expect(els.length).toBe(3);
        const selectedOption = wrapper.find(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "object_store_2" }).selector,
        );
        expect(selectedOption.exists()).toBeTruthy();
        await selectedOption.trigger("click");
        await flushPromises();
        const errorEl = wrapper.find(".object-store-selection-error");
        expect(errorEl.exists()).toBeFalsy();

        const okButton = wrapper.get(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(putRequests.length).toBe(1);
        expect(putRequests[0]?.data.preferred_object_store_id).toEqual("object_store_2");

        expect(emittedArg(wrapper, "updated")).toEqual("object_store_2");
    });

    it("keeps the modal open and shows a toast when the storage update request fails", async () => {
        const wrapper = await mountComponent();
        server.use(
            http.untyped.put(`/api/histories/${TEST_HISTORY_ID}`, () => {
                return HttpResponse.json({ err_msg: "failed to update" }, { status: 500 });
            }),
        );

        const selectedOption = wrapper.get(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "object_store_2" }).selector,
        );
        await selectedOption.trigger("click");
        await flushPromises();

        const okButton = wrapper.get(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(wrapper.getComponent(GModal).props("show")).toBe(true);
        expect(emittedArg(wrapper, "update:show", -1)).not.toBe(false);
        expect(Toast.error).toHaveBeenCalledWith("failed to update", "Failed to update history storage location");
    });

    it("closes modal on a successful update", async () => {
        const wrapper = await mountComponent();
        const selectedOption = wrapper.get(
            PREFERENCES.object_store_selection.option_card_select({ object_store_id: "object_store_2" }).selector,
        );
        await selectedOption.trigger("click");
        await flushPromises();

        const okButton = wrapper.get(CONFIRM_BUTTON_SELECTOR);
        await okButton.trigger("click");

        await flushPromises();

        expect(emittedArg(wrapper, "update:show", -1)).toBe(false);
    });
});
