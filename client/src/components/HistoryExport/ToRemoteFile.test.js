import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { waitOnJob } from "@/components/JobStates/wait";

import ToRemoteFile from "./ToRemoteFile.vue";
import ExportForm from "@/components/Common/ExportForm.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();
enableAutoUnmount(afterEach);

const TEST_HISTORY_ID = "hist1235";
const TEST_JOB_ID = "job123789";

vi.mock("@/components/JobStates/wait", () => ({
    waitOnJob: vi.fn(),
}));

describe("ToRemoteFile", () => {
    it("exports the requested remote archive and shows success after its job completes", async () => {
        const exportRequest = vi.fn();
        server.use(
            http.untyped.put(`/api/histories/${TEST_HISTORY_ID}/exports`, async ({ request }) => {
                exportRequest(await request.json());
                return HttpResponse.json({ job_id: TEST_JOB_ID });
            }),
        );
        vi.mocked(waitOnJob).mockResolvedValue({ state: "ok" });
        const wrapper = shallowMount(ToRemoteFile, {
            props: { historyId: TEST_HISTORY_ID },
            global: localVue,
        });

        wrapper.findComponent(ExportForm).vm.$emit("export", "gxfiles://", "export.tar.gz");
        await flushPromises();

        expect(exportRequest).toHaveBeenCalledExactlyOnceWith({
            directory_uri: "gxfiles://",
            file_name: "export.tar.gz",
        });
        expect(waitOnJob).toHaveBeenCalledExactlyOnceWith(TEST_JOB_ID);
        expect(wrapper.find("g-alert-stub").attributes("variant")).toBe("success");
    });
});
