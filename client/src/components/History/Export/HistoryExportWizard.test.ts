import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as HistoryExportWizardStories from "./HistoryExportWizard.stories";

import HistoryExportWizard from "./HistoryExportWizard.vue";

const router = createTestRouter();

const stories = composeStories(HistoryExportWizardStories);
const mountStory = useStoryMount();

const selectors = {
    formatCard: "[data-export-format]",
    directoryInput: '[data-test-id="export-destination-input"]',
    fileNameInput: "#exported-file-name",
    submitButton: ".go-next-btn",
    nextButton: ".go-next-btn",
} as const;

async function mountWizard(story: StoryOf<typeof stories>) {
    const root = mountStory(story, { router });
    await flushPromises();
    return root.findComponent(HistoryExportWizard);
}

type Wizard = Awaited<ReturnType<typeof mountWizard>>;

const destinationCard = (wizard: Wizard, destination: string) =>
    wizard.find(`[data-history-export-destination="${destination}"]`);

async function next(wizard: Wizard) {
    await wizard.find(selectors.nextButton).trigger("click");
    await flushPromises();
}

/** Past the format step, picks a destination and moves on to its setup step. */
async function setUpDestination(wizard: Wizard, destination: string) {
    await next(wizard);
    await destinationCard(wizard, destination).trigger("click");
    await next(wizard);
}

describe("HistoryExportWizard.vue", () => {
    describe("Component Initialization", () => {
        it("should start with format selection step", async () => {
            const wizard = await mountWizard(stories.DownloadOnly);
            expect(wizard.find(selectors.formatCard).exists()).toBe(true);
        });

        it("should display available export formats", async () => {
            const wizard = await mountWizard(stories.DownloadOnly);
            expect(wizard.findAll(selectors.formatCard).length).toBe(2);
        });
    });

    describe("Format Selection", () => {
        it("should display format options", async () => {
            const formats = [
                { id: "rocrate.zip", label: "RO-Crate" },
                { id: "tar.gz", label: "Compressed TGZ" },
            ];
            const wizard = await mountWizard(stories.DownloadOnly);

            expect(wizard.findAll(selectors.formatCard).length).toBe(formats.length);
            for (const format of formats) {
                const card = wizard.find(`[data-export-format="${format.id}"]`);
                expect(card.exists()).toBe(true);
                expect(card.text()).toContain(format.label);
            }
        });
    });

    describe("Description rendering", () => {
        it("renders format and destination descriptions through v-sanitize-html with the links profile", async () => {
            vi.mocked(sanitizeHtml).mockClear();
            const wizard = await mountWizard(stories.DownloadOnly);

            const formatCalls = vi.mocked(sanitizeHtml).mock.calls;
            expect(formatCalls.length).toBeGreaterThan(0);
            expect(formatCalls.every(([, profile]) => profile === "links")).toBe(true);

            await next(wizard);

            const downloadCall = vi
                .mocked(sanitizeHtml)
                .mock.calls.find(([html]) => html?.includes("download it directly to your computer"));
            expect(downloadCall?.[1]).toBe("links");
            expect(destinationCard(wizard, "download").text()).toContain("download it directly to your computer");
        });
    });

    describe("Destination Selection", () => {
        it("should show download destination by default", async () => {
            const wizard = await mountWizard(stories.DownloadOnly);
            await next(wizard);
            expect(destinationCard(wizard, "download").exists()).toBe(true);
        });

        it("should show remote source destination when file sources are available", async () => {
            const wizard = await mountWizard(stories.WithRemoteFileSource);
            await next(wizard);
            expect(destinationCard(wizard, "remote-source").exists()).toBe(true);
        });

        it("should show Zenodo destination when Zenodo plugin is available", async () => {
            const wizard = await mountWizard(stories.WithZenodo);
            await next(wizard);
            expect(destinationCard(wizard, "zenodo-repository").exists()).toBe(true);
        });

        it("should prioritize user-defined Zenodo over default Zenodo", async () => {
            const wizard = await mountWizard(stories.WithUserAndDefaultZenodo);
            await next(wizard);
            expect(destinationCard(wizard, "zenodo-repository").text()).toContain("My Zenodo");
        });
    });

    describe("Remote Source Setup", () => {
        it("should show directory input when remote source is selected", async () => {
            const wizard = await mountWizard(stories.WithRemoteFileSource);
            await setUpDestination(wizard, "remote-source");
            expect(wizard.text()).toContain("Select a 'repository' to export history to.");
        });
    });

    describe("Export Summary", () => {
        it("should display default file name placeholder", async () => {
            const wizard = await mountWizard(stories.WithRemoteFileSource);
            await setUpDestination(wizard, "remote-source");

            const directoryInput = wizard.find(selectors.directoryInput);
            await directoryInput.setValue("gxfiles://test-posix-source/test-directory");
            await directoryInput.trigger("input");
            await next(wizard);

            const fileNameInput = wizard.find(selectors.fileNameInput);
            expect(fileNameInput.exists()).toBe(true);
            expect(fileNameInput.attributes("placeholder")).toContain("Test History");
        });
    });

    describe("Event Handling", () => {
        it("should emit onExport event when export is triggered", async () => {
            const wizard = await mountWizard(stories.DownloadOnly);
            await setUpDestination(wizard, "download");
            await wizard.find(selectors.submitButton).trigger("click");
            expect(wizard.emitted("onExport")).toBeTruthy();
        });
    });

    describe("Validation", () => {
        it("should validate remote source selection", async () => {
            const wizard = await mountWizard(stories.WithRemoteFileSource);
            await setUpDestination(wizard, "remote-source");
            const directoryInput = wizard.find(selectors.directoryInput);
            expect(directoryInput.exists() || wizard.text().includes("Select a 'repository'")).toBe(true);
        });
    });

    describe("Step Navigation", () => {
        it("should show setup steps for remote source selection", async () => {
            const wizard = await mountWizard(stories.WithRemoteFileSource);
            await setUpDestination(wizard, "remote-source");
            expect(wizard.find(selectors.directoryInput).exists()).toBe(true);
        });

        it("should show Zenodo setup when Zenodo is selected", async () => {
            const wizard = await mountWizard(stories.WithZenodo);
            await setUpDestination(wizard, "zenodo-repository");
            expect(wizard.text().includes("Zenodo") || wizard.text().includes("draft record")).toBe(true);
        });
    });
});
