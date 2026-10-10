import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { expect } from "storybook/test";
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

/** A server set to install no dependencies with its tools. */
const NO_DEPENDENCY_SETTINGS = {
    install_tool_dependencies: false,
    install_repository_dependencies: false,
    install_resolver_dependencies: false,
};

/** The dependency checkboxes in the advanced settings, by label. */
const DEPENDENCY_OPTIONS = [
    "Install resolvable dependencies",
    "Install repository dependencies",
    "Install tool dependencies",
];

/**
 * InstallationSettings reads the dependency settings once, when created, from a config store
 * the app has already loaded. Load the story's `dependencySettings` before it renders.
 */
const withLoadedConfig: Decorator = (story, { parameters }) => ({
    setup() {
        useConfigStore().setConfiguration(parameters.dependencySettings);
    },
    render: () => h(story()),
});

/** Story parameters for a server with these dependency settings, in the store and the API alike. */
function dependencySettings(settings: typeof DEPENDENCY_SETTINGS) {
    return { dependencySettings: settings, msw: { handlers: { configuration: configurationHandler(settings) } } };
}

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
        dependencySettings: DEPENDENCY_SETTINGS,
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
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Opens the collapsed advanced settings, where the dependency options are. */
async function openAdvancedSettings({ canvas, userEvent, step }: PlayContext) {
    await step("See no dependency options until the advanced settings are shown", async () => {
        await expect(canvas.queryAllByRole("checkbox")).toHaveLength(0);
    });
    await step("Show the advanced settings", async () => {
        await userEvent.click(await canvas.findByRole("heading", { name: "Show advanced settings" }));
        await expect(canvas.getByRole("heading", { name: "Hide advanced settings" })).toBeVisible();
    });
}

/** Each dependency option is offered, checked when the server installs that kind of dependency. */
async function expectDependencyOptions({ canvas }: PlayContext, checked: boolean) {
    await expect(canvas.getAllByRole("checkbox")).toHaveLength(DEPENDENCY_OPTIONS.length);
    for (const option of DEPENDENCY_OPTIONS) {
        const checkbox = canvas.getByRole("checkbox", { name: option });
        if (checked) {
            await expect(checkbox).toBeChecked();
        } else {
            await expect(checkbox).not.toBeChecked();
        }
    }
}

/** The repository has tools, so the dialog offers the panel's sections to put them in. */
export const WithToolPanel: Story = {
    play: async ({ args, canvas, step }) => {
        await step("See the dialog titled with the repository being installed", async () => {
            const title = await canvas.findByRole("heading", { name: `Installing '${args.repo.name}'` });
            await expect(title).toBeVisible();
        });
        await step("See its long description, owner and revision", async () => {
            await expect(canvas.getByText(args.repo.long_description)).toBeVisible();
            await expect(canvas.getByText(`${args.repo.owner} rev. ${args.changesetRevision}`)).toBeVisible();
        });
        await step("See the target section field labeled and offering the panel's sections", async () => {
            const sectionInput = canvas.getByLabelText("Target Section:");
            await expect(sectionInput).toHaveAttribute("id", "install-tool-section");
            await expect(canvas.getByRole("combobox")).toContainElement(sectionInput);
        });
    },

    // TODO a11y: button-name, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Nothing to show in the tool panel (e.g. only data managers), so no section to pick. */
export const WithoutToolPanel: Story = {
    args: { requiresPanel: false },
    // TODO a11y: button-name (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** With more than one shed tool config, the advanced settings (collapsed at first) ask which one gets the tools. */
export const SeveralToolConfigs: Story = {
    parameters: {
        // TODO a11y: button-name, label (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { shedToolConfigs: shedToolConfigs("shed_tool_conf.xml", "custom_shed_tool_conf.xml") } },
    },
};

/** The advanced settings check every dependency option, as the server's defaults install them all. */
export const ChecksEnabledDependencies: Story = {
    play: async (context) => {
        await openAdvancedSettings(context);
        await context.step("See every dependency option checked", () => expectDependencyOptions(context, true));
    },

    // TODO a11y: button-name, label (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** On a server set to install no dependencies, the advanced settings check none. */
export const UnchecksDisabledDependencies: Story = {
    parameters: {
        ...dependencySettings(NO_DEPENDENCY_SETTINGS),
        // TODO a11y: button-name, label (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: async (context) => {
        await openAdvancedSettings(context);
        await context.step("See every dependency option unchecked", () => expectDependencyOptions(context, false));
    },
};
