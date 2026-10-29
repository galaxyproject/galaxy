import { getLocalVue } from "@tests/vitest/helpers";
import { type DOMWrapper, flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import TrsIdImport from "./TrsIdImport.vue";
import TrsServerSelection from "@/components/Workflow/Import/TrsServerSelection.vue";

const { getTrsTool } = vi.hoisted(() => ({ getTrsTool: vi.fn() }));

vi.mock("@/components/Workflow/services", () => ({
    Services: vi.fn().mockImplementation(function () {
        return { getTrsTool };
    }),
}));

// setValue also fires change, which applies the value at once; typing only fires input
async function type(input: Omit<DOMWrapper<Element>, "exists">, value: string) {
    (input.element as HTMLInputElement).value = value;
    await input.trigger("input");
}

const TRS_SELECTION = { id: "dockstore", label: "Dockstore", link_url: "https://dockstore.org", doc: "" };

async function mountTrsIdImport(props = {}) {
    const wrapper = mount(TrsIdImport as object, {
        props,
        global: { ...getLocalVue(), stubs: { TrsServerSelection: true, TrsTool: true } },
    });
    wrapper.findComponent(TrsServerSelection).vm.$emit("onTrsSelection", TRS_SELECTION);
    await flushPromises();
    return wrapper;
}

describe("TrsIdImport", () => {
    beforeEach(() => {
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        getTrsTool.mockReset();
        getTrsTool.mockResolvedValue({ id: "#workflow/example", name: "example", versions: [] });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("renders the TRS ID field as a GFormInput", async () => {
        const wrapper = await mountTrsIdImport();
        const input = wrapper.get("input#trs-id-input");
        expect(input.classes()).toContain("g-form-input");
    });

    it("looks the tool up once, 500ms after the last keystroke", async () => {
        const wrapper = await mountTrsIdImport();
        const input = wrapper.get("input#trs-id-input");

        await type(input, "#workflow/exa");
        vi.advanceTimersByTime(300);
        await type(input, " #workflow/example ");
        vi.advanceTimersByTime(499);
        await flushPromises();
        expect(getTrsTool).not.toHaveBeenCalled();

        vi.advanceTimersByTime(1);
        await flushPromises();
        expect(getTrsTool).toHaveBeenCalledOnce();
        expect(getTrsTool).toHaveBeenCalledWith("dockstore", "#workflow/example");
    });

    it("looks the tool up at once when the field changes", async () => {
        const wrapper = await mountTrsIdImport();
        await wrapper.get("input#trs-id-input").setValue("#workflow/example");
        await flushPromises();
        expect(getTrsTool).toHaveBeenCalledOnce();
        expect(getTrsTool).toHaveBeenCalledWith("dockstore", "#workflow/example");

        vi.advanceTimersByTime(500);
        await flushPromises();
        expect(getTrsTool).toHaveBeenCalledOnce();
    });

    it("looks up the TRS ID from the route without waiting", async () => {
        const wrapper = await mountTrsIdImport({ queryTrsId: "#workflow/from-query" });
        expect((wrapper.get("input#trs-id-input").element as HTMLInputElement).value).toBe("#workflow/from-query");
        expect(getTrsTool).toHaveBeenCalledWith("dockstore", "#workflow/from-query");
    });
});
