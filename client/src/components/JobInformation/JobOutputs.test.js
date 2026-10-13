import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import JobOutputs from "./JobOutputs.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

vi.mock("components/providers/DatasetCollectionProvider");

enableAutoUnmount(afterEach);

function mountJobOutputs(props, stubs = {}) {
    return shallowMount(JobOutputs, {
        props,
        global: { renderStubDefaultSlot: true, stubs },
    });
}

describe("JobInformation/JobOutputs.vue", () => {
    it("displays a titled table with one collection output", () => {
        const props = {
            jobOutputs: { list_output: [{ label: "List Output", value: { id: "1", src: "hdca" } }] },
            title: "my cool title",
        };
        const wrapper = mountJobOutputs(props);
        const jobOutputsTable = wrapper.get("#job-outputs");
        expect(wrapper.get("heading-stub").text()).toBe("my cool title");
        expect(jobOutputsTable).toBeTruthy();
        const rows = jobOutputsTable.findAll("tr");
        expect(rows.length).toBe(2);
    });

    it("shows dataset and collection outputs while excluding hidden outputs", () => {
        const props = {
            jobOutputs: {
                list_output: [{ label: "List Output", value: { id: "1", src: "hdca" } }],
                another_outputs: [{ label: "Other Output", value: { id: "2", src: "hda" } }],
                __hidden_output: [{ label: "hidden Output", value: { id: "2", src: "hda" } }],
            },
        };
        const wrapper = mountJobOutputs(props);
        expect(wrapper.find("heading-stub").exists()).toBeFalsy();
        const jobOutputsTable = wrapper.get("#job-outputs");
        expect(jobOutputsTable).toBeTruthy();
        const rows = jobOutputsTable.findAll("tr");
        expect(rows.length).toBe(3);
    });

    it("displays a table with 15 visible job outputs (paginated)", async () => {
        const props = {
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
        // Real GButton so the click runs through its handler.
        const wrapper = mountJobOutputs(props, { GButton });
        expect(wrapper.get("heading-stub").text()).toContain(
            "(showing 10 of " + Object.keys(props.jobOutputs).length + ")",
        );
        const jobOutputsTable = wrapper.get("#job-outputs");
        expect(jobOutputsTable).toBeTruthy();
        const initialRows = jobOutputsTable.findAll("tr");
        expect(initialRows.length).toBe(12);
        expect(wrapper.find("#paginate-btn").exists()).toEqual(true);
        await wrapper.get("#paginate-btn").trigger("click");
        const expandedRows = wrapper.get("#job-outputs").findAll("tr");
        expect(expandedRows.length).toBe(16);
        expect(wrapper.find("#paginate-btn").exists()).toEqual(false);
        expect(wrapper.get("heading-stub").text()).toBe("Job Outputs");
    });
});
