import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
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

    it("should render a form with export disable because inputs empty", async () => {
        expect(wrapper.find(".export-button").exists()).toBeTruthy();
        expect(wrapper.find(".export-button").attributes("disabled")).toBeTruthy();
        expect(wrapper.vm.canExport).toBeFalsy();
    });

    it("should allow export when name and directory available", async () => {
        await wrapper.setData({
            name: "export.tar.gz",
            directory: "gxfiles://",
        });
        expect(wrapper.vm.directory).toEqual("gxfiles://");
        expect(wrapper.vm.name).toEqual("export.tar.gz");
        expect(wrapper.vm.canExport).toBeTruthy();
    });

    it("should issue export PUT request on export", async () => {
        await wrapper.setData({
            name: "export.tar.gz",
            directory: "gxfiles://",
        });
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
        wrapper.vm.doExport();
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
