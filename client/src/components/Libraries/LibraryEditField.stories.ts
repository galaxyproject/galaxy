import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";
import { defineComponent, h, ref } from "vue";

import { MAX_DESCRIPTION_LENGTH } from "./library-utils";

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

export const LinkedDescription: Story = {
    args: { text: "See https://usegalaxy.org <em>now</em>" },
    play: async ({ canvas, step }) => {
        await step("Read the linked description with its emphasis", async () => {
            const link = canvas.getByRole("link", { name: "https://usegalaxy.org" });
            await expect(link).toBeVisible();
            await expect(link).toHaveAttribute("href", "https://usegalaxy.org");
            await expect(canvas.getByRole("emphasis")).toHaveTextContent(/^now$/);
        });
    },
};

export const CollapsedDescription: Story = {
    args: { text: "Reference genome annotations and alignments for the Arabidopsis thaliana reference assembly." },
};

export const ExpandedDescription: Story = {
    args: { ...CollapsedDescription.args, isExpanded: true },
};

export const ExpandsDescription: Story = {
    ...CollapsedDescription,
    play: async ({ canvas, args, userEvent, step }) => {
        const text = args.text!;
        await step("Start with a shortened description", async () => {
            await expect(canvas.getByText(text.substring(0, MAX_DESCRIPTION_LENGTH), { exact: true })).toBeVisible();
            await expect(canvas.queryByText(text, { exact: true })).not.toBeInTheDocument();
            await expect(canvas.getByRole("link", { name: "(more)" })).toBeVisible();
        });
        await step("Expand and read the complete description", async () => {
            await userEvent.click(canvas.getByRole("link", { name: "(more)" }));
            await expect(await canvas.findByText(text, { exact: true })).toBeVisible();
            await expect(canvas.getByRole("link", { name: "(less)" })).toBeVisible();
            await expect(canvas.queryByRole("link", { name: "(more)" })).not.toBeInTheDocument();
        });
    },
};

export const CollapsesDescription: Story = {
    ...ExpandedDescription,
    play: async ({ canvas, args, userEvent, step }) => {
        const text = args.text!;
        await step("Start with the complete description", async () => {
            await expect(canvas.getByText(text, { exact: true })).toBeVisible();
            await expect(canvas.getByRole("link", { name: "(less)" })).toBeVisible();
        });
        await step("Collapse the description back to its preview", async () => {
            await userEvent.click(canvas.getByRole("link", { name: "(less)" }));
            await expect(
                await canvas.findByText(text.substring(0, MAX_DESCRIPTION_LENGTH), { exact: true }),
            ).toBeVisible();
            await expect(canvas.queryByText(text, { exact: true })).not.toBeInTheDocument();
            await expect(canvas.getByRole("link", { name: "(more)" })).toBeVisible();
            await expect(canvas.queryByRole("link", { name: "(less)" })).not.toBeInTheDocument();
        });
    },
};
