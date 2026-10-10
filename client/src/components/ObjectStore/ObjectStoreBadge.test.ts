import { getLocalVue } from "@tests/vitest/helpers";
import { advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";
import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "This is a test message for the badge.";

async function mountBadge(badge: ObjectStoreBadgeType) {
    return mount(ObjectStoreBadge as object, {
        props: { badge },
        global: localVue,
        attachTo: document.body,
    });
}

// The popover relocates out of the wrapper, so it's queried off the document.
function getTooltip() {
    return document.body.querySelector(".popover")?.textContent;
}

describe("ObjectStoreBadge", () => {
    afterEach(() => {
        document.body.innerHTML = "";
    });

    it("should render a valid badge for more_secure type", async () => {
        await mountBadge({ type: "more_secure", message: TEST_MESSAGE, source: "admin" });

        const tooltip = getTooltip();

        expect(tooltip).toContain(TEST_MESSAGE);
        expect(tooltip).toContain(MESSAGES.more_secure);
    });

    it("should render a valid badge for less_secure type", async () => {
        await mountBadge({ type: "less_secure", message: TEST_MESSAGE, source: "admin" });

        const tooltip = getTooltip();

        expect(tooltip).toContain(TEST_MESSAGE);
        expect(tooltip).toContain(MESSAGES.less_secure);
    });

    it("should gracefully handle unspecified/null badge messages", async () => {
        await mountBadge({ type: "more_secure", message: null, source: "admin" });

        const tooltip = getTooltip();

        expect(tooltip).toContain("This storage has been marked as more secure by the Galaxy administrator.");
        expect(tooltip).toContain(MESSAGES.more_secure);
    });
});

enableAutoUnmount(afterEach);

describe("ObjectStoreBadge popover", () => {
    afterEach(() => {
        vi.useRealTimers();
        document.body.innerHTML = "";
    });

    async function hoverBadge(message: string | null, interactive?: boolean) {
        vi.useFakeTimers();
        const wrapper = mount(ObjectStoreBadge, {
            props: { badge: { type: "short_term", message, source: "admin" }, interactive },
            global: localVue,
            attachTo: document.body,
        });
        const trigger = wrapper.get(".object-store-badge-wrapper");
        await trigger.trigger("mouseenter");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        const popover = document.body.querySelector(".popover") as HTMLElement;
        return { trigger, popover };
    }

    it("shows the admin message as its own paragraph, with Markdown links you can reach", async () => {
        const { trigger, popover } = await hoverBadge(
            "Read our **policy** on the [Archive Tier Storage](https://example.org/archive) page.",
        );
        expect(trigger.element.tagName).toBe("BUTTON");
        expect(trigger.attributes("aria-label")).toBe(MESSAGES.short_term);
        expect(trigger.attributes("aria-haspopup")).toBe("dialog");
        expect(trigger.attributes("aria-controls")).toBe(popover.id);
        expect(popover.getAttribute("role")).toBe("dialog");
        expect(popover.getAttribute("aria-label")).toBe(MESSAGES.short_term);
        const paragraphs = Array.from(popover.querySelectorAll("p")).map((p) => p.textContent);
        expect(paragraphs).toEqual([MESSAGES.short_term, "Read our policy on the Archive Tier Storage page."]);
        expect(popover.textContent).not.toContain("<p>");
        expect(popover.querySelector("strong")?.textContent).toBe("policy");
        expect(popover.querySelector("a")?.getAttribute("href")).toBe("https://example.org/archive");
    });

    it("shows only the stock sentence, as a tooltip, when there is no admin message", async () => {
        const { trigger, popover } = await hoverBadge(null);
        expect(trigger.element.tagName).toBe("BUTTON");
        expect(popover.getAttribute("role")).toBe("tooltip");
        expect(trigger.attributes("aria-describedby")).toBe(popover.id);
        const paragraphs = Array.from(popover.querySelectorAll("p")).map((p) => p.textContent);
        expect(paragraphs).toEqual([MESSAGES.short_term]);
    });

    it("uses a hover-only tooltip and an unfocusable trigger when not interactive", async () => {
        const { trigger, popover } = await hoverBadge("The data stored here is purged after a month.", false);
        expect(trigger.element.tagName).toBe("SPAN");
        expect(trigger.attributes("tabindex")).toBeUndefined();
        expect(trigger.attributes("aria-label")).toBe(MESSAGES.short_term);
        expect(popover.getAttribute("role")).toBe("tooltip");
        expect(trigger.attributes("aria-describedby")).toBe(popover.id);
        expect(popover.textContent).toContain("The data stored here is purged after a month.");
    });
});
