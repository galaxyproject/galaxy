import JobOutputs from "./JobOutputs";
import { shallowMount } from "@vue/test-utils";

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

    it("displays a table with 15 visible job outputs (paginated)", async () => {
        const propsData = {
            jobOutputs: {
                a: [{ label: "a", value: { id: "1", src: "hda" } }],
                b: [{ label: "b", value: { id: "2", src: "hda" } }],
                c: [{ label: "c", value: { id: "3", src: "hda" } }],
                d: [{ label: "d", value: { id: "4", src: "hda" } }],
                e: [{ label: "e", value: { id: "5", src: "hda" } }],
                f: [{ label: "f", value: { id: "6", src: "hda" } }],
                g: [{ label: "g", value: { id: "7", src: "hda" } }],
                h: [{ label: "h", value: { id: "8", src: "hda" } }],
                i: [{ label: "i", value: { id: "9", src: "hda" } }],
                j: [{ label: "j", value: { id: "10", src: "hda" } }],
                k: [{ label: "k", value: { id: "11", src: "hda" } }],
                l: [{ label: "l", value: { id: "12", src: "hda" } }],
                m: [{ label: "m", value: { id: "13", src: "hda" } }],
                n: [{ label: "n", value: { id: "14", src: "hda" } }],
                o: [{ label: "o", value: { id: "15", src: "hda" } }],
            },
            title: "Job Outputs",
            paginate: true,
        };
        wrapper = shallowMount(JobOutputs, {
            propsData,
        });
        // ---- Before all remaining outputs are paginated: ----
        // heading should exist and include count (due to pagination)
        expect(wrapper.find("h3").text()).toContain("(showing 10 of " + Object.keys(propsData.jobOutputs).length + ")");
        jobOutputsTable = wrapper.find("#job-outputs");
        // table should exist
        expect(jobOutputsTable).toBeTruthy();
        let rows = jobOutputsTable.findAll("tr");
        // should initially contain a header and 11 rows (10 items + a button)
        expect(rows.length).toBe(12);
        // ---- Click button, remaining 5 outputs should be displayed ----
        expect(wrapper.find("#paginate-btn").exists()).toEqual(true);
        await wrapper.find("#paginate-btn").trigger("click");
        jobOutputsTable = wrapper.find("#job-outputs");
        rows = jobOutputsTable.findAll("tr");
        // should now contain a header and 15 rows (all 15 items and no button)
        expect(rows.length).toBe(16);
        expect(wrapper.find("#paginate-btn").exists()).toEqual(false);
        // heading reverts to original value of title (as all ouputs are paginated)
        expect(wrapper.find("h3").text()).toBe("Job Outputs");
    });
});
