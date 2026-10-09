import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeFileSource } from "@tests/test-data/fileSources";

import { http } from "@/api/client/__mocks__/http";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

import HistoryExportWizard from "./HistoryExportWizard.vue";

const posixSource = getFakeFileSource({
    id: "test-posix-source",
    type: "posix",
    label: "TestSource",
    doc: "For testing",
    writable: true,
    browsable: true,
    requires_roles: undefined,
    requires_groups: undefined,
    uri_root: "gxfiles://test-posix-source",
});

const zenodo = getFakeFileSource({
    id: "zenodo",
    type: "rdm",
    label: "Zenodo",
    doc: "For testing",
    writable: true,
    browsable: true,
    uri_root: "zenodo://",
});

const userZenodo = getFakeFileSource({
    id: "998c5bba-b18f-4223-9c93-0f36fa2fdae8",
    type: "zenodo",
    label: "My Zenodo",
    doc: "My integration with Zenodo",
    browsable: true,
    writable: true,
    requires_roles: null,
    requires_groups: null,
    url: "https://zenodo.org/",
    supports: { pagination: true, search: true, sorting: false },
    uri_root: "gxuserfiles://998c5bba-b18f-4223-9c93-0f36fa2fdae8",
});

/** The file sources the user can export to. */
function fileSources(plugins: BrowsableFilesSourcePlugin[]) {
    return {
        msw: {
            handlers: {
                fileSources: http.get("/api/remote_files/plugins", ({ response }) => response(200).json(plugins)),
            },
        },
    };
}

const meta = {
    title: "History/Export/HistoryExportWizard",
    component: HistoryExportWizard,
    args: { historyId: "fake-history-id", historyName: "Test History", isBusy: false },
    parameters: fileSources([]),
} satisfies Meta<typeof HistoryExportWizard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const DownloadOnly: Story = {};

export const WithRemoteFileSource: Story = { parameters: fileSources([posixSource]) };

export const WithZenodo: Story = { parameters: fileSources([zenodo]) };

export const WithUserAndDefaultZenodo: Story = { parameters: fileSources([zenodo, userZenodo]) };
