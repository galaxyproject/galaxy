import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withGalaxyInstance } from "@tests/test-data/galaxyInstance";
import { expect, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";

import { BOWTIE2, FASTP, FASTQC, type InstalledRepository, TOOL_SHED_URLS } from "../test_fixtures";

import Index from "./Index.vue";

/** Answers the list of installed repositories with `repositories`. */
function installedRepositories(repositories: InstalledRepository[]) {
    return http.get("/api/tool_shed_repositories", ({ response }) => response(200).json(repositories));
}

const meta = {
    title: "Toolshed/InstalledList/Index",
    component: Index,
    decorators: [withGalaxyInstance({ tool_shed_urls: TOOL_SHED_URLS })],
    args: { filter: "" },
} satisfies Meta<typeof Index>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Repositories from the main and test Tool Sheds, so the table names each one's Tool Shed; bowtie2 has a newer version. */
export const FromTwoToolSheds: Story = {
    play: async ({ canvas, step }) => {
        await step("Read the installed repositories and their Tool Sheds", async () => {
            const table = await canvas.findByRole("table", {}, { timeout: 5000 });
            await expect(canvas.getByText("2 repositories installed on this instance.")).toBeVisible();
            await expect(within(table).getByRole("columnheader", { name: "Tool Shed" })).toBeVisible();
            const rows = within(table).getAllByRole("row").slice(1);
            await expect(rows).toHaveLength(2);
            await expect(within(rows[0]!).getByText(BOWTIE2.name, { exact: true })).toBeVisible();
            await expect(within(rows[1]!).getByText(FASTP.name, { exact: true })).toBeVisible();
            await expect(within(rows[0]!).getByText("Newer version available!", { exact: true })).toBeVisible();
            await expect(
                within(rows[1]!).queryByText("Newer version available!", { exact: true }),
            ).not.toBeInTheDocument();
            await expect(canvas.queryByText("Loading installed repositories", { exact: true })).not.toBeInTheDocument();
        });
    },
    parameters: { msw: { handlers: { installedRepositories: installedRepositories([BOWTIE2, FASTP]) } } },
};

/** Every repository is from the main Tool Shed, so there's no Tool Shed column. */
export const FromOneToolShed: Story = {
    play: async ({ canvas, step }) => {
        await step("Read repositories from one Tool Shed without a redundant column", async () => {
            const table = await canvas.findByRole("table", {}, { timeout: 5000 });
            await expect(within(table).getByRole("columnheader", { name: "Name" })).toBeVisible();
            await expect(within(table).queryByRole("columnheader", { name: "Tool Shed" })).not.toBeInTheDocument();
            await expect(within(table).getByText(BOWTIE2.name, { exact: true })).toBeVisible();
            await expect(within(table).getByText(FASTQC.name, { exact: true })).toBeVisible();
        });
    },
    parameters: { msw: { handlers: { installedRepositories: installedRepositories([BOWTIE2, FASTQC]) } } },
};

export const ShowsAndHidesInstallationProgress: Story = {
    parameters: FromTwoToolSheds.parameters,
    play: async ({ canvas, userEvent, step }) => {
        const emptyProgress = "Currently there are no installing repositories.";
        await step("Start with installation progress hidden", async () => {
            await expect(
                await canvas.findByText("2 repositories installed on this instance.", {}, { timeout: 5000 }),
            ).toBeVisible();
            await expect(canvas.queryByText(emptyProgress, { exact: true })).not.toBeInTheDocument();
            await expect(canvas.getByRole("button", { name: "Show installation progress." })).toBeVisible();
        });
        await step("Show the current installation progress", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Show installation progress." }));
            await expect(await canvas.findByText(emptyProgress, { exact: true }, { timeout: 5000 })).toBeVisible();
            await expect(canvas.getByRole("button", { name: "Hide installation progress." })).toBeVisible();
        });
        await step("Hide installation progress again", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Hide installation progress." }));
            await expect(canvas.getByRole("button", { name: "Show installation progress." })).toBeVisible();
            await expect(canvas.queryByText(emptyProgress, { exact: true })).not.toBeInTheDocument();
        });
    },
};
