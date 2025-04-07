import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue, wait } from "tests/jest/helpers";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { waitOnJob } from "@/components/JobStates/wait";

import HistoryImport from "./HistoryImport.vue";

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const TEST_JOB_ID = "job123789";
const TEST_SOURCE_URL = "http://galaxy.example/import";

jest.mock("components/JobStates/wait");

const { server, http } = useServerMock();

describe("HistoryImport.vue", () => {
    let wrapper;

    beforeEach(async () => {
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json([
                    {
                        id: "_ftp",
                        type: "gxftp",
                        uri_root: "gxftp://",
                        label: "FTP Directory",
                        doc: "Galaxy User's FTP Directory",
                        writable: false,
                        browsable: true,
                        supports: {
                            pagination: false,
                            search: false,
                            sorting: false,
                        },
                    },
                ]);
            })
        );

        wrapper = mount(HistoryImport, {
            propsData: {},
            localVue,
            router,
        });
        await flushPromises();
    });

    it("should render a form with submit disabled because inputs empty", async () => {
        expect(wrapper.find(".import-button").exists()).toBeTruthy();
        expect(wrapper.find(".import-button").attributes("data-disabled")).toBeTruthy();
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

        server.use(
            http.post("/api/histories", async ({ response, request }) => {
                formData = await request.formData();
                return response(200).json({ job_id: TEST_JOB_ID });
            })
        );

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
});
