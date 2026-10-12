import type { Meta, StoryContext, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { withLoadedConfig } from "@tests/test-data/config";
import { withToasts } from "@tests/test-data/toasts";
import { http as mswHttp, HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import { configurationHandler } from "@/api/client/__mocks__/http";

import {
    EDAM_MAPPER,
    FASTQC_VERSIONS,
    TOOLBOX_PANEL,
    TOOLBOX_TOOLS,
    toolboxHandlers,
    toolBoxState,
    withToolBoxState,
} from "./test_fixtures";

import ToolBox from "./ToolBox.vue";

const meta = {
    title: "Panels/ToolBox",
    component: ToolBox,
    decorators: [withLoadedConfig, withToolBoxState, withToasts],
    args: { favoritesDefault: true, workflow: false, useSearchWorker: false },
    // Configuration and the viewer hash resolve before the toolbox can mount.
    afterEach: async ({ canvasElement }) => {
        await waitFor(() => expect(canvasElement.querySelector("input.search-query")).toBeVisible(), { timeout: 5000 });
    },
    parameters: {
        msw: {
            handlers: {
                ...toolboxHandlers,
                configuration: configurationHandler({
                    toolbox_auto_sort: true,
                    enable_notification_system: true,
                    enable_tool_installation_request_form: true,
                }),
                // Submitting the administrator request encounters a transport failure.
                installationRequest: mswHttp.post("/api/notifications", () => HttpResponse.error()),
            },
        },
    },
} satisfies Meta<typeof ToolBox>;
export default meta;
type Story = StoryObj<typeof meta>;

export const FavoriteGenomeTool: Story = {
    parameters: toolBoxState({ favorites: { tools: ["liftOver1"] } }),
};
export const NoFavorites: Story = {};
export const FavoriteAndOtherFilters: Story = {
    parameters: toolBoxState({ favorites: { tools: ["__FILTER_FAILED_DATASETS__"] } }),
};
export const FavoriteCollections: Story = {
    parameters: toolBoxState({ favorites: { tools: ["__FILTER_FAILED_DATASETS__", "__ZIP_COLLECTION__"] } }),
};
export const RecentAndFavoriteCollections: Story = {
    parameters: toolBoxState({
        favorites: { tools: ["__FILTER_FAILED_DATASETS__"] },
        recentTools: ["__ZIP_COLLECTION__", "__FILTER_EMPTY_DATASETS__"],
    }),
};
export const RecentInstalledVersions: Story = {
    parameters: toolBoxState({
        tools: [...TOOLBOX_TOOLS, ...FASTQC_VERSIONS],
        toolSections: {
            default: {
                ...TOOLBOX_PANEL,
                quality_control: {
                    model_class: "ToolSection",
                    id: "quality_control",
                    name: "Quality control",
                    tools: [FASTQC_VERSIONS[1]!.id],
                },
            },
        },
        recentTools: [FASTQC_VERSIONS[0]!.id, FASTQC_VERSIONS[1]!.id, "__FILTER_EMPTY_DATASETS__", "uninstalled-tool"],
    }),
};
export const FavoriteTags: Story = {
    parameters: toolBoxState({
        favorites: {
            tools: ["__FILTER_FAILED_DATASETS__"],
            tags: ["genome_coordinates", "data_cleanup", "missing_tag"],
        },
        recentTools: ["__ZIP_COLLECTION__"],
    }),
};
export const FavoriteCleanupTag: Story = {
    parameters: toolBoxState({ favorites: { tags: ["data_cleanup"] } }),
};
export const OrderedTagAndToolFavorites: Story = {
    parameters: toolBoxState({
        favorites: {
            tools: ["__FILTER_FAILED_DATASETS__"],
            tags: ["genome_coordinates"],
            order: [
                { object_type: "tags", object_id: "genome_coordinates" },
                { object_type: "tools", object_id: "__FILTER_FAILED_DATASETS__" },
            ],
        },
    }),
};
export const RecentCollectionAndFavoriteFilter: Story = {
    parameters: toolBoxState({
        favorites: { tools: ["__FILTER_FAILED_DATASETS__"] },
        recentTools: ["__ZIP_COLLECTION__"],
    }),
};
export const RecentOnly: Story = {
    parameters: toolBoxState({ recentTools: ["__ZIP_COLLECTION__"] }),
};
export const FavoriteEdamOperation: Story = {
    parameters: toolBoxState({
        tools: [...TOOLBOX_TOOLS, EDAM_MAPPER],
        toolSections: {
            default: {
                ...TOOLBOX_PANEL,
                mapping: { model_class: "ToolSection", id: "mapping", name: "Mapping", tools: [EDAM_MAPPER.id] },
            },
            "ontology:edam_operations": {
                operation_3198: {
                    model_class: "ToolSection",
                    id: "operation_3198",
                    name: "Sequence alignment",
                    tools: [EDAM_MAPPER.id],
                },
            },
        },
        favorites: { edam_operations: ["operation_3198"] },
    }),
};
export const InstallationRequestsAvailable: Story = {
    args: { favoritesDefault: false },
    parameters: toolBoxState({ currentPanelView: "default" }),
};
export const InstallationRequestsDisabled: Story = {
    args: { favoritesDefault: false },
    parameters: {
        ...toolBoxState({ currentPanelView: "default" }),
        msw: {
            handlers: {
                configuration: configurationHandler({
                    toolbox_auto_sort: true,
                    enable_notification_system: true,
                    enable_tool_installation_request_form: false,
                }),
            },
        },
    },
};
export const NotificationsDisabled: Story = {
    args: { favoritesDefault: false },
    parameters: {
        ...toolBoxState({ currentPanelView: "default" }),
        msw: {
            handlers: {
                configuration: configurationHandler({
                    toolbox_auto_sort: true,
                    enable_notification_system: false,
                    enable_tool_installation_request_form: true,
                }),
            },
        },
    },
};
export const AnonymousDefaultPanel: Story = {
    args: { favoritesDefault: false },
    parameters: toolBoxState({ currentPanelView: "default", user: getFakeAnonymousUser() }),
};
export const WorkflowToolbox: Story = {
    args: { favoritesDefault: false, workflow: true },
    parameters: toolBoxState({ currentPanelView: "default" }),
};

const GENOME_TOOL = "Convert genome coordinates between assemblies and genomes";
const FAILED_FILTER = "Filter failed datasets from a collection";
const EMPTY_FILTER = "Filter empty datasets from a collection";

/** Read tool links by their visible names, including each tool's description. */
async function seeTools({ canvas }: Pick<StoryContext, "canvas">, names: string[]) {
    await waitFor(
        () => {
            const shown = canvas
                .queryAllByRole("link")
                .map((link) => link.textContent?.replace(/\s+/g, " ").trim() ?? "")
                .filter((name) =>
                    /^(Convert genome coordinates|Filter failed|Filter empty|Zip Collection|Unzip Collection)/.test(
                        name,
                    ),
                );
            expect(shown).toEqual(names);
        },
        { timeout: 5000 },
    );
}

/** A search reaches tools outside the favorite view; Escape returns to the saved favorite. */
export const SearchesOutsideFavorites: Story = {
    parameters: FavoriteGenomeTool.parameters,
    play: async (context) => {
        await context.step("Start with the favorite genome tool", async () => {
            await seeTools(context, [GENOME_TOOL]);
        });
        await context.step("Search all tools for Zip", async () => {
            const search = context.canvas.getByPlaceholderText("search tools");
            await context.userEvent.type(search, "Zip");
            await seeTools(context, ["Zip Collection", "Unzip Collection"]);
        });
        await context.step("Escape clears the search and restores the favorite", async () => {
            await context.userEvent.keyboard("{Escape}");
            await seeTools(context, [GENOME_TOOL]);
            await expect(context.canvas.getByPlaceholderText("search tools")).toHaveValue("");
        });
    },
};

/** Filter the favorites explicitly and with shorthand, then collapse their mixed search results. */
export const FiltersAndCollapsesFavorites: Story = {
    parameters: FavoriteCollections.parameters,
    play: async (context) => {
        await seeTools(context, [FAILED_FILTER, "Zip Collection"]);
        const search = context.canvas.getByPlaceholderText("search tools");
        await context.step("Use explicit AND and shorthand favorite searches", async () => {
            await context.userEvent.type(search, "#favorites AND Filter");
            await seeTools(context, [FAILED_FILTER]);
            await context.userEvent.clear(search);
            await context.userEvent.type(search, "#favorites Filter");
            await seeTools(context, [FAILED_FILTER]);
            await context.userEvent.clear(search);
            await context.userEvent.type(search, "#favorites");
            await seeTools(context, [FAILED_FILTER, "Zip Collection"]);
        });
        await context.step("Collapse favorite results while retaining other matches", async () => {
            await context.userEvent.clear(search);
            await context.userEvent.type(search, "Filter");
            await seeTools(context, [FAILED_FILTER, EMPTY_FILTER]);
            const favorites = context.canvas.getByRole("button", { name: "Favorites" });
            await expect(favorites).toHaveAttribute("aria-expanded", "true");
            await context.userEvent.click(favorites);
            await seeTools(context, [EMPTY_FILTER]);
            await expect(favorites).toHaveAttribute("aria-expanded", "false");
            await context.userEvent.click(favorites);
            await seeTools(context, [FAILED_FILTER, EMPTY_FILTER]);
            await expect(favorites).toHaveAttribute("aria-expanded", "true");
        });
    },
};

/** A signed-in user can open and cancel the administrator request after finding no matching tool. */
export const OpensInstallationRequest: Story = {
    args: InstallationRequestsAvailable.args,
    parameters: InstallationRequestsAvailable.parameters,
    play: async (context) => {
        const search = await context.canvas.findByPlaceholderText("search tools", {}, { timeout: 5000 });
        await context.step("Find no matching tool", async () => {
            await context.userEvent.type(search, "xyznonexistenttool123");
            await expect(await context.canvas.findByText("No results found", {}, { timeout: 5000 })).toBeVisible();
            await expect(context.canvas.queryByRole("dialog")).not.toBeInTheDocument();
        });
        await context.step("Open the installation request and cancel it", async () => {
            await context.userEvent.click(context.canvas.getByRole("button", { name: "Request Tool Installation" }));
            // The modal title currently does not give its native dialog an accessible name.
            const dialog = await context.canvas.findByRole("dialog");
            await expect(within(dialog).getByRole("heading", { name: "Request Tool Installation" })).toBeVisible();
            await expect(within(dialog).getByText("Tool Information")).toBeVisible();
            await expect(within(dialog).getByRole("button", { name: "Submit Request" })).toHaveAttribute(
                "aria-disabled",
                "true",
            );
            await context.userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
            await waitFor(() => expect(context.canvas.queryByRole("dialog")).not.toBeInTheDocument());
            await expect(context.canvas.getByText("No results found")).toBeVisible();
        });
    },
};
