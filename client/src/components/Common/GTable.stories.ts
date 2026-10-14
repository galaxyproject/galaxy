import type { Meta, StoryObj } from "@storybook/vue3-vite";
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

export const SelectableDatasets: Story = {
    args: { selectable: true, clickableRows: true, showSelectAll: true },
};

/** One dataset is selected, while the other contains a partial collection selection. */
export const PartialSelection: Story = {
    args: { ...SelectableDatasets.args, selectedItems: [0], indeterminateItems: [1] },
};

export const AllSelected: Story = {
    args: { ...SelectableDatasets.args, selectedItems: [0, 1] },
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
