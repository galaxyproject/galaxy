import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { withLoadedConfig } from "@tests/test-data/config";
import { withToasts } from "@tests/test-data/toasts";
import { http as mswHttp, HttpResponse } from "msw";
import { expect, waitFor } from "storybook/test";

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
