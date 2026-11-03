import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as HistoryExportWizardStories from "./HistoryExportWizard.stories";

import HistoryExportWizard from "./HistoryExportWizard.vue";

const router = createTestRouter();

const stories = composeStories(HistoryExportWizardStories);
const mountStory = useStoryMount();

async function mountWizard() {
    const root = mountStory(stories.DownloadOnly, { router });
    await flushPromises();
    return root.findComponent(HistoryExportWizard);
}

// User-facing behavior is covered by the stories' play functions.
describe("HistoryExportWizard.vue", () => {
    describe("Format Selection", () => {
        it("should display format options", async () => {
            const formats = [
                { id: "rocrate.zip", label: "RO-Crate" },
                { id: "tar.gz", label: "Compressed TGZ" },
            ];
            const wizard = await mountWizard();

            expect(wizard.findAll("[data-export-format]").length).toBe(formats.length);
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
            const wizard = await mountWizard();

            const formatCalls = vi.mocked(sanitizeHtml).mock.calls;
            expect(formatCalls.length).toBeGreaterThan(0);
            expect(formatCalls.every(([, profile]) => profile === "links")).toBe(true);

            await wizard.find(".go-next-btn").trigger("click");
            await flushPromises();

            const downloadCall = vi
                .mocked(sanitizeHtml)
                .mock.calls.find(([html]) => html?.includes("download it directly to your computer"));
            expect(downloadCall?.[1]).toBe("links");
            expect(wizard.find('[data-history-export-destination="download"]').text()).toContain(
                "download it directly to your computer",
            );
        });
    });
});
