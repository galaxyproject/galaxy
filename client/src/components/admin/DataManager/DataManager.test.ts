import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import DataManager from "./DataManager.vue";

vi.mock("axios");

const ROUTES = [
    { path: "/datamanager/jobs/:id", name: "DataManagerJobs", component: { template: "<div />" } },
    { path: "/datamanager/table/:name", name: "DataManagerTable", component: { template: "<div />" } },
];

const RESPONSE = {
    dataManagers: [
        { id: "dm1", name: "Fetch genome", description: "Download a reference", toolUrl: "/tool_runner?id=dm1" },
        { id: "dm2", name: "Build index", toolUrl: "/tool_runner?id=dm2" },
    ],
    dataTables: [
        { name: "all_fasta", managed: true },
        { name: "bwa_indexes", managed: false },
    ],
    viewOnly: false,
    message: "",
    status: "",
};

async function mountDataManager() {
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.mocked(axios.get).mockResolvedValue({ data: RESPONSE });
    const wrapper = mount(DataManager as object, {
        props: { debouncePeriod: 0 },
        global: withPlugins(getLocalVue(), createTestRouter(ROUTES)),
    });
    await vi.waitFor(() => expect(axios.get).toHaveBeenCalled());
    await flushPromises();
    return wrapper;
}

function clearButton(wrapper: Awaited<ReturnType<typeof mountDataManager>>) {
    return wrapper.find(".input-group-append .g-button");
}

describe("DataManager", () => {
    it("clears the search with the Clear button", async () => {
        const wrapper = await mountDataManager();
        expect(clearButton(wrapper).text()).toBe("Clear (esc)");
        expect(clearButton(wrapper).attributes("aria-disabled")).toBe("true");

        await wrapper.find("input").setValue("fetch");
        expect(wrapper.find("#data-managers-card").text()).toContain("Fetch genome");
        expect(wrapper.find("#data-managers-card").text()).not.toContain("Build index");
        expect(clearButton(wrapper).attributes("aria-disabled")).toBeUndefined();

        await clearButton(wrapper).trigger("click");

        expect((wrapper.find("input").element as HTMLInputElement).value).toBe("");
        expect(wrapper.find("#data-managers-card").text()).toContain("Build index");
        expect(clearButton(wrapper).attributes("aria-disabled")).toBe("true");
    });
});
