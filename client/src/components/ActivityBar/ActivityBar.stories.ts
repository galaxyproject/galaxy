import type { Meta, StoryObj } from "@storybook/vue3-vite";

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

/** Tools, running interactive tools and workflows are available in this instance. */
export const InteractiveToolsEnabled: Story = {};

/** The instance disables interactive tools, but preserves their saved position in the bar. */
export const InteractiveToolsDisabled: Story = {
    parameters: {
        msw: { handlers: { configuration: configurationHandler({ interactivetools_enable: false }) } },
    },
};
