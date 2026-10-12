import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { defineComponent, h, ref } from "vue";

import LibraryEditField from "./LibraryEditField.vue";

/** The library page feeds an expansion toggle back into the description. */
const LibraryDescription = defineComponent({
    name: "LibraryDescription",
    props: { text: { type: String, default: "" }, isExpanded: Boolean },
    setup(props) {
        const expanded = ref(props.isExpanded);
        return () =>
            h(LibraryEditField, {
                text: props.text,
                isExpanded: expanded.value,
                onToggleDescriptionExpand: () => {
                    expanded.value = !expanded.value;
                },
            });
    },
});

/** Library descriptions linkify URLs and shorten long descriptions until the reader expands them. */
const meta = {
    title: "Libraries/LibraryEditField",
    component: LibraryEditField,
    render: (args) => () => h(LibraryDescription, args),
} satisfies Meta<typeof LibraryEditField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const LinkedDescription: Story = { args: { text: "See https://usegalaxy.org <em>now</em>" } };

export const CollapsedDescription: Story = {
    args: { text: "Reference genome annotations and alignments for the Arabidopsis thaliana reference assembly." },
};

export const ExpandedDescription: Story = {
    args: { ...CollapsedDescription.args, isExpanded: true },
};
