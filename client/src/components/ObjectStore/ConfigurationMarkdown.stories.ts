import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";

import ConfigurationMarkdown from "./ConfigurationMarkdown.vue";

const meta = {
    title: "ObjectStore/ConfigurationMarkdown",
    component: ConfigurationMarkdown,
    args: {
        markdown:
            'Scratch space, *not backed up*. <b>Purged after 30 days.</b> See the <a href="https://example.org" target="_blank">storage policy</a>.',
    },
} satisfies Meta<typeof ConfigurationMarkdown>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function seeMarkdownEmphasis({ canvas, step }: PlayContext) {
    await step("See the markdown emphasis rendered as emphasis", async () => {
        await expect(canvas.getByRole("emphasis")).toHaveTextContent(/^not backed up$/);
    });
}

/** Written by an admin (storage and template descriptions, help terms), so inline HTML renders. */
export const AdminConfigured: Story = {
    args: { admin: true },
    play: async (context) => {
        const { canvas, step } = context;
        await step("Read the description with no markup showing", async () => {
            await expect(canvas.getByRole("paragraph")).toHaveTextContent(
                /^Scratch space, not backed up\. Purged after 30 days\. See the storage policy\.$/,
            );
        });
        await seeMarkdownEmphasis(context);
        await step("See the admin's inline HTML rendered as bold text", async () => {
            await expect(canvas.getByText("Purged after 30 days.").tagName).toBe("B");
        });
        await step("See the storage policy link open in a new window", async () => {
            const link = canvas.getByRole("link", { name: "storage policy" });
            await expect(link).toHaveAttribute("href", "https://example.org");
            await expect(link).toHaveAttribute("target", "_blank");
            await expect(link).toHaveAttribute("rel", "noopener noreferrer");
        });
    },

    // TODO a11y: link-in-text-block (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A user's own storage description: markdown still renders, but inline HTML shows as text. */
export const UserDefined: Story = {
    args: { admin: false },
    play: async (context) => {
        const { canvas, step } = context;
        await seeMarkdownEmphasis(context);
        await step("Read the user's inline HTML as literal text", async () => {
            await expect(canvas.getByRole("paragraph").textContent).toBe(
                'Scratch space, not backed up. <b>Purged after 30 days.</b> See the <a href="https://example.org" target="_blank">storage policy</a>.',
            );
            await expect(canvas.queryByText("Purged after 30 days.")).toBeNull();
            await expect(canvas.queryByRole("link")).toBeNull();
        });
    },
};
