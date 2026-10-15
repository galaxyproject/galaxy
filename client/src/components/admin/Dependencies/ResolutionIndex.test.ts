import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getToolboxDependencies, installDependencies } from "../AdminServices";

import ResolutionIndex from "./ResolutionIndex.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";

vi.mock("../AdminServices", () => ({
    getToolboxDependencies: vi.fn(),
    installDependencies: vi.fn(),
    uninstallDependencies: vi.fn(),
}));

const globalConfig = getLocalVue();

const REQUIREMENTS = [
    { requirements: [{ name: "bwa", version: "0.7" }], status: [], tool_ids: ["bwa_tool"] },
    { requirements: [{ name: "samtools", version: "1.9" }], status: [], tool_ids: ["samtools_tool"] },
];

async function mountIndex(attachTo?: HTMLElement) {
    const wrapper = mount(ResolutionIndex as object, {
        attachTo,
        global: { ...globalConfig, stubs: { ...globalConfig.stubs, FontAwesomeIcon: true, ResolutionDetails: true } },
    });
    await flushPromises();
    return wrapper;
}

async function clickButton(wrapper: Awaited<ReturnType<typeof mountIndex>>, text: string) {
    await wrapper
        .findAll("button")
        .find((button) => button.text() === text)!
        .trigger("click");
}

describe("ResolutionIndex", () => {
    beforeEach(() => {
        vi.mocked(getToolboxDependencies).mockReset().mockResolvedValue(REQUIREMENTS);
        vi.mocked(installDependencies).mockReset().mockResolvedValue([]);
    });

    it("reloads with the picked resolver type and without it for *any*", async () => {
        const wrapper = await mountIndex();
        const select = wrapper.findAllComponents(GSelect)[0]!;
        expect(select.attributes("id")).toBe("manage-resolver-type");
        expect((select.element as HTMLSelectElement).selectedOptions[0]!.text).toBe("*any*");

        await select.setValue("conda");
        await flushPromises();
        expect(getToolboxDependencies).toHaveBeenLastCalledWith({ resolver_type: "conda" });

        (select.element as HTMLSelectElement).selectedIndex = 0;
        await select.trigger("change");
        await flushPromises();
        expect(getToolboxDependencies).toHaveBeenLastCalledWith({});
    });

    it("installs the requirements ticked through the select-all box", async () => {
        const wrapper = await mountIndex();
        const selectAll = wrapper.find('#g-table-requirements-table thead input[type="checkbox"]');
        expect(selectAll.attributes("aria-label")).toBe("Select all requirements");

        await selectAll.setValue(true);
        const rows = wrapper.findAll('#g-table-requirements-table tbody input[type="checkbox"]');
        expect(rows.map((row) => (row.element as HTMLInputElement).checked)).toEqual([true, true]);
        expect(rows[0]!.attributes("aria-label")).toBe("Select bwa");

        await clickButton(wrapper, "Install");
        expect(installDependencies).toHaveBeenCalledWith(["bwa_tool", "samtools_tool"]);
    });

    it("names each tool row once the tools are expanded", async () => {
        vi.mocked(getToolboxDependencies).mockResolvedValue([
            { ...REQUIREMENTS[0], tool_ids: ["bwa_tool", "bwa_mem_tool"] },
            REQUIREMENTS[1],
        ]);
        const wrapper = await mountIndex();

        await clickButton(wrapper, "Expand Tools");
        const rows = wrapper.findAll('#g-table-requirements-table tbody input[type="checkbox"]');
        expect(rows.map((row) => row.attributes("aria-label"))).toEqual([
            "Select bwa (bwa_tool)",
            "Select bwa (bwa_mem_tool)",
            "Select samtools (samtools_tool)",
        ]);
    });

    it("installs only the ticked requirement", async () => {
        const wrapper = await mountIndex();
        await wrapper.find('#g-table-requirements-table tbody input[type="checkbox"]').setValue(true);

        await clickButton(wrapper, "Install");
        expect(installDependencies).toHaveBeenCalledWith(["bwa_tool"]);
    });

    it("ticks a row without opening its details", async () => {
        // Attached, so the click runs the checkbox activation and fires change
        const wrapper = await mountIndex(document.body);
        const row = wrapper.find('#g-table-requirements-table tbody input[type="checkbox"]');
        await row.trigger("click");
        expect((row.element as HTMLInputElement).checked).toBe(true);
        expect(wrapper.find(".g-table-details-row").exists()).toBe(false);

        await wrapper.find("#g-table-requirements-table tbody td:nth-child(2)").trigger("click");
        expect(wrapper.find(".g-table-details-row").exists()).toBe(true);
        wrapper.unmount();
    });

    it("names a row without requirement names after its tools", async () => {
        vi.mocked(getToolboxDependencies).mockResolvedValue([
            { requirements: [], status: [], tool_ids: ["secret_tool"] },
        ]);
        const wrapper = await mountIndex();
        const label = () =>
            wrapper.find('#g-table-requirements-table tbody input[type="checkbox"]').attributes("aria-label");
        expect(label()).toBe("Select secret_tool");

        await clickButton(wrapper, "Expand Tools");
        expect(label()).toBe("Select secret_tool");
    });

    describe("header select-all state", () => {
        const headerBox = (wrapper: Awaited<ReturnType<typeof mountIndex>>) =>
            wrapper.find('#g-table-requirements-table thead input[type="checkbox"]').element as HTMLInputElement;
        const rowBoxes = (wrapper: Awaited<ReturnType<typeof mountIndex>>) =>
            wrapper.findAll('#g-table-requirements-table tbody input[type="checkbox"]');

        it("checks the header once both rows are ticked", async () => {
            const wrapper = await mountIndex();
            const rows = rowBoxes(wrapper);

            await rows[0]!.setValue(true);
            expect(headerBox(wrapper).checked).toBe(false);

            await rows[1]!.setValue(true);
            expect(headerBox(wrapper).checked).toBe(true);
        });

        it("unchecks the header when a row is unticked again", async () => {
            const wrapper = await mountIndex();
            const rows = rowBoxes(wrapper);

            await rows[0]!.setValue(true);
            await rows[1]!.setValue(true);
            await rows[0]!.setValue(false);
            expect(headerBox(wrapper).checked).toBe(false);
        });
    });
});
