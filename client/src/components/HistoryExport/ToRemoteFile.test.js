import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { waitOnJob } from "@/components/JobStates/wait";

import ToRemoteFile from "./ToRemoteFile.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const TEST_HISTORY_ID = "hist1235";
const TEST_JOB_ID = "job123789";
const TEST_EXPORTS_URL = `/api/histories/${TEST_HISTORY_ID}/exports`;

vi.mock("@/components/JobStates/wait", () => ({
    waitOnJob: vi.fn(),
}));

describe("ToRemoteFile.vue", () => {
    let wrapper;
    let lastPutRequest = null;

    beforeEach(async () => {
        lastPutRequest = null;
        wrapper = shallowMount(ToRemoteFile, {
            propsData: {
                historyId: TEST_HISTORY_ID,
            },
            localVue,
        });
    });

    it("should issue export PUT request on export", async () => {
        server.use(
            http.untyped.put(TEST_EXPORTS_URL, async ({ request }) => {
                lastPutRequest = await request.json();
                return HttpResponse.json({ job_id: TEST_JOB_ID });
            }),
        );
        waitOnJob.mockReturnValue(
            new Promise((then) => {
                then({ state: "ok" });
            }),
        );
        wrapper.vm.doExport("gxfiles://", "export.tar.gz");
        await flushPromises();
        expect(lastPutRequest.directory_uri).toEqual("gxfiles://");
        expect(lastPutRequest.file_name).toEqual("export.tar.gz");
        expect(wrapper.find("b-alert-stub").attributes("variant")).toEqual("success");
    });
});
