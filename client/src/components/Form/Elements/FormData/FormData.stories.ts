import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { type Component, defineComponent, h, ref } from "vue";

import { testDatatypesMapper, typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";

import type { DataOption } from "./types";

import FormData from "./FormData.vue";

// Fixtures carry only the fields FormData reads, so they are cast rather than full DataOptions.
type Options = Record<string, DataOption[]>;

const datasets = {
    dce: [
        { id: "dce1", name: "dceName1", src: "dce", is_dataset: true },
        { id: "dce2", name: "dceName2", src: "dce" },
        { id: "dce3", name: "dceName3", src: "dce", map_over_type: "mapOverType" },
        { id: "dce4", name: "dceName4", src: "dce", is_dataset: true },
    ],
    hda: [
        { id: "hda1", hid: 1, name: "hdaName1", src: "hda", tags: ["tag1"] },
        { id: "hda2", hid: 2, name: "hdaName2", src: "hda", tags: ["tag1", "tag2"] },
        { id: "hda3", hid: 3, name: "hdaName3", src: "hda", tags: ["tag2", "tag3"] },
        { id: "hda4", hid: 4, name: "hdaName4", src: "hda" },
    ],
    hdca: [
        { id: "hdca5", hid: 5, name: "hdcaName5", src: "hdca" },
        { id: "hdca6", hid: 6, name: "hdcaName6", src: "hdca" },
    ],
} as unknown as Options;

const datasetsAndDatasetElements = {
    hda: datasets.hda,
    dce: [1, 2, 3, 4].map((n) => ({ id: `dce${n}`, name: `dceName${n}`, src: "dce", is_dataset: true })),
} as unknown as Options;

const selected = (...values: Array<[string, string]>) =>
    ({ values: values.map(([src, id]) => ({ id, src })) }) as unknown as { values: DataOption[] };

/**
 * Plays the parent's part of v-model: every `input` FormData emits comes back as its
 * `value`. Tests turn that off with `vModel: false` and set `value` themselves.
 */
export const FormDataWithModel = defineComponent({
    name: "FormDataWithModel",
    inheritAttrs: false,
    props: { vModel: { type: Boolean, default: true } },
    setup(props, { attrs, expose }) {
        const value = ref(attrs.value);
        expose({
            setValue(newValue: unknown) {
                value.value = newValue;
            },
        });
        return () =>
            h(FormData as Component, {
                ...attrs,
                value: value.value,
                onInput: (newValue: unknown) => {
                    if (props.vModel) {
                        value.value = newValue;
                    }
                },
            });
    },
});

const withDatatypes: Decorator = (story) => ({
    setup() {
        useDatatypesMapperStore().datatypesMapper = testDatatypesMapper;
        return () => h(story());
    },
});

const meta = {
    title: "Form/Elements/FormData",
    component: FormData,
    excludeStories: ["FormDataWithModel"],
    render: (args) => () => h(FormDataWithModel, args),
    decorators: [withDatatypes],
    parameters: {
        msw: {
            handlers: {
                typesAndMapping: typesAndMappingHandler,
            },
        },
    },
    args: { options: datasets },
} satisfies Meta<typeof FormData>;

export default meta;
type Story = StoryObj<typeof meta>;

export const SingleDataset: Story = {};

export const OptionalDataset: Story = { args: { optional: true } };

export const NoDatasetsInWorkflowRun: Story = { args: { options: {}, workflowRun: true } };

export const MultipleDatasets: Story = {
    args: { multiple: true, optional: true, value: selected(["hda", "hda2"], ["hda", "hda3"]) },
};

export const MultipleDatasetsSelectedOutOfOrder: Story = {
    args: { ...MultipleDatasets.args, value: selected(["hda", "hda2"], ["hda", "hda3"], ["hda", "hda1"]) },
};

export const MultipleDatasetsAndElementsIntermixed: Story = {
    args: {
        ...MultipleDatasets.args,
        options: datasetsAndDatasetElements,
        value: selected(["hda", "hda1"], ["dce", "dce4"], ["dce", "dce2"], ["hda", "hda2"], ["dce", "dce3"]),
    },
};

export const CollectionElementThatIsADataset: Story = { args: { value: selected(["dce", "dce1"]) } };

export const CollectionElementThatIsACollection: Story = { args: { value: selected(["dce", "dce2"]) } };

export const CollectionElementMappedOver: Story = { args: { value: selected(["dce", "dce3"]) } };

export const CollectionElementMappedOverOnCollectionInput: Story = {
    args: { type: "data_collection", value: selected(["dce", "dce3"]) },
};

export const CollectionOnCollectionInput: Story = {
    args: { type: "data_collection", value: selected(["hdca", "hdca5"]) },
};

export const TwoCollectionElementsThatAreDatasets: Story = {
    args: { value: selected(["dce", "dce1"], ["dce", "dce4"]) },
};

export const EmptyCollectionInput: Story = { args: { type: "data_collection" } };

export const EmptyListCollectionInput: Story = { args: { type: "data_collection", collectionTypes: ["list"] } };

export const InWorkflowEditor: Story = { args: { flavor: "module" } };

export const CollectionOnMultipleDatasetsInput: Story = {
    args: { multiple: true, value: selected(["hdca", "hdca5"]) },
};

export const PinnedSelectionOutsideCurrentPage: Story = {
    args: {
        options: { hda: datasets.hda! },
        pinned: {
            hda: [{ id: "hdaPinned", hid: 999, name: "OldDataset", src: "hda", keep: true, tags: [] }],
        } as unknown as Options,
        value: selected(["hda", "hdaPinned"]),
    },
};

export const FilteredByTag: Story = { args: { tag: "tag1" } };
