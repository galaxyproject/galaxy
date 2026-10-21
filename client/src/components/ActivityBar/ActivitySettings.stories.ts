import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import { h, ref } from "vue";

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

export const ShowsAndHidesWorkflowShortcut: Story = {
    ...HiddenWorkflowShortcut,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const title = await canvas.findByText("Workflows", { exact: true }, { timeout: 5000 });
        const row = title.closest("button");
        if (!row) {
            throw new Error("The workflow activity row must be a button");
        }
        const workflow = within(row);
        await step("Show the saved workflow shortcut", async () => {
            await userEvent.click(workflow.getByRole("button", { description: "Show in Activity Bar" }));
            await waitFor(() => {
                expect(workflow.getByRole("button", { description: "Hide in Activity Bar" })).toBeVisible();
                expect(workflow.queryByRole("button", { description: "Show in Activity Bar" })).not.toBeInTheDocument();
            });
            expect(canvas.getByText("Workflows", { exact: true })).toBeVisible();
        });
        await step("Hide the shortcut again without removing the activity", async () => {
            await userEvent.click(workflow.getByRole("button", { description: "Hide in Activity Bar" }));
            await waitFor(() => {
                expect(workflow.getByRole("button", { description: "Show in Activity Bar" })).toBeVisible();
                expect(workflow.queryByRole("button", { description: "Hide in Activity Bar" })).not.toBeInTheDocument();
            });
            expect(canvas.getByText("Workflows", { exact: true })).toBeVisible();
        });
    },
};

export const DeletesDatasetBookmark: Story = {
    ...DatasetBookmark,
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        const title = await canvas.findByText("RNA-seq counts", { exact: true }, { timeout: 5000 });
        const row = title.closest("button");
        if (!row) {
            throw new Error("The dataset bookmark row must be a button");
        }
        await step("Remove the dataset bookmark and keep the built-in activities", async () => {
            await userEvent.click(within(row).getByRole("button", { description: "Delete Activity" }));
            await waitFor(() => {
                expect(canvas.getByText("Histories", { exact: true })).toBeVisible();
                expect(canvas.queryByText("RNA-seq counts", { exact: true })).not.toBeInTheDocument();
                expect(canvas.queryByRole("button", { description: "Delete Activity" })).not.toBeInTheDocument();
            });
        });
    },
};

export const SearchesActivities: Story = {
    ...DatasetBookmark,
    render: (args) => ({
        setup() {
            const query = ref(args.query);
            return () =>
                h("div", [
                    h("label", { for: "activity-settings-search" }, "Search activities"),
                    h("input", {
                        id: "activity-settings-search",
                        type: "search",
                        value: query.value,
                        onInput: (event: Event) => {
                            query.value = (event.target as HTMLInputElement).value;
                        },
                    }),
                    h(ActivitySettings, { ...args, query: query.value }),
                ]);
        },
    }),
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await canvas.findByText("RNA-seq counts", { exact: true }, { timeout: 5000 });
        const search = canvas.getByRole("searchbox", { name: "Search activities" });
        await step("Search by the bookmark title without matching case", async () => {
            await userEvent.type(search, "rNa-SeQ");
            await waitFor(() => {
                expect(canvas.getByText("RNA-seq counts", { exact: true })).toBeVisible();
                expect(canvas.queryByText("Histories", { exact: true })).not.toBeInTheDocument();
            });
        });
        await step("Search the bookmark description", async () => {
            await userEvent.clear(search);
            await userEvent.type(search, "this dataset");
            await waitFor(() => {
                expect(canvas.getByText("RNA-seq counts", { exact: true })).toBeVisible();
                expect(canvas.getByText("Displays this dataset.", { exact: true })).toBeVisible();
                expect(canvas.queryByText("Histories", { exact: true })).not.toBeInTheDocument();
            });
        });
        await step("Show an empty result then clear the search", async () => {
            await userEvent.clear(search);
            await userEvent.type(search, "unmatched activity");
            await waitFor(() => {
                expect(canvas.getByText("No matching activities found.", { exact: true })).toBeVisible();
                expect(canvas.queryByText("RNA-seq counts", { exact: true })).not.toBeInTheDocument();
            });
            await userEvent.clear(search);
            await waitFor(() => {
                expect(canvas.getByText("Histories", { exact: true })).toBeVisible();
                expect(canvas.getByText("RNA-seq counts", { exact: true })).toBeVisible();
                expect(canvas.queryByText("No matching activities found.", { exact: true })).not.toBeInTheDocument();
            });
        });
    },
};
