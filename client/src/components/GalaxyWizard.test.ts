import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import GalaxyWizard from "./GalaxyWizard.vue";

const { server, http } = useServerMock();

const ANALYZE_BUTTON = '[data-description="galaxy wizard analyze button"]';

describe("GalaxyWizard", () => {
    it("renders the analysis through v-sanitize-html with the links profile", async () => {
        server.use(
            http.post("/api/ai/agents/error-analysis", ({ response }) =>
                response(200).json({
                    content: "The tool ran out of memory.",
                    confidence: "high",
                    agent_type: "error_analysis",
                    suggestions: [],
                    metadata: {},
                }),
            ),
        );
        vi.mocked(sanitizeHtml).mockClear();
        const wrapper = mount(GalaxyWizard as object, {
            propsData: { jobId: "job_id", query: "Traceback: something went wrong", context: "tool_error" },
            localVue: getLocalVue(),
        });

        await wrapper.find(ANALYZE_BUTTON).trigger("click");
        await flushPromises();

        expect(sanitizeHtml).toHaveBeenLastCalledWith("<p>The tool ran out of memory.</p>\n", "links");
        expect(wrapper.find('[data-description="galaxy wizard response"]').text()).toContain("ran out of memory");
    });
});
