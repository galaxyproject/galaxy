import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getContainerResolutionToolbox, resolveContainersWithInstall } from "../AdminServices";

import ContainerIndex from "./ContainerIndex.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";

vi.mock("../AdminServices", () => ({
    getContainerResolutionToolbox: vi.fn(),
    resolveContainersWithInstall: vi.fn(),
}));

const globalConfig = getLocalVue();

const RESOLUTIONS = [
    { requirements: [], status: { dependency_type: null }, tool_id: "unresolved_tool" },
    { requirements: [], status: { dependency_type: "docker" }, tool_id: "resolved_tool" },
];

async function mountIndex(attachTo?: HTMLElement) {
    const wrapper = mount(ContainerIndex as object, {
        attachTo,
        global: {
            ...globalConfig,
            stubs: {
                ...globalConfig.stubs,
                ContainerDescription: true,
                ContainerResolutionDetails: true,
                ContainerResolver: true,
                FontAwesomeIcon: true,
                Requirements: true,
                StatusDisplay: true,
                ToolDisplay: true,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

function selectById(wrapper: Awaited<ReturnType<typeof mountIndex>>, id: string) {
    return wrapper.findAllComponents(GSelect).find((select) => select.attributes("id") === id)!;
}

describe("ContainerIndex", () => {
    beforeEach(() => {
        vi.mocked(getContainerResolutionToolbox).mockReset().mockResolvedValue(RESOLUTIONS);
        vi.mocked(resolveContainersWithInstall).mockReset().mockResolvedValue(RESOLUTIONS);
    });

    it("reloads with the picked container type and without it for *any*", async () => {
        const wrapper = await mountIndex();
        const select = selectById(wrapper, "manage-container-type");

        await select.setValue("docker");
        await flushPromises();
        expect(getContainerResolutionToolbox).toHaveBeenLastCalledWith({ container_type: "docker" });

        (select.element as HTMLSelectElement).selectedIndex = 0;
        await select.trigger("change");
        await flushPromises();
        expect(getContainerResolutionToolbox).toHaveBeenLastCalledWith({});
    });

    it("hides the type filters for unresolved containers and shows them again for *any*", async () => {
        const wrapper = await mountIndex();
        const filter = selectById(wrapper, "manage-filter-resolution");

        await filter.setValue("unresolved");
        expect(wrapper.find("#manage-filter-container-type").exists()).toBe(false);
        expect(wrapper.findAll('tbody input[type="checkbox"]')).toHaveLength(1);

        (filter.element as HTMLSelectElement).selectedIndex = 0;
        await filter.trigger("change");
        expect(wrapper.find("#manage-filter-container-type").exists()).toBe(true);
        expect(wrapper.findAll('tbody input[type="checkbox"]')).toHaveLength(2);
    });

    it("builds the containers of the ticked tools", async () => {
        const wrapper = await mountIndex();
        const row = wrapper.find('tbody input[type="checkbox"]');
        expect(row.attributes("aria-label")).toBe("Select unresolved_tool");

        await row.setValue(true);
        await wrapper
            .findAll("button")
            .find((button) => button.text() === "Attempt Build")!
            .trigger("click");

        expect(resolveContainersWithInstall).toHaveBeenCalledWith(["unresolved_tool"], {});
    });

    it("ticks a row without opening its details", async () => {
        // Attached, so the click runs the checkbox activation and fires change
        const wrapper = await mountIndex(document.body);
        const row = wrapper.find('tbody input[type="checkbox"]');
        await row.trigger("click");
        expect((row.element as HTMLInputElement).checked).toBe(true);
        expect(wrapper.find(".g-table-details-row").exists()).toBe(false);

        await wrapper.find("tbody td:nth-child(2)").trigger("click");
        expect(wrapper.find(".g-table-details-row").exists()).toBe(true);
        wrapper.unmount();
    });
});
