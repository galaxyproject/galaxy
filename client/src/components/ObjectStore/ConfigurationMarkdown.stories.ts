import type { Meta, StoryObj } from "@storybook/vue3-vite";

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

/** Written by an admin (storage and template descriptions, help terms), so inline HTML renders. */
export const AdminConfigured: Story = { args: { admin: true } };

/** A user's own storage description: markdown still renders, but inline HTML shows as text. */
export const UserDefined: Story = { args: { admin: false } };
