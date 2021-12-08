import JobOutputs from "./JobOutputs";
import { shallowMount } from "@vue/test-utils";

jest.mock("components/providers/History/caching");
jest.mock("components/providers/DatasetCollectionProvider");

describe("JobInformation/JobOutputs.vue", () => {
    let wrapper;
    let jobOutputsTable;

    it("displays a table with job collection outputs", async () => {
        const propsData = {
            jobOutputs: { list_output: [{ label: "List Output", value: { id: "1", src: "hdca" } }] },
            title: "my cool title",
        };
        wrapper = shallowMount(JobOutputs, {
            propsData,
        });
        jobOutputsTable = wrapper.find("#job-outputs");
        // header should exist
        expect(wrapper.find("h3").text()).toBe("my cool title");
        // table should exist
        expect(jobOutputsTable).toBeTruthy();
        // title should be set
        const rows = jobOutputsTable.findAll("tr");
        // should contain 2 rows, header + 1 collection
        expect(rows.length).toBe(2);
    });

    it("displays a table with 2 job outputs", async () => {
        const propsData = {
            jobOutputs: {
                list_output: [{ label: "List Output", value: { id: "1", src: "hdca" } }],
                another_outputs: [{ label: "Other Output", value: { id: "2", src: "hda" } }],
                __hidden_output: [{ label: "hidden Output", value: { id: "2", src: "hda" } }],
            },
        };
        wrapper = shallowMount(JobOutputs, {
            propsData,
        });
        // no title
        expect(wrapper.find("h3").exists()).toBeFalsy();
        jobOutputsTable = wrapper.find("#job-outputs");
        // table should exist
        expect(jobOutputsTable).toBeTruthy();
        const rows = jobOutputsTable.findAll("tr");
        // should contain 2 rows, header + 1 collection + 1 hda
        expect(rows.length).toBe(3);
    });
});
