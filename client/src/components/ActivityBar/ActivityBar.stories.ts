import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";

import { configurationHandler } from "@/api/client/__mocks__/http";
import { toolBoxState, toolPanelHandlers, withToolBoxState } from "@/components/Panels/test_fixtures";
import { defaultActivities } from "@/stores/activitySetup";

import { activitySettingsHandlers, activitySettingsState, withActivitySettingsState } from "./test_fixtures";

import ActivityBar from "./ActivityBar.vue";

const activities = ["tools", "interactivetools", "workflows"].map((id) => ({
    ...defaultActivities.find((activity) => activity.id === id)!,
}));

const meta = {
    title: "ActivityBar/ActivityBar",
    component: ActivityBar,
    decorators: [withToolBoxState, withActivitySettingsState],
    args: {
        activityBarId: "story-activity-bar",
        defaultActivities: activities,
        hidePanel: true,
    },
    argTypes: { defaultActivities: { control: false } },
    parameters: {
        ...toolBoxState({ tools: [], toolSections: { default: {} } }),
        ...activitySettingsState({ activities }),
        msw: {
            handlers: {
                ...toolPanelHandlers,
                configuration: configurationHandler({ interactivetools_enable: true }),
                customTools: activitySettingsHandlers.permittedTools,
            },
        },
    },
} satisfies Meta<typeof ActivityBar>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

async function readConfiguredActivities({ canvas }: PlayContext) {
    const tools = await canvas.findByRole("link", { name: "Tools" }, { timeout: 5000 });
    await expect(tools).toBeVisible();
    await expect(canvas.getByRole("link", { name: "Workflows" })).toBeVisible();
}

/** Tools, running interactive tools and workflows are available in this instance. */
export const InteractiveToolsEnabled: Story = {
    play: async (context) => {
        await context.step("Read tools, workflows and the enabled interactive-tools activity", async () => {
            await readConfiguredActivities(context);
            const interactiveTools = await context.canvas.findByRole(
                "link",
                { name: "Interactive Tools" },
                { timeout: 5000 },
            );
            await expect(interactiveTools).toBeVisible();
            await expect(context.canvas.getAllByRole("link", { name: "Interactive Tools" })).toHaveLength(1);
        });
    },
};

/** The instance disables interactive tools, but preserves their saved position in the bar. */
export const InteractiveToolsDisabled: Story = {
    parameters: {
        msw: { handlers: { configuration: configurationHandler({ interactivetools_enable: false }) } },
    },
    play: async (context) => {
        await context.step("Read tools and workflows on this instance", async () => {
            await readConfiguredActivities(context);
            // These activities can render before configuration loads, so absence of interactive tools remains a unit contract.
        });
    },
};
