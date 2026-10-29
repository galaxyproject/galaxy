import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import { saveInvocationBCOToDatabase } from "@/components/Workflow/Invocation/Export/Plugins/BioComputeObject/service";

import InvocationExportWizard from "./InvocationExportWizard.vue";
import ExportRemoteSourceSelector from "@/components/Common/ExportRemoteSourceSelector.vue";

vi.mock("@/components/Workflow/Invocation/Export/Plugins/BioComputeObject/service", () => ({
    saveInvocationBCOToDatabase: vi.fn(),
}));

const INVOCATION_ID = "fake-invocation-id";

const WRITABLE_FILE_SOURCE: BrowsableFilesSourcePlugin = {
    id: "test-posix-source",
    type: "posix",
    uri_root: "gxfiles://test-posix-source",
    label: "Test Posix Source",
    doc: "Writable test source",
    writable: true,
    browsable: true,
    supports: { pagination: false, search: false, sorting: false, recursive: true },
};

const { server, http } = useServerMock();

async function mountWizard() {
    const global = getLocalVue();
    const wrapper = mount(InvocationExportWizard as object, {
        props: { invocationId: INVOCATION_ID },
        global: {
            ...global,
            stubs: {
                ...global.stubs,
                ExistingInvocationExportProgressCard: defineComponent({
                    methods: { updateExistingExportProgress: vi.fn() },
                    render: () => null,
                }),
            },
        },
    });
    await flushPromises();
    return wrapper;
}

async function goNext(wrapper: VueWrapper) {
    await wrapper.get(".go-next-btn").trigger("click");
    await flushPromises();
}

describe("InvocationExportWizard.vue", () => {
    let writeStoreBody: Record<string, unknown> | undefined;

    beforeEach(() => {
        writeStoreBody = undefined;
        vi.mocked(saveInvocationBCOToDatabase).mockClear();
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json([WRITABLE_FILE_SOURCE]);
            }),
            http.post("/api/invocations/{invocation_id}/write_store", async ({ request, response }) => {
                writeStoreBody = (await request.json()) as Record<string, unknown>;
                return response(200).json({ id: "task-id", ignored: false });
            }),
        );
    });

    it("sends the BCODB fields typed in the GFormInput fields", async () => {
        const wrapper = await mountWizard();
        await wrapper.get('[data-export-format="bco.json"]').trigger("click");
        await goNext(wrapper);
        await wrapper.get('[data-invocation-export-destination="bco-database"]').trigger("click");
        await goNext(wrapper);

        const serverUrl = wrapper.get("input#bcodb-server");
        const table = wrapper.get("input#bcodb-table");
        const owner = wrapper.get("input#bcodb-owner");
        const authorization = wrapper.get("input#bcodb-authorization");
        for (const input of [serverUrl, table, owner, authorization]) {
            expect(input.classes()).toContain("g-form-input");
            expect(input.attributes("required")).toBeDefined();
            expect(input.attributes("autocomplete")).toBe("off");
        }
        expect(authorization.attributes("type")).toBe("password");
        expect((serverUrl.element as HTMLInputElement).value).toBe("https://biocomputeobject.org");
        expect(wrapper.get(".go-next-btn").attributes("disabled")).toBeDefined();

        await owner.setValue("owner-group");
        await authorization.setValue("secret-key");
        expect(wrapper.get(".go-next-btn").attributes("disabled")).toBeUndefined();
        await goNext(wrapper);
        await goNext(wrapper);

        expect(saveInvocationBCOToDatabase).toHaveBeenCalledWith(INVOCATION_ID, {
            serverBaseUrl: "https://biocomputeobject.org",
            table: "GALXY",
            ownerGroup: "owner-group",
            authorization: "secret-key",
        });
    });

    it("writes the export to the remote source with the typed file name", async () => {
        const wrapper = await mountWizard();
        await goNext(wrapper);
        await wrapper.get('[data-invocation-export-destination="remote-source"]').trigger("click");
        await goNext(wrapper);
        wrapper
            .findComponent(ExportRemoteSourceSelector)
            .vm.$emit("update:directory", "gxfiles://test-posix-source/dir");
        await flushPromises();
        await goNext(wrapper);

        const fileNameInput = wrapper.get("input#exported-file-name");
        expect(fileNameInput.classes()).toContain("g-form-input");
        expect(fileNameInput.attributes("required")).toBeDefined();
        expect(wrapper.get(".go-next-btn").attributes("disabled")).toBeDefined();

        await fileNameInput.setValue("my-export");
        await goNext(wrapper);

        expect(writeStoreBody?.target_uri).toBe("gxfiles://test-posix-source/dir/my-export.rocrate.zip");
    });
});
