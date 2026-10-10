import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { selectableObjectStores } from "@/components/ObjectStore/test_fixtures";

import ToolSelectPreferredObjectStore from "./ToolSelectPreferredObjectStore.vue";

const meta = {
    title: "Tool/ToolSelectPreferredObjectStore",
    component: ToolSelectPreferredObjectStore,
    args: { toolPreferredObjectStoreId: null },
    parameters: { msw: { handlers: { objectStores: selectableObjectStores() } } },
} satisfies Meta<typeof ToolSelectPreferredObjectStore>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The tool has no preference, so the "Use Defaults" card is the current choice. */
export const UsesDefaults: Story = {};

/** The tool's outputs go to Object Store 1. */
export const PreferredStorage: Story = { args: { toolPreferredObjectStoreId: "object_store_1" } };
