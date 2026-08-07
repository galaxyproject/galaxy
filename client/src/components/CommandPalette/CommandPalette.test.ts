import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { useCommandPalette } from "@/composables/useCommandPalette";

import MountTarget from "./CommandPalette.vue";

vi.mock("@/composables/config");

const localVue = getLocalVue(true);
localVue.use(VueRouter);

const { server, http } = useServerMock();

const DEBOUNCE_WAIT = 250;

async function settle() {
    await new Promise((resolve) => setTimeout(resolve, DEBOUNCE_WAIT));
    await flushPromises();
}

describe("CommandPalette", () => {
    let wrapper: Wrapper<Vue>;
    let router: VueRouter;

    beforeEach(async () => {
        server.use(
            http.get("/api/unprivileged_tools", ({ response }) => {
                return response(200).json([]);
            }),
        );
        router = new VueRouter({ mode: "abstract" });
        wrapper = mount(MountTarget as object, {
            localVue,
            router,
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: true }),
        });
        useCommandPalette().openPalette();
        await settle();
    });

    afterEach(() => {
        useCommandPalette().closePalette();
        wrapper?.destroy();
    });

    async function type(query: string) {
        const input = wrapper.find("[data-description='palette input']");
        (input.element as HTMLInputElement).value = query;
        await input.trigger("input");
        await settle();
    }

    it("shows actions and navigation sections for an empty query", () => {
        const text = wrapper.text();
        expect(text).toContain("Actions");
        expect(text).toContain("Navigation");
        expect(text).toContain("Upload data");
    });

    it("filters results while typing", async () => {
        await type("workflows");
        const options = wrapper.findAll("[role='option']");
        expect(options.length).toBeGreaterThan(0);
        expect(options.at(0).text()).toContain("Workflows");
    });

    it("scopes to actions with the '>' prefix", async () => {
        await type("> ");
        const text = wrapper.text();
        expect(text).toContain("Upload data");
        expect(text).not.toContain("Navigation");
    });

    it("shows a hint for reserved entity prefixes", async () => {
        await type("w: rna");
        expect(wrapper.find("[data-description='palette reserved hint']").text()).toContain("workflow");
    });

    it("navigates to the selected item on enter and closes", async () => {
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);
        await type("workflows");
        await wrapper.find("[data-description='palette input']").trigger("keydown", { key: "Enter" });
        expect(push).toHaveBeenCalledWith("/workflows/list");
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("opens in a new tab on ctrl/cmd+enter", async () => {
        const open = vi.spyOn(window, "open").mockImplementation(() => null);
        const push = vi.spyOn(router, "push");
        await type("workflows");
        await wrapper.find("[data-description='palette input']").trigger("keydown", { key: "Enter", ctrlKey: true });
        expect(open).toHaveBeenCalledWith(router.resolve("/workflows/list").href, "_blank", "noopener");
        expect(push).not.toHaveBeenCalled();
    });

    it("closes on escape", async () => {
        await wrapper.find("[data-description='palette input']").trigger("keydown", { key: "Escape" });
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });
});
