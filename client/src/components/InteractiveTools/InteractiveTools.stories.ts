import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";

import { interactiveToolsHandlers, RUNNING_TOOLS } from "./test_fixtures";

import InteractiveTools from "./InteractiveTools.vue";

const meta = {
    title: "InteractiveTools/InteractiveTools",
    component: InteractiveTools,
    decorators: [withCurrentUser()],
    parameters: { msw: { handlers: interactiveToolsHandlers() } },
} satisfies Meta<typeof InteractiveTools>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Running sessions offer inline navigation, a new tab, and a stop button. */
export const RunningTools: Story = {};

/** A starting session has not published its external access target yet. */
export const StartingTool: Story = {
    parameters: {
        msw: {
            handlers: interactiveToolsHandlers([
                { ...RUNNING_TOOLS[0]!, name: "Starting JupyterLab notebook", active: false, target: undefined },
            ]),
        },
    },
};

/** No interactive tool jobs are currently running. */
export const NoRunningTools: Story = { parameters: { msw: { handlers: interactiveToolsHandlers([]) } } };
