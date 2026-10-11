import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withGalaxyInstance } from "@tests/test-data/galaxyInstance";

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
    parameters: { msw: { handlers: { installedRepositories: installedRepositories([BOWTIE2, FASTP]) } } },
};

/** Every repository is from the main Tool Shed, so there's no Tool Shed column. */
export const FromOneToolShed: Story = {
    parameters: { msw: { handlers: { installedRepositories: installedRepositories([BOWTIE2, FASTQC]) } } },
};
