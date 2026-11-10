import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import TrsSearch from "./TrsSearch.vue";

vi.mock("axios");

const TRS_SERVER = { id: "dockstore", label: "Dockstore", link_url: "https://dockstore.org", doc: "" };

describe("TrsSearch", () => {
    it("encodes the query and server in the search URL", async () => {
        vi.mocked(axios.get).mockResolvedValue({ data: [] });
        const wrapper = mount(TrsSearch as object, {
            global: { ...getLocalVue(), stubs: { TrsServerSelection: true } },
        });
        wrapper.findComponent({ name: "TrsServerSelection" }).vm.$emit("onTrsSelection", TRS_SERVER);
        await flushPromises();

        const input = wrapper.find("#trs-search-query");
        await input.setValue("rna-seq & qc #1 + more");
        await input.trigger("change");
        await flushPromises();

        expect(axios.get).toHaveBeenCalledTimes(1);
        const url = new URL(vi.mocked(axios.get).mock.calls[0]![0], "http://localhost");
        expect(url.pathname).toBe("/api/trs_search");
        expect(Object.fromEntries(url.searchParams)).toEqual({
            query: "rna-seq & qc #1 + more",
            trs_server: "dockstore",
        });
    });
});
