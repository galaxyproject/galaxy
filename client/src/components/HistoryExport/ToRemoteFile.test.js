import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ToRemoteFile from "./ToRemoteFile.vue";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import flushPromises from "flush-promises";
import { waitOnJob } from "components/JobStates/wait";

const localVue = getLocalVue();
const TEST_HISTORY_ID = "hist1235";
const TEST_JOB_ID = "job123789";
const TEST_EXPORTS_URL = `/api/histories/${TEST_HISTORY_ID}/exports`;

jest.mock("components/JobStates/wait");

describe("ToRemoteFile.vue", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = shallowMount(ToRemoteFile, {
            propsData: {
                historyId: TEST_HISTORY_ID,
            },
            localVue,
        });
    });

    it("should issue export PUT request on export", async () => {
        let request;
        axiosMock.onPut(TEST_EXPORTS_URL).reply((request_) => {
            request = request_;
            return [200, { job_id: TEST_JOB_ID }];
        });
        waitOnJob.mockReturnValue(
            new Promise((then) => {
                then({ state: "ok" });
            })
        );
        wrapper.vm.doExport("gxfiles://", "export.tar.gz");
        await flushPromises();
        const putData = JSON.parse(request.data);
        expect(putData.directory_uri).toEqual("gxfiles://");
        expect(putData.file_name).toEqual("export.tar.gz");
        expect(wrapper.find("b-alert-stub").attributes("variant")).toEqual("success");
    });

    afterEach(() => {
        axiosMock.restore();
    });
});
