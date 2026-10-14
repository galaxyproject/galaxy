import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";

import RepositoryTools from "./RepositoryTools.vue";

/** A tool in a revision's metadata from the Tool Shed (`RepositoryTool` in `tool_shed_client/schema`). */
interface RepositoryTool {
    description: string;
    guid: string;
    id: string;
    name: string;
    requirements: { name: string; type: string; version: string }[];
    tool_config: string;
    tool_type: string;
    version: string;
}

/** A tool of `repository` on the main Tool Shed, with the guid the Tool Shed builds from it. */
function shedTool(repository: string, tool: Omit<RepositoryTool, "guid" | "tool_type">): RepositoryTool {
    return {
        ...tool,
        guid: `toolshed.g2.bx.psu.edu/repos/${repository}/${tool.id}/${tool.version}`,
        tool_type: "default",
    };
}

const FASTQC = shedTool("devteam/fastqc", {
    id: "fastqc",
    name: "FastQC",
    description: "Read Quality reports",
    version: "0.74+galaxy1",
    requirements: [{ name: "fastqc", type: "package", version: "0.12.1" }],
    tool_config: "rgFastQC.xml",
});

const TEXT_PROCESSING_TOOLS: [RepositoryTool, RepositoryTool, RepositoryTool] = [
    shedTool("bgruening/text_processing", {
        id: "tp_cat",
        name: "Concatenate datasets",
        description: "tail-to-head",
        version: "9.5+galaxy2",
        requirements: [{ name: "coreutils", type: "package", version: "9.5" }],
        tool_config: "cat.xml",
    }),
    shedTool("bgruening/text_processing", {
        id: "tp_sed_tool",
        name: "Text reformatting",
        description: "with sed",
        version: "9.5+galaxy3",
        requirements: [{ name: "sed", type: "package", version: "4.8" }],
        tool_config: "sed.xml",
    }),
    shedTool("bgruening/text_processing", {
        id: "tp_awk_tool",
        name: "Text reformatting",
        description: "with awk",
        version: "9.5+galaxy0",
        requirements: [{ name: "gawk", type: "package", version: "5.3.0" }],
        tool_config: "awk.xml",
    }),
];

const meta = {
    title: "Toolshed/RepositoryDetails/RepositoryTools",
    component: RepositoryTools,
} satisfies Meta<typeof RepositoryTools>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Each table row's cell texts, top to bottom. */
function rowTexts({ canvas }: PlayContext) {
    return canvas.getAllByRole("row").map((row) =>
        within(row)
            .getAllByRole("cell")
            .map((cell) => cell.textContent?.trim()),
    );
}

/** A tool's row: its id, then its version. */
function toolRow(tool: RepositoryTool) {
    return [tool.id, tool.version];
}

/** A repository with one tool, so there's nothing to expand. */
export const SingleTool: Story = {
    args: { tools: [FASTQC] },
    play: async (context) => {
        const { canvas, step } = context;
        await step("See the tool's id and version as the only row", async () => {
            await expect(rowTexts(context)).toEqual([toolRow(FASTQC)]);
            await expect(canvas.getByRole("cell", { name: FASTQC.id })).toBeVisible();
        });
        await step("See nothing to show more or less of", async () => {
            await expect(canvas.queryAllByRole("button")).toHaveLength(0);
            await expect(canvas.queryAllByRole("link")).toHaveLength(0);
        });
    },
};

/** A repository with several tools: the first two show, and "Show more" reveals the rest. */
export const SeveralTools: Story = {
    args: { tools: TEXT_PROCESSING_TOOLS },
};

/** "Show more" lists every tool, and "Show less" goes back to the first two. */
export const ShowsMoreAndLess: Story = {
    args: SeveralTools.args,
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        const [firstTool, secondTool, thirdTool] = TEXT_PROCESSING_TOOLS;
        const collapsed = [toolRow(firstTool), toolRow(secondTool), ["Show more", ""]];
        await step("See the first two tools, then Show more", async () => {
            await expect(rowTexts(context)).toEqual(collapsed);
            await expect(canvas.queryByRole("cell", { name: thirdTool.id })).toBeNull();
        });
        await step("Show more, to see Show less above every tool", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Show more" }));
            await canvas.findByRole("button", { name: "Show less" });
            await expect(rowTexts(context)).toEqual([
                ["Show less", ""],
                toolRow(firstTool),
                toolRow(secondTool),
                toolRow(thirdTool),
            ]);
            await expect(canvas.getByRole("cell", { name: thirdTool.id })).toBeVisible();
            await expect(canvas.queryByRole("button", { name: "Show more" })).toBeNull();
        });
        await step("Show less, to see the first two tools again", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Show less" }));
            await canvas.findByRole("button", { name: "Show more" });
            await expect(rowTexts(context)).toEqual(collapsed);
            await expect(canvas.queryByRole("button", { name: "Show less" })).toBeNull();
        });
    },
};
