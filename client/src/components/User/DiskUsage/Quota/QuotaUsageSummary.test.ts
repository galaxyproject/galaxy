import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as QuotaUsageSummaryStories from "./QuotaUsageSummary.stories";

import QuotaUsageSummary from "./QuotaUsageSummary.vue";

const stories = composeStories(QuotaUsageSummaryStories);
const mountStory = useStoryMount();

describe("QuotaUsageSummary", () => {
    it("exposes the sum of the finite quotas, excluding the unlimited source", () => {
        const summary = mountStory(stories.MixedQuotas).findComponent(QuotaUsageSummary);
        const finiteQuotasTotalBytes = 654846535 + 68468436;
        expect(summary.vm.totalQuotaInBytes).toBe(finiteQuotasTotalBytes);
    });
});
