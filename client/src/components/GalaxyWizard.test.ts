import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import GalaxyWizard from "./GalaxyWizard.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

const TRUNCATION_NOTICE = '[data-description="galaxy wizard truncation notice"]';
const ANALYZE_BUTTON = '[data-description="galaxy wizard analyze button"]';

function mountWizard() {
    return mount(GalaxyWizard as object, {
        propsData: {
            jobId: "job_id",
            query: "Traceback: something went wrong",
            context: "tool_error",
        },
        localVue,
    });
}

function mockErrorAnalysis(metadata: Record<string, unknown>) {
    server.use(
        http.post("/api/ai/agents/error-analysis", ({ response }) => {
            return response(200).json({
                content: "The tool ran out of memory.",
                confidence: "high",
                agent_type: "error_analysis",
                suggestions: [],
                metadata,
            });
        }),
    );
}

describe("GalaxyWizard", () => {
    it("warns that only part of an oversized error log was analyzed", async () => {
        mockErrorAnalysis({ query_truncated: true, original_query_length: 32768 });
        const wrapper = mountWizard();

        await wrapper.find(ANALYZE_BUTTON).trigger("click");
        await flushPromises();

        const notice = wrapper.find(TRUNCATION_NOTICE);
        expect(notice.exists()).toBe(true);
        // Match the runtime's own grouping rather than a hardcoded "32,768" -- the
        // component uses toLocaleString and vitest doesn't pin a locale.
        expect(notice.text()).toContain(`${(32768).toLocaleString()} characters`);
        expect(notice.text()).toContain("beginning and the end");
        expect(notice.text()).toContain("at least");
        // The diagnosis is still shown -- truncation is a caveat, not a failure.
        expect(wrapper.find('[data-description="galaxy wizard response"]').text()).toContain("ran out of memory");
    });

    it("does not caveat a diagnosis that never happened", async () => {
        // A truncated query whose inference call then failed: warning the user that
        // "the diagnosis may have missed something" next to "unable to reach the
        // service" describes an analysis that was never produced.
        mockErrorAnalysis({ query_truncated: true, original_query_length: 32768, error: "Service unavailable" });
        const wrapper = mountWizard();

        await wrapper.find(ANALYZE_BUTTON).trigger("click");
        await flushPromises();

        expect(wrapper.find(TRUNCATION_NOTICE).exists()).toBe(false);
    });

    it("stays quiet when the error log fit within the limit", async () => {
        mockErrorAnalysis({});
        const wrapper = mountWizard();

        await wrapper.find(ANALYZE_BUTTON).trigger("click");
        await flushPromises();

        expect(wrapper.find(TRUNCATION_NOTICE).exists()).toBe(false);
        expect(wrapper.find('[data-description="galaxy wizard response"]').text()).toContain("ran out of memory");
    });

    it("still warns when the original length is missing from the response", async () => {
        mockErrorAnalysis({ query_truncated: true });
        const wrapper = mountWizard();

        await wrapper.find(ANALYZE_BUTTON).trigger("click");
        await flushPromises();

        const notice = wrapper.find(TRUNCATION_NOTICE);
        expect(notice.exists()).toBe(true);
        expect(notice.text()).toContain("too much error output");
    });
});
