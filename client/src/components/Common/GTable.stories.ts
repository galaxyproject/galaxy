import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";
import { defineComponent, h, ref } from "vue";

import GTable from "./GTable.vue";

type Args = Parameters<typeof GTable>[0];

/** Owns row indexes as a dataset picker does, so checkbox and row selections stay visible. */
export const DatasetTableWithSelection = defineComponent({
    name: "DatasetTableWithSelection",
    compatConfig: { MODE: 3 },
    inheritAttrs: false,
    setup(_props, { attrs }) {
        const selectedItems = ref<number[]>([...((attrs.selectedItems as number[] | undefined) ?? [])]);
        const indeterminateItems = ref<number[]>([...((attrs.indeterminateItems as number[] | undefined) ?? [])]);
        return () =>
            h(GTable, {
                ...attrs,
                selectedItems: selectedItems.value,
                indeterminateItems: indeterminateItems.value,
                onRowSelect: ({ index, selected }: { index: number; selected: boolean }) => {
                    selectedItems.value = selected
                        ? [...new Set([...selectedItems.value, index])]
                        : selectedItems.value.filter((candidate) => candidate !== index);
                    indeterminateItems.value = indeterminateItems.value.filter((candidate) => candidate !== index);
                },
                onSelectAll: (selected: boolean) => {
                    selectedItems.value = selected ? (attrs.items as unknown[]).map((_, index) => index) : [];
                    indeterminateItems.value = [];
                },
            });
    },
});

const meta = {
    title: "Common/GTable",
    excludeStories: ["DatasetTableWithSelection"],
    render: (args) => () => h(DatasetTableWithSelection, args),
    args: {
        items: [
            { id: 1, name: "Control read counts", note: "Control sample" },
            { id: 2, name: "Treated read counts", note: "Treated sample" },
        ],
        fields: [{ key: "name", label: "Dataset" }],
    },
    // The harness owns live selection; these choose the initial state.
    argTypes: { selectedItems: { control: false }, indeterminateItems: { control: false } },
} satisfies Meta<Args>;

export default meta;
type Story = StoryObj<Args>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

function datasetCheckbox(context: PlayContext, name: string, title = "Select for bulk actions") {
    const row = context.canvas.getByRole("row", { name: new RegExp(name) });
    return within(row).getByRole("checkbox", { name: title });
}

async function readSelectionNames(context: PlayContext, title = "Select for bulk actions") {
    await expect(context.canvas.getByRole("checkbox", { name: "Select all for bulk actions" })).toBeVisible();
    for (const name of ["Control read counts", "Treated read counts"]) {
        await expect(datasetCheckbox(context, name, title)).toBeVisible();
    }
}

function namesInOrder({ canvas }: PlayContext) {
    return canvas.getAllByRole("row").flatMap((row) => {
        const cells = within(row).queryAllByRole("cell");
        return cells.length ? [cells[0]!.textContent?.trim()] : [];
    });
}

export const SelectableDatasets: Story = {
    args: { selectable: true, clickableRows: true, showSelectAll: true },
};

/** One dataset is selected, while the other contains a partial collection selection. */
export const PartialSelection: Story = {
    args: { ...SelectableDatasets.args, selectedItems: [0], indeterminateItems: [1] },
    play: async (context) => {
        await context.step("Read a selected dataset and a partial collection selection", async () => {
            await readSelectionNames(context);
            await expect(
                context.canvas.getByRole("checkbox", { name: "Select all for bulk actions" }),
            ).toBePartiallyChecked();
            const control = datasetCheckbox(context, "Control read counts");
            await expect(control).toBeChecked();
            await expect(control).not.toBePartiallyChecked();
            await expect(datasetCheckbox(context, "Treated read counts")).toBePartiallyChecked();
        });
    },
};

export const AllSelected: Story = {
    args: { ...SelectableDatasets.args, selectedItems: [0, 1] },
    play: async (context) => {
        await context.step("Read all datasets selected without a mixed header", async () => {
            await readSelectionNames(context);
            const header = context.canvas.getByRole("checkbox", { name: "Select all for bulk actions" });
            await expect(header).toBeChecked();
            await expect(header).not.toBePartiallyChecked();
            await expect(datasetCheckbox(context, "Control read counts")).toBeChecked();
            await expect(datasetCheckbox(context, "Treated read counts")).toBeChecked();
        });
    },
};

/** Name and ID headers sort by click or keyboard; the note column stays unsortable. */
export const SortableDatasets: Story = {
    args: {
        fields: [
            { key: "name", label: "Name", sortable: true },
            { key: "id", label: "Id", sortable: true },
            { key: "note", label: "Note" },
        ],
        sortBy: "name",
    },
};

/** Selection controls retain their default names even when rows are not clickable. */
export const DefaultSelectionNames: Story = {
    args: { ...SelectableDatasets.args, clickableRows: false, selectCheckboxTitle: undefined },
    play: async (context) => {
        await context.step("Read the default names for the header and both dataset checkboxes", async () => {
            await readSelectionNames(context);
        });
    },
};

/** A dataset picker supplies its row-checkbox name while the bulk header keeps its own name. */
export const CustomSelectionNames: Story = {
    args: { ...SelectableDatasets.args, clickableRows: false, selectCheckboxTitle: "Select dataset" },
    play: async (context) => {
        await context.step("Read the supplied name on both dataset checkboxes", async () => {
            await readSelectionNames(context, "Select dataset");
        });
    },
};

/** The checkbox label selects and deselects the treated dataset. */
export const SelectsDataset: Story = {
    ...SelectableDatasets,
    play: async (context) => {
        await context.step("Select the treated dataset through its checkbox label", async () => {
            await readSelectionNames(context);
            const treated = datasetCheckbox(context, "Treated read counts");
            const control = datasetCheckbox(context, "Control read counts");
            await expect(treated).not.toBeChecked();
            await expect(control).not.toBeChecked();
            const label = (treated as HTMLInputElement).labels![0]!;
            await context.userEvent.click(label);
            await waitFor(() => expect(treated).toBeChecked());
            await expect(treated).toBeVisible();
            await expect(control).not.toBeChecked();
            await expect(
                context.canvas.getByRole("checkbox", { name: "Select all for bulk actions" }),
            ).toBePartiallyChecked();
            await context.userEvent.click(label);
            await waitFor(() => expect(treated).not.toBeChecked());
            await expect(treated).toBeVisible();
            const header = context.canvas.getByRole("checkbox", { name: "Select all for bulk actions" });
            await expect(header).not.toBeChecked();
            await expect(header).not.toBePartiallyChecked();
        });
    },
};

/** The bulk checkbox selects every dataset and clears the selection again. */
export const SelectsAllDatasets: Story = {
    ...SelectableDatasets,
    play: async (context) => {
        await context.step("Select and clear both datasets through the bulk checkbox", async () => {
            await readSelectionNames(context);
            const header = context.canvas.getByRole("checkbox", { name: "Select all for bulk actions" });
            await expect(header).not.toBeChecked();
            for (const name of ["Control read counts", "Treated read counts"]) {
                await expect(datasetCheckbox(context, name)).not.toBeChecked();
            }
            await context.userEvent.click((header as HTMLInputElement).labels![0]!);
            await waitFor(() => expect(header).toBeChecked());
            for (const name of ["Control read counts", "Treated read counts"]) {
                const checkbox = datasetCheckbox(context, name);
                await expect(checkbox).toBeVisible();
                await expect(checkbox).toBeChecked();
            }
            await expect(header).not.toBePartiallyChecked();
            await context.userEvent.click((header as HTMLInputElement).labels![0]!);
            await waitFor(() => expect(header).not.toBeChecked());
            await expect(header).not.toBePartiallyChecked();
            for (const name of ["Control read counts", "Treated read counts"]) {
                await expect(datasetCheckbox(context, name)).not.toBeChecked();
            }
        });
    },
};

/** The original first/second records sort with Enter and return to ascending order with Space. */
export const SortsFromKeyboard: Story = {
    args: {
        ...SortableDatasets.args,
        items: [
            { id: 1, name: "first" },
            { id: 2, name: "second" },
        ],
    },
    play: async (context) => {
        await context.step("Reach the ascending Name header with Tab", async () => {
            await expect(namesInOrder(context)).toEqual(["first", "second"]);
            const name = context.canvas.getByRole("columnheader", { name: "Name" });
            await expect(name).toHaveAttribute("aria-sort", "ascending");
            await context.userEvent.tab();
            await expect(name).toHaveFocus();
        });
        await context.step("Sort descending with Enter, then ascending with Space", async () => {
            const name = context.canvas.getByRole("columnheader", { name: "Name" });
            await context.userEvent.keyboard("{Enter}");
            await waitFor(() => expect(namesInOrder(context)).toEqual(["second", "first"]));
            await expect(name).toHaveAttribute("aria-sort", "descending");
            await context.userEvent.keyboard(" ");
            await waitFor(() => expect(namesInOrder(context)).toEqual(["first", "second"]));
            await expect(name).toHaveAttribute("aria-sort", "ascending");
        });
    },
};
