import { getLocalVue } from "@tests/vitest/helpers";
import { type DOMWrapper, flushPromises, mount } from "@vue/test-utils";
import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TrsSearch from "./TrsSearch.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";

// setValue also fires change, which applies the value at once; typing only fires input
async function type(input: Omit<DOMWrapper<Element>, "exists">, value: string) {
    (input.element as HTMLInputElement).value = value;
    await input.trigger("input");
}

const TRS_SELECTION = { id: "dockstore", label: "Dockstore", link_url: "https://dockstore.org", doc: "" };
const SEARCH_RESULT = { id: "#workflow/example", name: "example", description: "", organization: "org", versions: [] };

async function mountTrsSearch() {
    const wrapper = mount(TrsSearch as object, {
        global: { ...getLocalVue(), stubs: { TrsServerSelection: true, TrsTool: true, HelpText: true } },
    });
    wrapper.findComponent(TrsServerSelection).vm.$emit("onTrsSelection", TRS_SELECTION);
    await flushPromises();
    return wrapper;
}

describe("TrsSearch", () => {
    let axiosGet: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        axiosGet = vi.spyOn(axios, "get").mockResolvedValue({ data: [SEARCH_RESULT] });
    });

    afterEach(() => {
        axiosGet.mockRestore();
        vi.useRealTimers();
    });

    it("renders the search field as a GFormInput", async () => {
        const wrapper = await mountTrsSearch();
        const input = wrapper.get("input#trs-search-query");
        expect(input.classes()).toContain("g-form-input");
        expect(input.attributes("placeholder")).toBe("search query");
    });

    it("searches once, 500ms after the last keystroke", async () => {
        const wrapper = await mountTrsSearch();
        const input = wrapper.get("input#trs-search-query");

        await type(input, "exa");
        vi.advanceTimersByTime(300);
        await type(input, "example");
        vi.advanceTimersByTime(499);
        await flushPromises();
        expect(axiosGet).not.toHaveBeenCalled();

        vi.advanceTimersByTime(1);
        await flushPromises();
        expect(axiosGet).toHaveBeenCalledOnce();
        expect(axiosGet.mock.calls[0]![0]).toContain("query=example&trs_server=dockstore");
        expect(wrapper.text()).toContain("example");
    });

    it("searches at once when the field changes", async () => {
        const wrapper = await mountTrsSearch();
        await wrapper.get("input#trs-search-query").setValue("example");
        await flushPromises();
        expect(axiosGet).toHaveBeenCalledOnce();

        vi.advanceTimersByTime(500);
        await flushPromises();
        expect(axiosGet).toHaveBeenCalledOnce();
    });

    it.each([
        [
            "the clear button",
            (wrapper: ReturnType<typeof mount>) => wrapper.get("button[title='clear search']").trigger("click"),
        ],
        [
            "Escape",
            (wrapper: ReturnType<typeof mount>) =>
                wrapper.get("input#trs-search-query").trigger("keyup", { key: "Escape" }),
        ],
    ])("clears the query and the results right away with %s", async (_, clear) => {
        const wrapper = await mountTrsSearch();
        const input = wrapper.get("input#trs-search-query");
        await type(input, "example");
        vi.advanceTimersByTime(500);
        await flushPromises();
        expect(wrapper.find("table").exists()).toBe(true);

        await clear(wrapper);
        await flushPromises();
        expect((input.element as HTMLInputElement).value).toBe("");
        expect(wrapper.find("table").exists()).toBe(false);
        expect(wrapper.text()).toContain("Enter search query to begin search.");
    });
});
