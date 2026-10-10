import type { Meta, StoryObj } from "@storybook/vue3-vite";

import ExportForm from "./ExportForm.vue";

/** An empty form; export stays disabled until a directory and name are set. */
const meta = {
    title: "Common/ExportForm",
    component: ExportForm,
} satisfies Meta<typeof ExportForm>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Exporting a history archive, as the history export's remote-file tab asks for it. */
export const HistoryArchive: Story = { args: { what: "history archive" } };

/** Exporting a history, as the archive dialog's repository tab asks for it. */
export const History: Story = { args: { what: "history" } };
