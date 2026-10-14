import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { expect, waitFor, within } from "storybook/test";

import { ensureDefined } from "@/utils/assertions";
import { escapeRegExp } from "@/utils/regExp";

import { interactiveToolsHandlers, RUNNING_TOOLS } from "./test_fixtures";
import originalToolsData from "./testData/testInteractiveToolsResponse.json";

import InteractiveTools from "./InteractiveTools.vue";

const meta = {
    title: "InteractiveTools/InteractiveTools",
    component: InteractiveTools,
    decorators: [withCurrentUser()],
    parameters: { msw: { handlers: interactiveToolsHandlers() } },
} satisfies Meta<typeof InteractiveTools>;
export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];
const runningNames = RUNNING_TOOLS.map((tool) => tool.name);

function sessionName(name: string) {
    // GLink includes its action tooltip in the accessible name. Match that
    // supplementary instruction or the session name on its own.
    return new RegExp(`^${escapeRegExp(name)}(?: Open Interactive Tool)?$`);
}

function toolRow(context: PlayContext, name: string) {
    return within(ensureDefined(context.canvas.getByRole("button", { name: sessionName(name) }).closest("tr")));
}

async function readRunningTools(context: PlayContext, names: string[] = runningNames) {
    await expect(
        await context.canvas.findByRole("button", { name: sessionName(names[0]!) }, { timeout: 5000 }),
    ).toBeVisible();
    for (const name of names) {
        await expect(context.canvas.getByRole("button", { name: sessionName(name) })).toBeVisible();
        await expect(context.canvas.getByText(name, { exact: true })).toBeVisible();
        await expect(toolRow(context, name).getByText("Running", { exact: true })).toBeVisible();
        await expect(toolRow(context, name).getByRole("link")).toBeVisible();
    }
}

/** Running sessions offer inline navigation, a new tab, and a stop button. */
export const RunningTools: Story = {
    play: async (context) => {
        await context.step("Read both running sessions and their external access controls", async () => {
            await readRunningTools(context);
        });
    },
};

/** A starting session has not published its external access target yet. */
export const StartingTool: Story = {
    play: async (context) => {
        await context.step("Read a starting session without an external access target", async () => {
            const name = "Starting JupyterLab notebook";
            await expect(
                await context.canvas.findByRole("button", { name: sessionName(name) }, { timeout: 5000 }),
            ).toBeVisible();
            await expect(context.canvas.getByText(name, { exact: true })).toBeVisible();
            await expect(toolRow(context, name).getByText("Starting", { exact: true })).toBeVisible();
            await expect(toolRow(context, name).queryByRole("link")).not.toBeInTheDocument();
        });
    },
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

const originalTools = originalToolsData.map((tool) => ({ ...tool, model_class: "InteractiveToolEntryPoint" as const }));

/** The original sessions remain readable with their full names. */
export const ReadsOriginalSessions: Story = {
    parameters: { msw: { handlers: interactiveToolsHandlers(originalTools) } },
    play: async (context) => {
        await context.step("Read the original Jupyter and AskOmics session names and Running states", async () => {
            await readRunningTools(
                context,
                originalTools.map((tool) => tool.name),
            );
            const table = within(context.canvas.getByRole("table"));
            await expect(context.canvas.getByRole("table")).toBeVisible();
            const rows = table.getAllByRole("row").filter((row) => within(row).queryAllByRole("cell").length > 0);
            await expect(rows).toHaveLength(2);
            const inlineControls = originalTools.flatMap((tool) => {
                const namedControl = table.getByRole("button", { name: sessionName(tool.name) });
                return within(ensureDefined(namedControl.closest("td"))).getAllByRole("button");
            });
            await expect(inlineControls).toHaveLength(2);
            await expect(table.getAllByRole("link")).toHaveLength(2);
            const first = originalTools[0]!;
            const external = toolRow(context, first.name).getByRole("link");
            await expect(external).toBeVisible();
            await expect(external).toHaveAttribute("href", first.target);
            await expect(external).toHaveAttribute("target", "_blank");
        });
    },
};

/** A query narrows the owner-rendered rows and can be cleared after no match. */
export const FiltersSessions: Story = {
    play: async (context) => {
        const { canvas, userEvent } = context;
        await context.step("Read both sessions before filtering", async () => {
            await readRunningTools(context);
        });
        const input = canvas.getByRole("textbox");
        await context.step("Match Jupyter with a padded uppercase query", async () => {
            await userEvent.type(input, "  JUPYTER  ");
            await waitFor(() =>
                expect(canvas.queryByRole("button", { name: sessionName(runningNames[1]!) })).not.toBeInTheDocument(),
            );
            await expect(canvas.getByRole("button", { name: sessionName(runningNames[0]!) })).toBeVisible();
        });
        await context.step("Read an unmatched query and return to the complete list", async () => {
            await userEvent.clear(input);
            await readRunningTools(context);
            await userEvent.type(input, "not-a-tool");
            const query = await canvas.findByText("not-a-tool", { exact: true });
            await expect(query).toBeVisible();
            await expect(query.parentElement).toHaveTextContent(/^No matching entries found for: not-a-tool\s*\.$/);
            for (const name of runningNames) {
                await expect(canvas.queryByRole("button", { name: sessionName(name) })).not.toBeInTheDocument();
            }
            await userEvent.clear(input);
            await readRunningTools(context);
        });
    },
};

/** Stopping each session removes its row and finally reveals the owner empty state. */
export const StopsSessions: Story = {
    play: async (context) => {
        const { canvas, userEvent } = context;
        await context.step("Read both sessions before stopping either", async () => {
            await readRunningTools(context);
        });
        await context.step("Stop Jupyter and retain the RStudio session", async () => {
            await userEvent.click(
                toolRow(context, runningNames[0]!).getByRole("button", { name: "Stop this interactive tool" }),
            );
            await waitFor(() =>
                expect(canvas.queryByRole("button", { name: sessionName(runningNames[0]!) })).not.toBeInTheDocument(),
            );
            await expect(canvas.getByRole("button", { name: sessionName(runningNames[1]!) })).toBeVisible();
        });
        await context.step("Stop RStudio and read that no active sessions remain", async () => {
            await userEvent.click(
                toolRow(context, runningNames[1]!).getByRole("button", { name: "Stop this interactive tool" }),
            );
            await expect(
                await canvas.findByText("You do not have active interactive tools yet", { exact: true }),
            ).toBeVisible();
            for (const name of runningNames) {
                await expect(canvas.queryByRole("button", { name: sessionName(name) })).not.toBeInTheDocument();
            }
        });
    },
};
