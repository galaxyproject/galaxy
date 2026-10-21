import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";

import FormElementHelpMarkdown from "./FormElementHelpMarkdown.vue";

const meta = {
    title: "Form/FormElementHelpMarkdown",
    component: FormElementHelpMarkdown,
} satisfies Meta<typeof FormElementHelpMarkdown>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Read the rendered help through the real sanitizer and Galaxy's glossary-link rewrite. */
async function readRegularExpressionHelp({ canvas, step }: PlayContext) {
    await step("Read the help and its glossary link", async () => {
        const link = await canvas.findByRole("link", { name: "regular expression" });
        await expect(link).toBeVisible();
        await expect(link).toHaveAttribute("href", "/help/terms/programming.python.regex");
        await expect(canvas.getByRole("paragraph")).toHaveTextContent(
            /^Filter reads with a regular expression\. Raw HTML such as <b>raw<\/b> is displayed as text\.$/,
        );
        await expect(canvas.queryByText("raw", { exact: true })).not.toBeInTheDocument();
    });
}

/** Tool parameter help links to Galaxy's regular-expression glossary; raw HTML remains literal text. */
export const RegularExpressionHelp: Story = {
    args: {
        content:
            "Filter reads with a [regular expression](gxhelp://programming.python.regex). Raw HTML such as <b>raw</b> is displayed as text.",
    },
    play: readRegularExpressionHelp,
};

/** A parameter with a short explanation and no glossary links. */
export const PlainHelp: Story = {
    args: { content: "Select a FASTQ dataset before running this tool." },
    play: async ({ canvas, step }) => {
        await step("Read the short parameter explanation without a glossary link", async () => {
            const paragraph = await canvas.findByRole("paragraph");
            await expect(paragraph).toBeVisible();
            await expect(paragraph).toHaveTextContent(/^Select a FASTQ dataset before running this tool\.$/);
            await expect(canvas.queryByRole("link")).not.toBeInTheDocument();
        });
    },
};

/** Hover the glossary reference to read the explanation without leaving the tool form. */
export const OpensRegularExpressionHelp: Story = {
    args: RegularExpressionHelp.args,
    play: async (context) => {
        await readRegularExpressionHelp(context);
        const { canvas, userEvent, step } = context;
        await step("Reveal the glossary explanation by hovering its link", async () => {
            await expect(
                canvas.queryByRole("link", { name: "this Python for Biologists tutorial" }),
            ).not.toBeInTheDocument();
            await userEvent.hover(canvas.getByRole("link", { name: "regular expression" }));
            await expect(
                canvas.findByRole("link", { name: "this Python for Biologists tutorial" }),
            ).resolves.toBeVisible();
            const explanation = canvas.getByText(
                /^Regular expressions are patterns used to match character combinations in strings\./,
            );
            await expect(explanation).toBeVisible();
            await userEvent.unhover(canvas.getByRole("link", { name: "regular expression" }));
        });
    },
};
