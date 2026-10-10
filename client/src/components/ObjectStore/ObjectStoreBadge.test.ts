// @vitest-environment jsdom
import { getLocalVue } from "@tests/vitest/helpers";
import { advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";
import { vGTooltip } from "@/directives/vGTooltip";
import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "This is a test message for the badge.";

async function mountBadge(badge: ObjectStoreBadgeType) {
    const wrapper = mount(ObjectStoreBadge as object, {
        props: { badge },
        global: localVue,
    });

    return wrapper;
}

async function getTooltip(wrapper: VueWrapper) {
    const badge = wrapper.find(".object-store-badge-wrapper");

    const content = document.createElement("div");
    content.innerHTML = badge.attributes("data-mock-directive") || "";
    return content.textContent;
}

describe("ObjectStoreBadge", () => {
    it("should render a valid badge for more_secure type", async () => {
        const wrapper = await mountBadge({ type: "more_secure", message: TEST_MESSAGE, source: "admin" });

        const tooltip = await getTooltip(wrapper);

        expect(tooltip).toContain(TEST_MESSAGE);
        expect(tooltip).toContain(MESSAGES.more_secure);
    });

    it("should render a valid badge for less_secure type", async () => {
        const wrapper = await mountBadge({ type: "less_secure", message: TEST_MESSAGE, source: "admin" });

        const tooltip = await getTooltip(wrapper);

        expect(tooltip).toContain(TEST_MESSAGE);
        expect(tooltip).toContain(MESSAGES.less_secure);
    });

    it("should gracefully handle unspecified/null badge messages", async () => {
        const wrapper = await mountBadge({ type: "more_secure", message: null, source: "admin" });

        const tooltip = await getTooltip(wrapper);

        expect(tooltip).toContain("This storage has been marked as more secure by the Galaxy administrator.");
        expect(tooltip).toContain(MESSAGES.more_secure);
    });
});

enableAutoUnmount(afterEach);

describe("ObjectStoreBadge rendered tooltip", () => {
    afterEach(() => {
        vi.useRealTimers();
        document.body.innerHTML = "";
    });

    it.each([
        ["The data stored here is purged after a month.", "The data stored here is purged after a month."],
        [
            "Read our **policy** on the [Archive Tier Storage](https://example.org/archive) page.",
            "Read our policy on the Archive Tier Storage page.",
        ],
        [null, ""],
    ])("renders the admin message and names the badge without tags: %s", async (message, text) => {
        vi.useFakeTimers();
        const wrapper = mount(ObjectStoreBadge, {
            props: { badge: { type: "short_term", message, source: "admin" } },
            global: { ...localVue, directives: { ...localVue.directives, "g-tooltip": vGTooltip } },
            attachTo: document.body,
        });
        const badge = wrapper.get(".object-store-badge-wrapper");
        await badge.trigger("mouseenter");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        const tooltip = document.querySelector(".g-tooltip-d-inner");
        expect(tooltip?.textContent).toContain(MESSAGES.short_term);
        expect(tooltip?.textContent).toContain(text);
        expect(tooltip?.textContent).not.toContain("<p>");
        expect(tooltip?.querySelectorAll("p")).toHaveLength(message ? 2 : 1);
        expect(badge.attributes("aria-label")).toBe([MESSAGES.short_term, text].filter(Boolean).join(" "));
        if (message?.includes("[Archive")) {
            expect(tooltip?.querySelector("strong")?.textContent).toBe("policy");
            expect(tooltip?.querySelector("a")?.getAttribute("href")).toBe("https://example.org/archive");
        }
        wrapper.unmount();
    });
});
