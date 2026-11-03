import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";

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

export const OffersEachStorageLocation: Story = {
    play: async ({ canvas, step }) => {
        await step("See the default option and each storage location", async () => {
            await canvas.findByRole("heading", { name: "Use Defaults" });
            const options = canvas.getAllByRole("heading").map((heading) => heading.textContent?.trim());
            await expect(options).toEqual(["Use Defaults", "Object Store 1", "Object Store 2"]);
        });
        await step("See the defaults are current, so only the storage locations can be selected", async () => {
            await expect(canvas.getAllByRole("button", { name: "Select as the preferred one" })).toHaveLength(2);
        });
    },
};
