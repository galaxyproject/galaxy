import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { UserFileSourceModel } from "@/api/fileSources";

import FileSourceInstanceDropdown from "./InstanceDropdown.vue";
import ConfigurationInstanceDropdown from "@/components/ConfigTemplates/InstanceDropdown.vue";

const { toastErrorMock } = vi.hoisted(() => ({
    toastErrorMock: vi.fn(),
}));

vi.mock("@/composables/toast", () => ({
    Toast: {
        error: toastErrorMock,
    },
}));

vi.mock("@/stores/fileSourceTemplatesStore", () => ({
    useFileSourceTemplatesStore: () => ({
        canUpgrade: () => false,
    }),
}));

const { server, http } = useServerMock();

const FILE_SOURCE: UserFileSourceModel = {
    uuid: "test-file-source-id",
    name: "Test File Source",
    description: null,
    template_id: "simple_variable",
    template_version: 0,
    active: true,
    hidden: false,
    purged: false,
    secrets: [],
    type: "posix",
    uri_root: "gxfiles://test-file-source-id",
    variables: null,
};

describe("File Source Instance Dropdown", () => {
    const localVue = getLocalVue(true);

    beforeEach(() => {
        server.resetHandlers();
        toastErrorMock.mockClear();
    });

    it("emits entryRemoved when remove succeeds", async () => {
        let requestBody: Record<string, unknown> | undefined;
        server.use(
            http.put("/api/file_source_instances/{uuid}", async ({ request, response }) => {
                requestBody = (await request.json()) as Record<string, unknown>;
                return response(200).json(FILE_SOURCE);
            }),
        );

        const wrapper = shallowMount(FileSourceInstanceDropdown as object, {
            localVue,
            propsData: {
                fileSource: FILE_SOURCE,
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
            http.put("/api/file_source_instances/{uuid}", ({ response }) => {
                return response("4XX").json({ err_code: 400, err_msg: "Unable to remove" }, { status: 400 });
            }),
        );

        const wrapper = shallowMount(FileSourceInstanceDropdown as object, {
            localVue,
            propsData: {
                fileSource: FILE_SOURCE,
            },
        });

        wrapper.findComponent(ConfigurationInstanceDropdown).vm.$emit("remove");
        await flushPromises();

        expect(toastErrorMock).toHaveBeenCalledWith("Unable to remove", "Failed to remove instance");
        expect(wrapper.emitted("entryRemoved")).toBeFalsy();
    });
});
