import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, waitFor, within } from "storybook/test";

import { configurationHandler } from "@/api/client/__mocks__/http";
import { toolBoxState, withToolBoxState } from "@/components/Panels/test_fixtures";
import { defaultActivities } from "@/stores/activitySetup";

import {
    ACTIVITY_SETTINGS_SCOPE,
    activitySettingsHandlers,
    activitySettingsState,
    DATASET_BOOKMARK,
    withActivitySettingsState,
} from "./test_fixtures";

import ActivitySettings from "./ActivitySettings.vue";

const meta = {
    title: "ActivityBar/ActivitySettings",
    component: ActivitySettings,
    decorators: [withToolBoxState, withActivitySettingsState],
    args: { activityBarId: ACTIVITY_SETTINGS_SCOPE, query: "" },
    afterEach: async ({ canvasElement, args }) => {
        await waitFor(
            () => {
                const canvas = within(canvasElement);
                if (args.query === "unmatched activity") {
                    expect(canvas.getByText("No matching activities found.")).toBeVisible();
                } else {
                    expect(
                        canvas.getByText(args.query ? "RNA-seq counts" : "Histories", { exact: true }),
                    ).toBeVisible();
                }
            },
            { timeout: 5000 },
        );
    },
    parameters: {
        ...toolBoxState({ tools: [], toolSections: { default: {} } }),
        msw: {
            handlers: {
                configuration: configurationHandler({ interactivetools_enable: true, llm_api_configured: true }),
                customTools: activitySettingsHandlers.deniedTools,
            },
        },
    },
} satisfies Meta<typeof ActivitySettings>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Optional built-in activities offered by a fully configured instance. */
export const BuiltInActivities: Story = {};

/** The saved workflow shortcut is hidden; settings can make it visible again. */
export const HiddenWorkflowShortcut: Story = {
    parameters: {
        ...activitySettingsState({
            activities: defaultActivities.map((activity) => ({
                ...activity,
                visible: activity.id === "workflows" ? false : activity.visible,
            })),
        }),
    },
};

/** Dragging a history dataset into the bar creates a removable bookmark. */
export const DatasetBookmark: Story = {
    parameters: { ...activitySettingsState({ activities: [...defaultActivities, DATASET_BOOKMARK] }) },
};

export const FilteredBookmark: Story = {
    args: { query: "RNA-seq" },
    parameters: { ...activitySettingsState({ activities: [...defaultActivities, DATASET_BOOKMARK] }) },
};

export const NoMatchingActivities: Story = { args: { query: "unmatched activity" } };

/** A registered user with the user-tool-execute role can open Custom Tools. */
export const CustomToolsPermitted: Story = {
    parameters: { msw: { handlers: { customTools: activitySettingsHandlers.permittedTools } } },
};

/** This instance offers neither interactive tools nor the GalaxyAI assistant. */
export const BasicInstance: Story = {
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ interactivetools_enable: false, llm_api_configured: false }),
                customTools: activitySettingsHandlers.permittedTools,
            },
        },
    },
};
