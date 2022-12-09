import { mount } from "@vue/test-utils";
import { getLocalVue, wait } from "tests/jest/helpers";
import HistoryImport from "./HistoryImport.vue";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import flushPromises from "flush-promises";
import { waitOnJob } from "components/JobStates/wait";

const localVue = getLocalVue();
const TEST_JOB_ID = "job123789";
const TEST_HISTORY_URI = "/api/histories";
const TEST_SOURCE_URL = "http://galaxy.example/import";
const TEST_PLUGINS_URL = "/api/remote_files/plugins";

jest.mock("components/JobStates/wait");

describe("HistoryImport.vue", () => {
    let axiosMock;
    let wrapper;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(TEST_PLUGINS_URL).reply(200, [{ id: "foo", writable: false }]);
        wrapper = mount(HistoryImport, {
            propsData: {},
            localVue,
        });
        await flushPromises();
    });

    it("should render a form with submit disabled because inputs empty", async () => {
        expect(wrapper.find(".import-button").exists()).toBeTruthy();
        expect(wrapper.find(".import-button").attributes("disabled")).toBeTruthy();
        expect(wrapper.vm.importReady).toBeFalsy();
    });

    it("should allow import when URL available", async () => {
        await wrapper.setData({
            sourceURL: TEST_SOURCE_URL,
        });
        expect(wrapper.vm.importReady).toBeTruthy();
    });

    it("should require an URI if that is the import type", async () => {
        await wrapper.setData({
            sourceURL: TEST_SOURCE_URL,
            importType: "sourceRemoteFilesUri",
        });
        expect(wrapper.vm.importReady).toBeFalsy();
    });

    it("should post to create a new history and wait on job when submitted", async () => {
        await wrapper.setData({
            sourceURL: TEST_SOURCE_URL,
        });
        let formData;
        axiosMock.onPost(TEST_HISTORY_URI).reply((request) => {
            formData = request.data;
            return [200, { job_id: TEST_JOB_ID }];
        });
        let then;
        waitOnJob.mockReturnValue(
            new Promise((then_) => {
                then = then_;
            })
        );
        wrapper.vm.submit();
        await flushPromises();
        expect(formData.get("archive_source")).toBe(TEST_SOURCE_URL);
        expect(wrapper.vm.waitingOnJob).toBeTruthy();

        // complete job and make sure waitingOnJob is false and complete is true
        then({ state: "ok" });
        await flushPromises();
        expect(wrapper.vm.waitingOnJob).toBeFalsy();
        expect(wrapper.vm.complete).toBeTruthy();
    });

    it("warns about shared history imports", async () => {
        const input = wrapper.find("input[type=url]");
        await input.setValue("https://usegalaxy.org/u/some_user/h/exported_history");

        await wait(210);

        const alert = wrapper.find(".alert");
        expect(alert.classes()).toContain("alert-warning");
        expect(alert.text()).toContain(
            "It looks like you are trying to import a published history from another galaxy instance"
        );

        // Link to the GTN
        const link = alert.find("a");
        expect(link.text()).toContain("GTN");
    });

    afterEach(() => {
        axiosMock.restore();
    });
});
