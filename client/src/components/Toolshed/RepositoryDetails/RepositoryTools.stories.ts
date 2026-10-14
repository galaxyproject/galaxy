import type { Meta, StoryObj } from "@storybook/vue3-vite";

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

const meta = {
    title: "Toolshed/RepositoryDetails/RepositoryTools",
    component: RepositoryTools,
} satisfies Meta<typeof RepositoryTools>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A repository with one tool, so there's nothing to expand. */
export const SingleTool: Story = {
    args: {
        tools: [
            shedTool("devteam/fastqc", {
                id: "fastqc",
                name: "FastQC",
                description: "Read Quality reports",
                version: "0.74+galaxy1",
                requirements: [{ name: "fastqc", type: "package", version: "0.12.1" }],
                tool_config: "rgFastQC.xml",
            }),
        ],
    },
};

/** A repository with several tools: the first two show, and "Show more" reveals the rest. */
export const SeveralTools: Story = {
    args: {
        tools: [
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
        ],
    },
};
