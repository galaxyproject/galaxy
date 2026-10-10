import { composeStories } from "@storybook/vue3-vite";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as QuotaUsageSummaryStories from "./QuotaUsageSummary.stories";

import QuotaUsageBar from "./QuotaUsageBar.vue";
import QuotaUsageSummary from "./QuotaUsageSummary.vue";

const stories = composeStories(QuotaUsageSummaryStories);
const mountStory = useStoryMount();

function mountSummary(story: StoryOf<typeof stories>) {
    return mountStory(story).findComponent(QuotaUsageSummary);
}

const mixedQuotas = stories.MixedQuotas.args.quotaUsages!;

describe("QuotaUsageSummary", () => {
    it("sums finite quotas and excludes the unlimited source", () => {
        const summary = mountSummary(stories.MixedQuotas);
        const finiteQuotasTotalBytes = 654846535 + 68468436;
        expect(summary.vm.totalQuotaInBytes).toBe(finiteQuotasTotalBytes);
        expect(summary.get("h2 b").text()).toBe("723.3 MB");
        expect(summary.get("h2").text()).toContain("of total disk quota");
    });

    it("passes each finite or unlimited quota to its bar", () => {
        const summary = mountSummary(stories.MixedQuotas);

        expect(summary.findAll(".quota-usage-bar")).toHaveLength(mixedQuotas.length);
        expect(summary.findAllComponents(QuotaUsageBar).map((bar) => bar.props("quotaUsage"))).toEqual(mixedQuotas);
    });

    it("shows unlimited total quota when every source is unlimited", () => {
        const summary = mountSummary(stories.AllUnlimited);
        expect(summary.get("h2").text()).toContain("unlimited");
    });
});
