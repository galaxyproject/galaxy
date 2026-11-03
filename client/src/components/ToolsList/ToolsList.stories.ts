import type { Meta, StoryObj } from "@storybook/vue3-vite";

import { toolboxHandlers, toolBoxState, toolPanelHandlers, withToolBoxState } from "@/components/Panels/test_fixtures";

import { CATALOG_TOOLS, catalogHandlers } from "./test_fixtures";

import ToolsList from "./ToolsList.vue";

const meta = {
    title: "ToolsList/ToolsList",
    component: ToolsList,
    decorators: [withToolBoxState],
    parameters: {
        ...toolBoxState({ tools: CATALOG_TOOLS }),
        msw: { handlers: { ...toolboxHandlers, ...toolPanelHandlers, ...catalogHandlers } },
    },
} satisfies Meta<typeof ToolsList>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Browse the instance's small collection-manipulation and genome-coordinate catalog. */
export const ToolCatalog: Story = {};

/** A shared link searches the curated multi-word tag, quoted in the search box. */
export const DataCleanupTools: Story = { args: { tag: ["data cleanup"] } };

/** A saved legacy section link is interpreted as a tag filter. */
export const CollectionToolsFromLegacyLink: Story = { args: { section: "collection_ops" } };
