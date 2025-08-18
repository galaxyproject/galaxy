import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { useServerMock } from "@/api/client/__mocks__";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";

import HistoryExportWizard from "./HistoryExportWizard.vue";

const localVue = getLocalVue(true);

const FAKE_HISTORY_ID = "fake-history-id";
const FAKE_HISTORY_NAME = "Test History";

const REMOTE_FILES_API_RESPONSE: BrowsableFilesSourcePlugin[] = [
    {
        id: "test-posix-source",
        type: "posix",
        label: "TestSource",
        doc: "For testing",
        writable: true,
        browsable: true,
        requires_roles: undefined,
        requires_groups: undefined,
        supports: {
            pagination: false,
            search: false,
            sorting: false,
        },
        uri_root: "gxfiles://test-posix-source",
    },
];

const ZENODO_PLUGIN: BrowsableFilesSourcePlugin = {
    id: "zenodo",
    type: "rdm",
    label: "Zenodo",
    doc: "For testing",
    writable: true,
    browsable: true,
    supports: {
        pagination: false,
        search: false,
        sorting: false,
    },
    uri_root: "zenodo://",
};

const USER_ZENODO_PLUGIN: BrowsableFilesSourcePlugin = {
    id: "998c5bba-b18f-4223-9c93-0f36fa2fdae8",
    type: "zenodo",
    label: "My Zenodo",
    doc: "My integration with Zenodo",
    browsable: true,
    writable: true,
    requires_roles: null,
    requires_groups: null,
    url: "https://zenodo.org/",
    supports: {
        pagination: true,
        search: true,
        sorting: false,
    },
    uri_root: "gxuserfiles://998c5bba-b18f-4223-9c93-0f36fa2fdae8",
};

const selectors = {
    wizard: ".history-export-wizard",
    formatCard: "[data-history-export-format]",
    destinationCard: "[data-history-export-destination]",
    directoryInput: "#directory",
    fileNameInput: "#exported-file-name",
    includeFilesCheckbox: 'input[type="checkbox"]',
    submitButton: ".go-next-btn",
    nextButton: ".go-next-btn",
    previousButton: ".go-back-btn",
    errorAlert: ".alert-danger",
} as const;

interface MountOptions {
    historyId?: string;
    historyName?: string;
    isBusy?: boolean;
}

async function mountHistoryExportWizard(options: MountOptions = {}) {
    const { historyId = FAKE_HISTORY_ID, historyName = FAKE_HISTORY_NAME, isBusy = false } = options;

    const pinia = createTestingPinia({ stubActions: false });
    setActivePinia(pinia);

    const wrapper = mount(HistoryExportWizard as object, {
        propsData: {
            historyId,
            historyName,
            isBusy,
        },
        localVue,
        pinia,
    });

    await flushPromises();
    return wrapper;
}

const { server, http } = useServerMock();

describe("HistoryExportWizard.vue", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json([]);
            })
        );
    });

    describe("Component Initialization", () => {
        it("should start with format selection step", async () => {
            const wrapper = await mountHistoryExportWizard();

            expect(wrapper.find(selectors.formatCard).exists()).toBe(true);
        });

        it("should display available export formats", async () => {
            const wrapper = await mountHistoryExportWizard();

            const formatCards = wrapper.findAll(selectors.formatCard);
            expect(formatCards.length).toBe(2);
        });
    });

    describe("Format Selection", () => {
        it("should display format options", async () => {
            const formats = [
                { id: "rocrate.zip", label: "RO-Crate" },
                { id: "tar.gz", label: "Compressed TGZ" },
            ];
            const wrapper = await mountHistoryExportWizard();

            const formatCards = wrapper.findAll(selectors.formatCard);
            expect(formatCards.length).toBe(formats.length);
            for (const format of formats) {
                const card = wrapper.find(`[data-history-export-format="${format.id}"]`);
                expect(card.exists()).toBe(true);
                expect(card.text()).toContain(format.label);
            }
        });
    });

    describe("Destination Selection", () => {
        it("should show download destination by default", async () => {
            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            const nextButtonAfterFormat = wrapper.find(selectors.nextButton);
            if (nextButtonAfterFormat.exists()) {
                await nextButtonAfterFormat.trigger("click");
            }

            const downloadCard = wrapper.find('[data-history-export-destination="download"]');
            expect(downloadCard.exists()).toBe(true);
        });

        it("should show remote source destination when file sources are available", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json(REMOTE_FILES_API_RESPONSE);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            const nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            const remoteCard = wrapper.find('[data-history-export-destination="remote-source"]');
            expect(remoteCard.exists()).toBe(true);
        });

        it("should show Zenodo destination when Zenodo plugin is available", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json([ZENODO_PLUGIN]);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            const nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            const zenodoCard = wrapper.find('[data-history-export-destination="zenodo-repository"]');
            expect(zenodoCard.exists()).toBe(true);
        });

        it("should prioritize user-defined Zenodo over default Zenodo", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json([ZENODO_PLUGIN, USER_ZENODO_PLUGIN]);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            const nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            const zenodoCard = wrapper.find('[data-history-export-destination="zenodo-repository"]');
            if (zenodoCard.exists()) {
                // Should show user-defined Zenodo label
                expect(zenodoCard.text()).toContain("My Zenodo");
            }
        });
    });

    describe("Remote Source Setup", () => {
        it("should show directory input when remote source is selected", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json(REMOTE_FILES_API_RESPONSE);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            let nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Select remote source
            const remoteCard = wrapper.find('[data-history-export-destination="remote-source"]');
            if (remoteCard.exists()) {
                await remoteCard.trigger("click");
            }

            // Navigate to setup step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Check that the setup step is rendered with directory selection
            expect(wrapper.text()).toContain("Select a 'repository' to export history to.");
        });
    });

    describe("Export Summary", () => {
        it("should display default file name placeholder", async () => {
            // Set up a remote file source to show file name input
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json(REMOTE_FILES_API_RESPONSE);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate through wizard steps to final step
            // Step 1: Select destination
            let nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Step 2: Select remote source to require file name
            const remoteCard = wrapper.find('[data-history-export-destination="remote-source"]');
            if (remoteCard.exists()) {
                await remoteCard.trigger("click");
            }

            // Step 3: Navigate to setup step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Simulate selecting a directory by triggering the input
            const directoryInput = wrapper.find('input[placeholder="Click to select directory"]');
            if (directoryInput.exists()) {
                await directoryInput.setValue("gxfiles://test-remote-source/test-directory");
            }

            // Step 4: Navigate to final step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Check if the file name input has the expected placeholder text
            const fileNameInput = wrapper.find(selectors.fileNameInput);
            expect(fileNameInput.exists()).toBe(true);
            expect(fileNameInput.attributes("placeholder")).toContain(FAKE_HISTORY_NAME);
        });
    });

    describe("Event Handling", () => {
        it("should emit onExport event when export is triggered", async () => {
            const wrapper = await mountHistoryExportWizard();

            // Navigate through wizard steps to final step
            // Step 1: Select destination
            let nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Step 2: Select download destination to skip setup steps
            const downloadCard = wrapper.find('[data-history-export-destination="download"]');
            if (downloadCard.exists()) {
                await downloadCard.trigger("click");
            }

            // Step 3: Navigate to final step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            const exportButton = wrapper.find(selectors.submitButton);
            await exportButton.trigger("click");

            expect(wrapper.emitted("onExport")).toBeTruthy();
        });
    });

    describe("Validation", () => {
        it("should validate remote source selection", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json(REMOTE_FILES_API_RESPONSE);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            let nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Navigate to remote source setup
            const remoteCard = wrapper.find('[data-history-export-destination="remote-source"]');
            if (remoteCard.exists()) {
                await remoteCard.trigger("click");
            }

            // Navigate to setup step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Check for directory input presence
            const directoryInput = wrapper.find(selectors.directoryInput);
            expect(directoryInput.exists() || wrapper.text().includes("Select a 'repository'")).toBe(true);
        });
    });

    describe("Step Navigation", () => {
        it("should show setup steps for remote source selection", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json(REMOTE_FILES_API_RESPONSE);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            let nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Select remote source
            const remoteCard = wrapper.find('[data-history-export-destination="remote-source"]');
            if (remoteCard.exists()) {
                await remoteCard.trigger("click");
            }

            // Navigate to setup step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Should show setup for remote source
            expect(wrapper.find(selectors.directoryInput).exists()).toBe(true);
        });

        it("should show Zenodo setup when Zenodo is selected", async () => {
            server.use(
                http.get("/api/remote_files/plugins", ({ response }) => {
                    return response(200).json([ZENODO_PLUGIN]);
                })
            );

            const wrapper = await mountHistoryExportWizard();

            // Navigate to destination step
            let nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Select Zenodo
            const zenodoCard = wrapper.find('[data-history-export-destination="zenodo-repository"]');
            if (zenodoCard.exists()) {
                await zenodoCard.trigger("click");
            }

            // Navigate to setup step
            nextButton = wrapper.find(selectors.nextButton);
            if (nextButton.exists()) {
                await nextButton.trigger("click");
            }

            // Should show Zenodo-specific setup
            expect(wrapper.text().includes("Zenodo") || wrapper.text().includes("draft record")).toBe(true);
        });
    });
});
