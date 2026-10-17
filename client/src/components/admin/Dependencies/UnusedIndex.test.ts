import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { deletedUnusedPaths, getDependencyUnusedPaths } from "../AdminServices";

import UnusedIndex from "./UnusedIndex.vue";

vi.mock("../AdminServices", () => ({
    deletedUnusedPaths: vi.fn(),
    getDependencyUnusedPaths: vi.fn(),
}));

const globalConfig = getLocalVue();

describe("UnusedIndex", () => {
    it("deletes only the ticked environments", async () => {
        vi.mocked(getDependencyUnusedPaths).mockResolvedValue(["/envs/a", "/envs/b"]);
        vi.mocked(deletedUnusedPaths).mockResolvedValue(undefined);
        const wrapper = mount(UnusedIndex as object, { global: globalConfig });
        await flushPromises();

        const rows = wrapper.findAll('tbody input[type="checkbox"]');
        expect(rows[1]!.attributes("aria-label")).toBe("Select /envs/b");

        await rows[1]!.setValue(true);
        await wrapper.find("button").trigger("click");

        expect(deletedUnusedPaths).toHaveBeenCalledWith(["/envs/b"]);
    });
});
