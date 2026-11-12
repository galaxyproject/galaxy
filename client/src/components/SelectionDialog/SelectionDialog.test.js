import { emittedArg, getLocalVue, nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { useSelectItems } from "@/composables/useSelectItems";

import { SELECTION_STATES } from "./selectionTypes";

import DataDialogSearch from "./DataDialogSearch.vue";
import SelectionDialog from "./SelectionDialog.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GTable from "@/components/Common/GTable.vue";

// Translates only what a test asks for, so the other assertions see the source strings.
const translations = vi.hoisted(() => ({}));
vi.mock("@/utils/localization", async (importOriginal) => {
    const actual = await importOriginal();
    const localize = (text) => translations[text] ?? actual.localize(text);
    return { ...actual, default: localize, localize };
});

const mockOptions = {
    callback: () => {},
    modalShow: true,
};

describe("SelectionDialog.vue", () => {
    let wrapper;
    let localVue;

    beforeEach(() => {
        localVue = getLocalVue();
        wrapper = mount(SelectionDialog, {
            props: mockOptions,
            global: localVue,
        });
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeTruthy();
        expect(wrapper.findComponent(GTable).exists()).toBeFalsy();
        await wrapper.setProps({ optionsShow: true });
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBeFalsy();
        expect(wrapper.findComponent(GTable).exists()).toBeTruthy();
    });

    it("opens a folder without also selecting its row", async () => {
        const folder = { id: "folder", label: "Results", url: "gxfiles://results", isLeaf: false };
        await wrapper.setProps({ optionsShow: true, selectable: true, items: [folder] });
        const open = wrapper.get("button.selection-dialog-folder");
        expect(open.text()).toContain("Results");
        expect(open.find("a").exists()).toBe(false);
        await open.trigger("click");
        expect(wrapper.emitted("onOpen")).toEqual([[folder]]);
        expect(wrapper.emitted("onClick")).toBeUndefined();
    });

    afterEach(() => {
        Object.keys(translations).forEach((text) => delete translations[text]);
    });

    it("names the search and its clear button", () => {
        expect(wrapper.get("input[type='text']").attributes("aria-label")).toContain("search");
        expect(wrapper.get("button[aria-label='Clear search']").exists()).toBe(true);
    });

    it("loads header correctly", async () => {
        await nextTick();
        expect(wrapper.findComponent(DataDialogSearch).exists()).toBeTruthy();
    });

    it("hideModal called on click cancel", async () => {
        expect(wrapper.emitted("onCancel")).toBeFalsy();
        wrapper.find("[data-description='selection dialog cancel']").trigger("click");
        expect(wrapper.emitted("onCancel")).toBeTruthy();
    });

    it("names each row's selection checkbox after the row's label", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "file1", isLeaf: true },
                { id: "2", label: "file2", isLeaf: true },
            ],
        });

        const names = wrapper.findAll("tbody input[type='checkbox']").map((box) => box.attributes("aria-label"));
        expect(names).toEqual(["Select file1", "Select file2"]);
    });

    it("localizes the row selection checkbox name", async () => {
        translations["Select"] = "Auswählen";
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [{ id: "1", label: "file1", isLeaf: true }],
        });

        expect(wrapper.get("tbody input[type='checkbox']").attributes("aria-label")).toBe("Auswählen file1");
    });

    it("syncs row selection state from incoming items", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.SELECTED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED },
            ],
        });

        const selectAllCheckbox = wrapper.find("input[id^='g-table-select-all-']").element;
        expect(selectAllCheckbox.checked).toBe(false);
        expect(selectAllCheckbox.indeterminate).toBe(true);
    });

    it("shows select-all as checked when all incoming items are selected", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.SELECTED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.SELECTED },
            ],
        });

        const selectAllCheckbox = wrapper.find("input[id^='g-table-select-all-']").element;
        expect(selectAllCheckbox.checked).toBe(true);
        expect(selectAllCheckbox.indeterminate).toBe(false);
    });

    it("renders a MIXED row as an indeterminate checkbox", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "folder1", isLeaf: false, selectionState: SELECTION_STATES.MIXED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED },
            ],
        });

        const rowCheckbox = wrapper.find("tbody tr[aria-rowindex='1'] .g-table-select-column input").element;
        expect(rowCheckbox.checked).toBe(false);
        expect(rowCheckbox.indeterminate).toBe(true);
    });

    it("emits onClick for the row when its checkbox is toggled", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [
                { id: "1", label: "folder1", isLeaf: false, selectionState: SELECTION_STATES.MIXED },
                { id: "2", label: "file2", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED },
            ],
        });

        const rowCheckbox = wrapper.find("tbody tr[aria-rowindex='1'] .g-table-select-column input");
        await rowCheckbox.trigger("change");

        expect(wrapper.emitted("onClick")).toBeTruthy();
        expect(emittedArg(wrapper, "onClick").id).toBe("1");
    });

    it("emits onClick exactly once when a selectable row is clicked", async () => {
        await wrapper.setProps({
            optionsShow: true,
            selectable: true,
            items: [{ id: "1", label: "file1", isLeaf: true, selectionState: SELECTION_STATES.UNSELECTED }],
        });

        // GTable emits both "row-select" and "row-click" for a selectable row;
        // SelectionDialog must not toggle selection twice.
        await wrapper.find("tbody tr[aria-rowindex='1']").trigger("click");

        expect(wrapper.emitted("onClick")).toBeTruthy();
        expect(wrapper.emitted("onClick")).toHaveLength(1);
    });

    it("formats the time column from the item's updateTime and shows - when it is missing", async () => {
        const updateTime = new Date("2026-10-17T09:30:00");
        await wrapper.setProps({
            optionsShow: true,
            fields: [
                { key: "label", label: "Name" },
                { key: "time", label: "Time" },
            ],
            items: [
                { id: "1", label: "file1", isLeaf: true, time: "2020-01-01T00:00:00", updateTime },
                { id: "2", label: "file2", isLeaf: true, time: "2026-10-17T09:30:00" },
            ],
        });

        const cells = wrapper.findAll("td[id^='g-table-cell-time-']");
        expect(cells).toHaveLength(2);
        expect(nth(cells, 0).text()).toBe(
            updateTime.toLocaleString("default", {
                day: "numeric",
                month: "short",
                year: "numeric",
                minute: "numeric",
                hour: "numeric",
            }),
        );
        expect(nth(cells, 1).text()).toBe("-");
    });

    it.each([
        ["the parsed update time", "gmt"],
        ["the raw entry", "object"],
        ["the selection state", "unselected"],
    ])("does not search %s (%j)", async (_field, text) => {
        vi.useFakeTimers();
        await wrapper.setProps({
            optionsShow: true,
            items: [
                {
                    id: "1",
                    label: "reads.fastq",
                    isLeaf: true,
                    selectionState: SELECTION_STATES.UNSELECTED,
                    updateTime: new Date("2026-10-17T09:30:00Z"),
                    entry: { id: "1" },
                },
                { id: "2", label: `${text}.txt`, isLeaf: true },
            ],
        });

        await wrapper.get("input[type='text']").setValue(text);
        await vi.advanceTimersByTimeAsync(500);

        const labels = wrapper.findAll("td[id^='g-table-cell-label-']").map((cell) => cell.text());
        expect(labels).toEqual([`${text}.txt`]);
    });
});

describe("SelectionDialog.vue with a provider", () => {
    function serverProvider(count) {
        const all = Array.from({ length: count }, (_, index) => ({ id: `${index + 1}`, name: `file ${index + 1}` }));
        const load = vi.fn(async ({ page, perPage, filter, path }) => {
            const level = path.length ? [{ id: "inner", name: "inner file" }] : all;
            const matches = level.filter((raw) => raw.name.includes(filter));
            return { items: matches.slice((page - 1) * perPage, page * perPage), total: matches.length };
        });
        const map = (raw) => ({
            id: raw.id,
            label: raw.name,
            details: "",
            isLeaf: raw.id !== "1",
            url: "",
            entry: raw,
        });
        return { provider: { load, map }, load };
    }

    function mountWith(provider, props = {}) {
        return mount(SelectionDialog, {
            props: { provider, ...props },
            global: getLocalVue(),
        });
    }

    function rowLabels(wrapper) {
        return wrapper.findAll("td[id^='g-table-cell-label-']").map((cell) => cell.text());
    }

    it("shows the spinner until the first page loads, then the rows", async () => {
        const { provider } = serverProvider(3);
        const wrapper = mountWith(provider);
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBe(true);
        await flushPromises();
        expect(wrapper.find("[data-description='selection dialog spinner']").exists()).toBe(false);
        expect(rowLabels(wrapper)).toEqual(["file 1", "file 2", "file 3"]);
    });

    it("pages through the provider with the footer pagination", async () => {
        const { provider, load } = serverProvider(30);
        const wrapper = mountWith(provider);
        await flushPromises();
        expect(rowLabels(wrapper)).toHaveLength(25);

        await wrapper.find("[aria-label='Go to page 2']").trigger("click");
        await flushPromises();
        expect(load).toHaveBeenLastCalledWith(expect.objectContaining({ page: 2, perPage: 25 }));
        expect(rowLabels(wrapper)).toEqual(["file 26", "file 27", "file 28", "file 29", "file 30"]);
    });

    it("searches through the provider", async () => {
        const { provider, load } = serverProvider(30);
        const wrapper = mountWith(provider);
        await flushPromises();

        wrapper.findComponent(DataDialogSearch).vm.$emit("input", "file 3");
        await flushPromises();
        expect(load).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1, filter: "file 3" }));
        expect(rowLabels(wrapper)).toEqual(["file 3", "file 30"]);
    });

    it("opens a folder and goes back with the Back button", async () => {
        const { provider, load } = serverProvider(3);
        const wrapper = mountWith(provider);
        await flushPromises();
        expect(wrapper.find("[data-description='selection dialog undo']").exists()).toBe(false);

        await wrapper.get("button.selection-dialog-folder").trigger("click");
        await flushPromises();
        expect(load.mock.lastCall[0].path.map((item) => item.id)).toEqual(["1"]);
        expect(rowLabels(wrapper)).toEqual(["inner file"]);
        expect(emittedArg(wrapper, "onOpen").id).toBe("1");

        await wrapper.get("[data-description='selection dialog undo']").trigger("click");
        await flushPromises();
        expect(load.mock.lastCall[0].path).toEqual([]);
        expect(rowLabels(wrapper)).toEqual(["file 1", "file 2", "file 3"]);
        expect(wrapper.emitted("onUndo")).toHaveLength(1);
    });

    it("selects rows into the shared state when selectable", async () => {
        const { provider } = serverProvider(3);
        const state = useSelectItems(provider);
        const wrapper = mount(SelectionDialog, { props: { state, selectable: true }, global: getLocalVue() });
        await flushPromises();

        await wrapper.find("tbody tr[aria-rowindex='2']").trigger("click");
        expect(state.selected.value.map((item) => item.id)).toEqual(["2"]);
        expect(wrapper.find("tbody tr[aria-rowindex='2'] .g-table-select-column input").element.checked).toBe(true);
    });

    it("shows the provider's error", async () => {
        const provider = { load: () => Promise.reject(new Error("Bad error")), map: (raw) => raw };
        const wrapper = mountWith(provider);
        await flushPromises();
        expect(wrapper.findComponent(GAlert).text()).toBe("Bad error");
    });

    it("shows none of the previous level's rows while a folder loads", async () => {
        let resolveFolder;
        const load = vi.fn(({ path }) =>
            path.length
                ? new Promise((resolve) => {
                      resolveFolder = resolve;
                  })
                : Promise.resolve({ items: [{ id: "folder" }, { id: "file" }], total: 2 }),
        );
        const map = (raw) => ({ id: raw.id, label: raw.id, details: "", isLeaf: raw.id !== "folder", url: "" });
        const state = useSelectItems({ load, map });
        const wrapper = mount(SelectionDialog, { props: { state, selectable: true }, global: getLocalVue() });
        await flushPromises();

        await wrapper.get("button.selection-dialog-folder").trigger("click");
        expect(wrapper.findAll("tbody tr[aria-rowindex]")).toHaveLength(0);
        expect(wrapper.emitted("onClick")).toBeUndefined();

        resolveFolder({ items: [{ id: "inner" }], total: 1 });
        await flushPromises();
        expect(rowLabels(wrapper)).toEqual(["inner"]);
        expect(state.selected.value).toEqual([]);
    });

    it("sorts a locally paged level by the sorted field's formatter", async () => {
        const load = vi.fn(async () => ({ items: [{ id: "a" }, { id: "b" }] }));
        const map = (raw) => ({ id: raw.id, label: raw.id, details: "", isLeaf: true, url: "" });
        const fields = [{ key: "label", label: "Name", formatter: (value) => (value === "a" ? "z" : value) }];
        const wrapper = mountWith({ load, map }, { fields });
        await flushPromises();

        wrapper.findComponent(GTable).vm.$emit("sort-changed", "label", false);
        await flushPromises();
        expect(rowLabels(wrapper)).toEqual(["b", "a"]);
    });

    it("keeps the header sort in step with the query across levels", async () => {
        const load = vi.fn(async ({ path }) => {
            const items = path.length ? [{ id: `${path[0].id}-file` }] : [{ id: "f1" }, { id: "f2" }];
            return { items, total: items.length };
        });
        const map = (raw) => ({ id: raw.id, label: raw.id, details: "", isLeaf: raw.id.endsWith("-file"), url: "" });
        const wrapper = mountWith({ load, map }, { fields: [{ key: "label", label: "Name" }] });
        await flushPromises();
        const nameSort = () => wrapper.get("thead th").attributes("aria-sort");
        const openFolder = async (index) => {
            await wrapper.findAll("button.selection-dialog-folder")[index].trigger("click");
            await flushPromises();
        };
        expect(nameSort()).toBe("none");

        await openFolder(0);
        await wrapper.get("thead th").trigger("click");
        await wrapper.get("thead th").trigger("click");
        await flushPromises();
        expect(load.mock.lastCall[0]).toMatchObject({ sortBy: "label", sortDesc: true });
        expect(nameSort()).toBe("descending");

        await wrapper.get("[data-description='selection dialog undo']").trigger("click");
        await flushPromises();
        await openFolder(1);
        expect(load.mock.lastCall[0].sortBy).toBeUndefined();
        expect(nameSort()).toBe("none");

        await wrapper.get("thead th").trigger("click");
        await flushPromises();
        expect(load.mock.lastCall[0]).toMatchObject({ sortBy: "label", sortDesc: false });
        expect(nameSort()).toBe("ascending");
    });
});
