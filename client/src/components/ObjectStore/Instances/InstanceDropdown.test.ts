import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import type { UserConcreteObjectStore } from "./types";

import ObjectStoreInstanceDropdown from "./InstanceDropdown.vue";
import ConfigurationInstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

const { toastErrorMock } = vi.hoisted(() => ({
    toastErrorMock: vi.fn(),
}));

vi.mock("@/composables/toast", () => ({
    Toast: {
        error: toastErrorMock,
    },
}));

vi.mock("@/stores/objectStoreTemplatesStore", () => ({
    useObjectStoreTemplatesStore: () => ({
        canUpgrade: () => false,
    }),
}));

const { server, http } = useServerMock();

const OBJECT_STORE: UserConcreteObjectStore = {
    uuid: "test-object-store-id",
    name: "Test Object Store",
    description: null,
    template_id: "simple_variable",
    template_version: 0,
    active: true,
    hidden: false,
    purged: false,
    private: false,
    object_store_id: null,
    device: null,
    object_expires_after_days: null,
    badges: [],
    quota: { enabled: false },
    secrets: [],
    type: "disk",
    variables: null,
};

describe("Object Store Instance Dropdown", () => {
    const localVue = getLocalVue(true);

    beforeEach(() => {
        server.resetHandlers();
        toastErrorMock.mockClear();
    });

    it("emits entryRemoved when remove succeeds", async () => {
        let requestBody: Record<string, unknown> | undefined;
        server.use(
            http.put("/api/object_store_instances/{uuid}", async ({ request, response }) => {
                requestBody = (await request.json()) as Record<string, unknown>;
                return response(200).json(OBJECT_STORE);
            }),
        );

        const wrapper = shallowMount(ObjectStoreInstanceDropdown as object, {
            localVue,
            propsData: {
                objectStore: OBJECT_STORE,
            },
        });

        wrapper.findComponent(ConfigurationInstanceDropdown).vm.$emit("remove");
        await flushPromises();

        expect(requestBody).toEqual({ hidden: true });
        expect(wrapper.emitted("entryRemoved")).toBeTruthy();
        expect(toastErrorMock).not.toHaveBeenCalled();
    });

    it("shows toast and does not emit entryRemoved when remove fails", async () => {
        server.use(
            http.put("/api/object_store_instances/{uuid}", ({ response }) => {
                return response("4XX").json({ err_code: 400, err_msg: "Unable to remove" }, { status: 400 });
            }),
        );

        const wrapper = shallowMount(ObjectStoreInstanceDropdown as object, {
            localVue,
            propsData: {
                objectStore: OBJECT_STORE,
            },
        });

        wrapper.findComponent(ConfigurationInstanceDropdown).vm.$emit("remove");
        await flushPromises();

        expect(toastErrorMock).toHaveBeenCalledWith("Unable to remove", "Failed to remove instance");
        expect(wrapper.emitted("entryRemoved")).toBeFalsy();
    });
});
