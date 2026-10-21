import { getLocalVue } from "@tests/vitest/helpers";
import { advanceTooltipHoverDelay } from "@tests/vitest/tooltipTestUtils";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import purify from "dompurify";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import type { ObjectStoreBadgeType } from "@/api/objectStores.templates";
import { MESSAGES } from "@/components/ObjectStore/badgeMessages";
import { vGTooltip } from "@/directives/vGTooltip";
import { DEFAULT_TOOLTIP_HOVER_DELAY_MS } from "@/utils/tooltipTiming";

import ObjectStoreBadge from "./ObjectStoreBadge.vue";

const localVue = getLocalVue(true);

const TEST_MESSAGE = "This is a test message for the badge.";
const LINKED_MESSAGE = "Read our **policy** on the [Archive Tier Storage](https://example.org/archive) page.";
const LINKED_TEXT = "Read our policy on the Archive Tier Storage page.";

enableAutoUnmount(afterEach);

describe("ObjectStoreBadge", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        // DOMPurify misbehaves under happy-dom, so it passes content through, like the global sanitizeHtml mock.
        vi.spyOn(purify, "sanitize").mockImplementation((html) => String(html));
    });

    afterEach(() => {
        vi.useRealTimers();
        vi.restoreAllMocks();
        document.body.innerHTML = "";
    });

    function mountBadge(badge: ObjectStoreBadgeType, interactive?: boolean) {
        return mount(ObjectStoreBadge, {
            props: { badge, interactive },
            global: { ...localVue, directives: { "g-tooltip": vGTooltip } },
            attachTo: document.body,
        });
    }

    function getTrigger(wrapper: ReturnType<typeof mountBadge>) {
        return wrapper.get(".object-store-badge-wrapper");
    }

    // The popover relocates, and the tooltip is added, at the end of the page.
    async function hoverBadge(badge: ObjectStoreBadgeType, interactive?: boolean) {
        const wrapper = mountBadge(badge, interactive);
        await nextTick();
        await getTrigger(wrapper).trigger("mouseenter");
        await advanceTooltipHoverDelay(DEFAULT_TOOLTIP_HOVER_DELAY_MS);
        const shown = document.body.querySelector<HTMLElement>(".popover, .g-tooltip-d")!;
        return { wrapper, trigger: getTrigger(wrapper), shown };
    }

    function paragraphs(element: HTMLElement) {
        return Array.from(element.querySelectorAll("p")).map((p) => p.textContent);
    }

    it("exposes the badge meaning and administrator message without relying on hover", async () => {
        const wrapper = mountBadge({ type: "more_secure", message: TEST_MESSAGE, source: "admin" }, false);

        const graphic = wrapper.get('[role="img"]');
        expect(graphic.attributes("aria-label")).toBe(`${MESSAGES.more_secure} ${TEST_MESSAGE}`);
        expect(graphic.findAll("svg").every((icon) => icon.attributes("aria-hidden") === "true")).toBe(true);
    });

    it("should render a valid badge for more_secure type", async () => {
        const { shown } = await hoverBadge({ type: "more_secure", message: TEST_MESSAGE, source: "admin" });
        expect(shown.textContent).toContain(TEST_MESSAGE);
        expect(shown.textContent).toContain(MESSAGES.more_secure);
    });

    it("should render a valid badge for less_secure type", async () => {
        const { shown } = await hoverBadge({ type: "less_secure", message: TEST_MESSAGE, source: "admin" });
        expect(shown.textContent).toContain(TEST_MESSAGE);
        expect(shown.textContent).toContain(MESSAGES.less_secure);
    });

    it("should gracefully handle unspecified/null badge messages", async () => {
        const { shown } = await hoverBadge({ type: "more_secure", message: null, source: "admin" });
        expect(shown.textContent).toContain("This storage has been marked as more secure by the Galaxy administrator.");
        expect(shown.textContent).toContain(MESSAGES.more_secure);
    });

    it("shows the admin message as its own paragraph, with Markdown links you can tab to", async () => {
        const { trigger, shown } = await hoverBadge({ type: "short_term", message: LINKED_MESSAGE, source: "admin" });
        expect(trigger.element.tagName).toBe("BUTTON");
        expect(trigger.attributes("aria-label")).toBe(MESSAGES.short_term);
        expect(trigger.attributes("aria-haspopup")).toBe("dialog");
        expect(trigger.attributes("aria-controls")).toBe(shown.id);
        expect(trigger.attributes("aria-describedby")).toBeUndefined();
        expect(shown.getAttribute("role")).toBe("dialog");
        expect(shown.getAttribute("aria-label")).toBe(MESSAGES.short_term);
        expect(paragraphs(shown)).toEqual([MESSAGES.short_term, LINKED_TEXT]);
        expect(shown.textContent).not.toContain("<p>");
        expect(shown.querySelector("strong")?.textContent).toBe("policy");
        const link = shown.querySelector("a")!;
        expect(link.getAttribute("href")).toBe("https://example.org/archive");

        (trigger.element as HTMLElement).focus();
        const tab = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
        trigger.element.dispatchEvent(tab);
        expect(tab.defaultPrevented).toBe(true);
        expect(document.activeElement).toBe(link);
    });

    it("shows only the stock sentence in a tooltip, without a Tab stop, when there is no admin message", async () => {
        const { trigger, shown } = await hoverBadge({ type: "short_term", message: null, source: "admin" });
        expect(trigger.element.tagName).toBe("SPAN");
        expect(trigger.attributes("role")).toBe("img");
        expect(trigger.attributes("tabindex")).toBeUndefined();
        expect(trigger.attributes("aria-haspopup")).toBeUndefined();
        expect(trigger.attributes("aria-label")).toBe(MESSAGES.short_term);
        expect(shown.getAttribute("role")).toBe("tooltip");
        expect(trigger.attributes("aria-describedby")).toBe(shown.id);
        expect(paragraphs(shown)).toEqual([MESSAGES.short_term]);
        expect(document.body.querySelector(".popover")).toBeNull();
    });

    it("shows a linked message in a tooltip that closes on leaving the badge when not interactive", async () => {
        const { trigger, shown } = await hoverBadge(
            { type: "short_term", message: LINKED_MESSAGE, source: "admin" },
            false,
        );
        expect(trigger.element.tagName).toBe("SPAN");
        expect(trigger.attributes("tabindex")).toBeUndefined();
        expect(trigger.attributes("aria-haspopup")).toBeUndefined();
        expect(trigger.attributes("aria-label")).toBe(`${MESSAGES.short_term} ${LINKED_TEXT}`);
        expect(shown.getAttribute("role")).toBe("tooltip");
        expect(paragraphs(shown)).toEqual([MESSAGES.short_term, LINKED_TEXT]);
        expect(shown.querySelector("a")?.getAttribute("href")).toBe("https://example.org/archive");
        expect(document.body.querySelector(".popover")).toBeNull();

        // Unlike a popover, it isn't kept open by moving onto it, so it can't outlive an enclosing popover.
        await trigger.trigger("mouseleave");
        expect(shown.isConnected).toBe(false);
    });

    // ObjectStoreBadges keys badges by position, and a relocated dataset's storage info is replaced in place.
    it("switches between popover and tooltip when a reused badge gains or loses its message", async () => {
        const withMessage: ObjectStoreBadgeType = { type: "short_term", message: LINKED_MESSAGE, source: "admin" };
        const wrapper = mountBadge(withMessage);
        await nextTick();
        expect(getTrigger(wrapper).attributes("aria-haspopup")).toBe("dialog");

        await wrapper.setProps({ badge: { ...withMessage, message: null } });
        await nextTick();
        let trigger = getTrigger(wrapper);
        expect(trigger.element.tagName).toBe("SPAN");
        expect(trigger.attributes("aria-haspopup")).toBeUndefined();
        expect(trigger.attributes("aria-controls")).toBeUndefined();
        expect(trigger.attributes("aria-label")).toBe(MESSAGES.short_term);
        expect(document.body.querySelector(".popover")).toBeNull();

        await wrapper.setProps({ badge: withMessage });
        await nextTick();
        trigger = getTrigger(wrapper);
        const popover = document.body.querySelector(".popover")!;
        expect(trigger.element.tagName).toBe("BUTTON");
        expect(trigger.attributes("aria-haspopup")).toBe("dialog");
        expect(trigger.attributes("aria-controls")).toBe(popover.id);
        expect(trigger.attributes("aria-describedby")).toBeUndefined();
        expect(popover.getAttribute("role")).toBe("dialog");
    });
});
