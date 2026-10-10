import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { h } from "vue";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import toolPanel from "@/components/ToolsView/testData/toolsListInPanel.json";
import { useConfigStore } from "@/stores/configurationStore";

import InstallationSettings from "./InstallationSettings.vue";

/** Galaxy's defaults: install every kind of dependency. */
const DEPENDENCY_SETTINGS = {
    install_tool_dependencies: true,
    install_repository_dependencies: true,
    install_resolver_dependencies: true,
};

/**
 * InstallationSettings reads the dependency settings once, when created, from a config store
 * the app has already loaded. Load it before the story renders.
 */
const withLoadedConfig: Decorator = (story) => ({
    setup() {
        useConfigStore().setConfiguration(DEPENDENCY_SETTINGS);
    },
    render: () => h(story()),
});

/** Answers the shed tool configs installed tools can be added to. */
function shedToolConfigs(...filenames: string[]) {
    return http.get("/api/configuration/dynamic_tool_confs", ({ response }) =>
        response(200).json(filenames.map((filename) => ({ config_filename: filename, tool_path: "../shed_tools" }))),
    );
}

const meta = {
    title: "Toolshed/RepositoryDetails/InstallationSettings",
    component: InstallationSettings,
    decorators: [withLoadedConfig],
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler(DEPENDENCY_SETTINGS),
                shedToolConfigs: shedToolConfigs("shed_tool_conf.xml"),
            },
        },
    },
    args: {
        repo: {
            name: "bwa",
            owner: "devteam",
            description: "Wrapper for the BWA short read aligner",
            long_description: "BWA maps low-divergent sequences against a large reference genome.",
        },
        changesetRevision: "3fe632431b68",
        toolshedUrl: "https://toolshed.g2.bx.psu.edu/",
        requiresPanel: true,
        currentPanel: toolPanel,
    },
} satisfies Meta<typeof InstallationSettings>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The repository has tools, so the dialog offers the panel's sections to put them in. */
export const WithToolPanel: Story = {};

/** Nothing to show in the tool panel (e.g. only data managers), so no section to pick. */
export const WithoutToolPanel: Story = { args: { requiresPanel: false } };

/** With more than one shed tool config, the advanced settings (collapsed at first) ask which one gets the tools. */
export const SeveralToolConfigs: Story = {
    parameters: {
        msw: { handlers: { shedToolConfigs: shedToolConfigs("shed_tool_conf.xml", "custom_shed_tool_conf.xml") } },
    },
};
