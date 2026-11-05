import { nth } from "@tests/vitest/helpers";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import { effectScope } from "vue";

import {
    SELECTION_STATES,
    type SelectionItem,
    type SelectItemsPage,
    type SelectItemsProvider,
    type SelectItemsQuery,
} from "@/components/SelectionDialog/selectionTypes";

import { useSelectItems } from "./useSelectItems";

interface Raw {
    id: string;
    name: string;
    folder?: boolean;
    size?: number | null;
}

function toItem(raw: Raw): SelectionItem {
    return {
        id: raw.id,
        label: raw.name,
        details: "",
        isLeaf: !raw.folder,
        url: `url-${raw.id}`,
        size: raw.size ?? undefined,
        entry: { ...raw },
    };
}

function records(count: number, prefix = "item"): Raw[] {
    return Array.from({ length: count }, (_, index) => ({
        id: `${prefix}-${index + 1}`,
        name: `${prefix} ${index + 1}`,
    }));
}

/** Provider whose loads resolve only when the test says so. */
function deferredProvider() {
    const calls: {
        query: SelectItemsQuery;
        resolve: (page: SelectItemsPage<Raw>) => void;
        reject: (e: unknown) => void;
    }[] = [];
    const provider: SelectItemsProvider<Raw> = {
        load: (query) =>
            new Promise((resolve, reject) => {
                calls.push({ query, resolve, reject });
            }),
        map: toItem,
    };
    return { provider, calls };
}

/** Provider that pages server-side over the given records. */
function serverProvider(all: Raw[]) {
    const load = vi.fn(async (query: SelectItemsQuery) => {
        const matches = all.filter((raw) => raw.name.includes(query.filter));
        const start = (query.page - 1) * query.perPage;
        return { items: matches.slice(start, start + query.perPage), total: matches.length };
    });
    return { provider: { load, map: toItem } as SelectItemsProvider<Raw>, load };
}

/** Provider that returns every record at once and leaves paging to the composable. */
function clientProvider(all: Raw[]) {
    const load = vi.fn(async () => ({ items: all }));
    return { provider: { load, map: toItem } as SelectItemsProvider<Raw>, load };
}

describe("useSelectItems", () => {
    it("drops a response that arrives after a newer query", async () => {
        const { provider, calls } = deferredProvider();
        const state = useSelectItems(provider);
        state.filter.value = "new";
        expect(calls).toHaveLength(2);

        calls[1]!.resolve({ items: [{ id: "new", name: "new" }], total: 1 });
        await flushPromises();
        calls[0]!.resolve({ items: [{ id: "old", name: "old" }], total: 1 });
        await flushPromises();

        expect(state.items.value.map((item) => item.id)).toEqual(["new"]);
    });

    it("aborts the running request when the query changes, without reporting an error", async () => {
        const { provider, calls } = deferredProvider();
        const state = useSelectItems(provider);
        const first = calls[0]!.query.signal;
        expect(first.aborted).toBe(false);

        state.filter.value = "x";
        expect(first.aborted).toBe(true);
        expect(calls[1]!.query.signal.aborted).toBe(false);

        calls[0]!.reject(new DOMException("The operation was aborted.", "AbortError"));
        await flushPromises();
        expect(state.error.value).toBe("");
    });

    it("reports a failed load and clears it on the next successful one", async () => {
        const { provider, calls } = deferredProvider();
        const state = useSelectItems(provider);
        calls[0]!.reject(new Error("Bad error"));
        await flushPromises();
        expect(state.error.value).toBe("Bad error");
        expect(state.loading.value).toBe(false);

        state.reload();
        calls[1]!.resolve({ items: [], total: 0 });
        await flushPromises();
        expect(state.error.value).toBe("");
    });

    it("loads one page per page change when the provider returns a total", async () => {
        const { provider, load } = serverProvider(records(75));
        const state = useSelectItems(provider);
        await flushPromises();
        expect(state.serverPaging.value).toBe(true);
        expect(state.total.value).toBe(75);
        expect(state.items.value.map((item) => item.id)).toEqual(records(25).map((raw) => raw.id));

        state.page.value = 3;
        await flushPromises();
        expect(load).toHaveBeenCalledTimes(2);
        expect(load.mock.calls[1]![0]).toMatchObject({ page: 3, perPage: 25, filter: "" });
        expect(state.items.value[0]!.id).toBe("item-51");
    });

    it("loads once and pages, filters and sorts locally when the provider returns no total", async () => {
        const all = [...records(75), { id: "zz", name: "zebra" }];
        const { provider, load } = clientProvider(all);
        const state = useSelectItems(provider);
        await flushPromises();
        expect(state.serverPaging.value).toBe(false);
        expect(state.total.value).toBe(76);
        expect(state.items.value).toHaveLength(25);

        state.page.value = 4;
        expect(state.items.value.map((item) => item.id)).toEqual(["zz"]);

        state.filter.value = "ZEB";
        expect(state.page.value).toBe(1);
        expect(state.total.value).toBe(1);
        expect(state.items.value.map((item) => item.id)).toEqual(["zz"]);

        state.filter.value = "";
        state.setSort("label", true);
        expect(state.items.value[0]!.id).toBe("zz");
        expect(load).toHaveBeenCalledTimes(1);
    });

    it.each(["f0", "url", "true", "selected", "object"])(
        "searches only the label, details and tags locally, not %j",
        async (text) => {
            const { provider } = clientProvider([
                { id: "f0a1b2c3d4e5f607", name: "alpha" },
                { id: "f0b2c3d4e5f60718", name: "beta" },
            ]);
            const state = useSelectItems(provider);
            await flushPromises();
            state.toggle(state.items.value[0]!);

            state.filter.value = text;
            expect(state.items.value).toEqual([]);
        },
    );

    it("searches the details and tags locally", async () => {
        const load = vi.fn(async () => ({ items: [{ id: "f0a1b2c3d4e5f607", name: "alpha" }] }));
        const map = (raw: Raw): SelectionItem => ({ ...toItem(raw), details: "fastq reads", tags: ["name:rna"] });
        const state = useSelectItems({ load, map });
        await flushPromises();

        state.filter.value = "reads";
        expect(state.items.value).toHaveLength(1);
        state.filter.value = "name:rna";
        expect(state.items.value).toHaveLength(1);
    });

    it("searches the given filterKeys locally", async () => {
        const { provider } = clientProvider([{ id: "f0a1b2c3d4e5f607", name: "alpha" }]);
        const state = useSelectItems(provider, { filterKeys: ["id"] });
        await flushPromises();

        state.filter.value = "f0a1";
        expect(state.items.value).toHaveLength(1);
        state.filter.value = "alpha";
        expect(state.items.value).toEqual([]);
    });

    it("resets the page and loads exactly once when the filter changes", async () => {
        const { provider, load } = serverProvider(records(30));
        const state = useSelectItems(provider);
        await flushPromises();
        state.page.value = 2;
        await flushPromises();
        load.mockClear();

        state.filter.value = "item 1";
        await flushPromises();
        expect(state.page.value).toBe(1);
        expect(load).toHaveBeenCalledTimes(1);
        expect(load.mock.calls[0]![0]).toMatchObject({ page: 1, filter: "item 1" });
    });

    it("opens a folder unfiltered and unsorted, and returns to the page, filter and sort it was opened from", async () => {
        const folders = records(60, "folder").map((raw) => ({ ...raw, folder: true }));
        const load = vi.fn(async (query: SelectItemsQuery) => {
            const all = query.path.length ? records(3, "file") : folders;
            const start = (query.page - 1) * query.perPage;
            return { items: all.slice(start, start + query.perPage), total: all.length };
        });
        const state = useSelectItems({ load, map: toItem });
        await flushPromises();
        state.page.value = 2;
        await flushPromises();
        state.filter.value = "folder";
        await flushPromises();
        state.page.value = 2;
        await flushPromises();
        state.setSort("label", true);
        await flushPromises();

        const folder = state.items.value[0]!;
        state.open(folder);
        await flushPromises();
        expect(state.path.value.map((item) => item.id)).toEqual([folder.id]);
        expect(state.page.value).toBe(1);
        expect(state.filter.value).toBe("");
        expect(state.sortBy.value).toBeUndefined();
        expect(load.mock.lastCall![0]).toMatchObject({ page: 1, filter: "", sortBy: undefined, path: [folder] });
        expect(state.items.value.map((item) => item.id)).toEqual(["file-1", "file-2", "file-3"]);

        const callsBeforeBack = load.mock.calls.length;
        state.back();
        await flushPromises();
        expect(load.mock.calls.length).toBe(callsBeforeBack + 1);
        expect(state.path.value).toEqual([]);
        expect(state.page.value).toBe(2);
        expect(state.filter.value).toBe("folder");
        expect(state.sortBy.value).toBe("label");
        expect(state.sortDesc.value).toBe(true);
        expect(load.mock.lastCall![0]).toMatchObject({
            page: 2,
            filter: "folder",
            sortBy: "label",
            sortDesc: true,
            path: [],
        });
    });

    it("restores the local sort formatter on back", async () => {
        const load = vi.fn(async (query: SelectItemsQuery) => ({
            items: query.path.length
                ? []
                : [
                      { id: "a", name: "a", size: 1 },
                      { id: "b", name: "b", size: 2 },
                      { id: "f", name: "f", folder: true, size: 3 },
                  ],
        }));
        const state = useSelectItems({ load, map: toItem });
        await flushPromises();
        state.setSort("size", false, (value: number) => nth(["z", "a", "m"], value - 1));
        expect(state.items.value.map((item) => item.id)).toEqual(["b", "f", "a"]);

        state.open(nth(state.items.value, 1));
        await flushPromises();
        state.back();
        await flushPromises();
        expect(state.items.value.map((item) => item.id)).toEqual(["b", "f", "a"]);
    });

    it("keeps the selection across pages and derives each row's state from it", async () => {
        const { provider } = serverProvider(records(60));
        const state = useSelectItems(provider);
        await flushPromises();

        state.toggle(state.items.value[0]!);
        expect(state.items.value[0]!.selectionState).toBe(SELECTION_STATES.SELECTED);
        expect(state.items.value[1]!.selectionState).toBe(SELECTION_STATES.UNSELECTED);

        state.page.value = 2;
        await flushPromises();
        state.selectAll(true);
        expect(state.selected.value).toHaveLength(26);

        state.page.value = 1;
        await flushPromises();
        expect(state.items.value[0]!.selectionState).toBe(SELECTION_STATES.SELECTED);

        state.toggle(state.items.value[0]!);
        expect(state.selected.value).toHaveLength(25);

        state.selectAll(false);
        expect(state.selected.value).toEqual([]);
    });

    it("leaves sortDesc out of the query until a column is sorted", async () => {
        const { provider, load } = serverProvider(records(5));
        const state = useSelectItems(provider);
        state.filter.value = "item";
        await flushPromises();
        expect(nth(load.mock.calls, -1)[0].sortDesc).toBeUndefined();

        state.setSort("label", false);
        await flushPromises();
        expect(nth(load.mock.calls, -1)[0]).toMatchObject({ sortBy: "label", sortDesc: false });
    });

    it("ignores toggling a folder", async () => {
        const { provider } = clientProvider([{ id: "f", name: "folder", folder: true }]);
        const state = useSelectItems(provider);
        await flushPromises();
        state.toggle(nth(state.items.value, 0));
        expect(state.selected.value).toEqual([]);
    });

    it("clears the previous level's rows while the next level loads", async () => {
        const { provider, calls } = deferredProvider();
        const state = useSelectItems(provider);
        nth(calls, 0).resolve({ items: [{ id: "f", name: "folder", folder: true }], total: 40 });
        await flushPromises();

        state.open(nth(state.items.value, 0));
        expect(state.items.value).toEqual([]);
        expect(state.total.value).toBe(0);

        nth(calls, 1).resolve({ items: [{ id: "a", name: "a" }], total: 1 });
        await flushPromises();
        expect(state.items.value.map((item) => item.id)).toEqual(["a"]);
    });

    it("ignores a second open while the level loads, so one back returns to the root", async () => {
        const { provider, calls } = deferredProvider();
        const state = useSelectItems(provider);
        nth(calls, 0).resolve({ items: [{ id: "f", name: "folder", folder: true }] });
        await flushPromises();
        const folder = nth(state.items.value, 0);

        state.open(folder);
        state.open(folder);
        expect(calls).toHaveLength(2);
        nth(calls, 1).resolve({ items: [] });
        await flushPromises();
        expect(state.path.value.map((item) => item.id)).toEqual(["f"]);

        state.back();
        expect(state.path.value).toEqual([]);
    });

    it("aborts the running request when its scope is disposed, without reporting an error", async () => {
        const { provider, calls } = deferredProvider();
        const scope = effectScope();
        const state = scope.run(() => useSelectItems(provider))!;
        scope.stop();
        expect(nth(calls, 0).query.signal.aborted).toBe(true);

        nth(calls, 0).reject(new DOMException("The operation was aborted.", "AbortError"));
        await flushPromises();
        expect(state.error.value).toBe("");
    });

    it.each([false, true])("sorts missing values last locally (descending: %s)", async (desc) => {
        const { provider } = clientProvider([
            { id: "none", name: "none", size: null },
            { id: "small", name: "small", size: 1 },
            { id: "big", name: "big", size: 9 },
        ]);
        const state = useSelectItems(provider);
        await flushPromises();
        state.setSort("size", desc);
        expect(state.items.value.map((item) => item.id)).toEqual(
            desc ? ["big", "small", "none"] : ["small", "big", "none"],
        );
    });

    it("sorts locally by the field formatter's output", async () => {
        const { provider } = clientProvider([
            { id: "a", name: "a", size: 1 },
            { id: "b", name: "b", size: 2 },
        ]);
        const state = useSelectItems(provider);
        await flushPromises();
        state.setSort("size", false, (value: number) => (value === 1 ? "z" : "a"));
        expect(state.items.value.map((item) => item.id)).toEqual(["b", "a"]);
    });
});
