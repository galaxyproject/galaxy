import type { Meta, StoryObj } from "@storybook/vue3-vite";

import FormElementHelpMarkdown from "./FormElementHelpMarkdown.vue";

const meta = {
    title: "Form/FormElementHelpMarkdown",
    component: FormElementHelpMarkdown,
} satisfies Meta<typeof FormElementHelpMarkdown>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Tool parameter help links to Galaxy's regular-expression glossary; raw HTML remains literal text. */
export const RegularExpressionHelp: Story = {
    args: {
        content:
            "Filter reads with a [regular expression](gxhelp://programming.python.regex). Raw HTML such as <b>raw</b> is displayed as text.",
    },
};

/** A parameter with a short explanation and no glossary links. */
export const PlainHelp: Story = {
    args: { content: "Select a FASTQ dataset before running this tool." },
};
