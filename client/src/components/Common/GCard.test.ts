import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, h, ref } from "vue";

import { sanitizeHtml } from "@/directives/sanitizeHtml";

import GCard from "./GCard.vue";

const { resizeCallbacks } = vi.hoisted(() => ({ resizeCallbacks: [] as Array<() => void> }));

vi.mock("@vueuse/core", async (importOriginal) => {
    const actual = await importOriginal<object>();
    return {
        ...actual,
        useResizeObserver: vi.fn((_target: unknown, callback: () => void) => {
            resizeCallbacks.push(callback);
            return { isSupported: { value: true }, stop: vi.fn() };
        }),
    };
});

const localVue = getLocalVue();

function setWidth(element: Element, property: "clientWidth" | "offsetWidth", value: number) {
    Object.defineProperty(element, property, { configurable: true, value });
}

function mountCard(propsData: object, slots: Record<string, string> = {}) {
    return mount(GCard as object, {
        propsData: { id: "card", title: "Card", ...propsData },
        slots,
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
        stubs: { FontAwesomeIcon: true },
    });
}

describe("GCard", () => {
    it("renders a full description as markdown through v-sanitize-html with the links profile", () => {
        vi.mocked(sanitizeHtml).mockClear();
        mountCard({
            description: "Some **bold** text, a [link](https://example.org) and <b>raw</b>",
            fullDescription: true,
        });

        const [html, profile] = vi.mocked(sanitizeHtml).mock.calls[0]!;
        expect(profile).toBe("links");
        expect(html).toContain("<strong>bold</strong>");
        expect(html).toContain('href="https://example.org" target="_blank"');
        expect(html).toContain("&lt;b&gt;raw&lt;/b&gt;");
    });

    it("allows clicking actions that only navigate", async () => {
        const handler = vi.fn();
        const wrapper = mountCard({
            secondaryActions: [
                { id: "download", label: "Download", title: "Download", href: "/download" },
                { id: "copy", label: "Copy", title: "Copy", handler },
            ],
            primaryActions: [{ id: "edit", label: "Edit", title: "Edit", href: "/edit" }],
        });
        await wrapper.find("#g-card-action-download-card").trigger("click");
        await wrapper.find("#g-card-action-edit-card").trigger("click");
        expect(handler).not.toHaveBeenCalled();
        await wrapper.find("#g-card-action-copy-card").trigger("click");
        expect(handler).toHaveBeenCalledOnce();
    });

    describe("keyboard", () => {
        it.each([" ", "Enter"])("clicks a clickable card on %j", async (key) => {
            const wrapper = mountCard({ clickable: true });
            await wrapper.trigger("keydown", { key });
            expect(wrapper.emitted("click")).toHaveLength(1);
        });

        it("does not click a card that is not clickable", async () => {
            const wrapper = mountCard({ selectable: true });
            await wrapper.trigger("keydown", { key: " " });
            expect(wrapper.emitted("click")).toBeUndefined();
        });

        it.each([" ", "Enter"])("leaves %j on the select checkbox to the checkbox", async (key) => {
            const wrapper = mountCard({ clickable: true, selectable: true });
            const checkbox = wrapper.get("input#g-card-select-card");

            await checkbox.trigger("keydown", { key });
            expect(wrapper.emitted("click")).toBeUndefined();

            await checkbox.setValue(true);
            expect(wrapper.emitted("select")).toHaveLength(1);
        });
    });

    describe("select checkbox", () => {
        const paths: Array<[string, (input: HTMLInputElement) => void]> = [
            ["a click on the box", (input) => input.click()],
            ["a click on its label", (input) => input.closest("label")!.click()],
            [
                "Space",
                (input) => {
                    input.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
                    input.click();
                    input.dispatchEvent(new KeyboardEvent("keyup", { key: " ", bubbles: true }));
                },
            ],
        ];

        const mounted: Array<{ unmount: () => void }> = [];
        afterEach(() => mounted.splice(0).forEach((wrapper) => wrapper.unmount()));

        // The box only fires change when connected, as in the browser.
        function mountToggleConsumer() {
            const selected = ref(false);
            const toggle = () => (selected.value = !selected.value);
            const Consumer = defineComponent({
                setup: () => () =>
                    h(GCard, {
                        id: "card",
                        title: "Card",
                        clickable: true,
                        selectable: true,
                        selected: selected.value,
                        onSelect: toggle,
                        onClick: toggle,
                    }),
            });
            const wrapper = mount(Consumer as object, {
                attachTo: document.body,
                localVue,
                pinia: createTestingPinia({ createSpy: vi.fn }),
                stubs: { FontAwesomeIcon: true },
            });
            mounted.push(wrapper);
            return { card: wrapper.findComponent(GCard), selected, wrapper };
        }

        it.each(paths)("selects without clicking the card on %s", async (_name, activate) => {
            const { card, selected, wrapper } = mountToggleConsumer();
            activate(card.get("input#g-card-select-card").element as HTMLInputElement);
            await wrapper.vm.$nextTick();

            expect(card.emitted("click")).toBeUndefined();
            expect(card.emitted("select")).toHaveLength(1);
            expect(selected.value).toBe(true);
        });

        it("still clicks a clickable card outside the checkbox", async () => {
            const wrapper = mountCard({ clickable: true, selectable: true });
            await wrapper.trigger("click");

            expect(wrapper.emitted("click")).toHaveLength(1);
            expect(wrapper.emitted("select")).toBeUndefined();
        });

        it.each([
            ["not clickable", { selectable: true }],
            ["disabled", { clickable: true, disabled: true, selectable: true }],
        ])("does not click a card that is %s", async (_name, props) => {
            const wrapper = mountCard(props);
            await wrapper.trigger("click");

            expect(wrapper.emitted("click")).toBeUndefined();
        });
    });

    describe("header", () => {
        function mountHeader() {
            return mountCard({
                badges: [{ id: "count", label: "3 items", title: "View items", to: "/items" }],
                canRenameTitle: true,
                extraActions: [{ id: "delete", label: "Delete", title: "Delete", handler: vi.fn() }],
                indicators: [{ id: "published", label: "Published", title: "Published", handler: vi.fn() }],
                selectable: true,
                showBookmark: true,
                titleNLines: 2,
            });
        }

        it("keeps the title, the badges and the bookmark and menu as separate groups of the header row", () => {
            const header = mountHeader().find("#g-card-card-header");
            const badges = header.find(".g-card-header-badges");
            const actions = header.find(".g-card-header-actions");

            for (const group of [header.find(".g-card-title-section"), badges, actions]) {
                expect(group.element.parentElement).toBe(header.element);
            }
            for (const id of ["badges", "indicators"]) {
                expect(badges.find(`#g-card-${id}-card`).exists()).toBe(true);
            }
            expect(actions.classes()).toContain("flex-shrink-0");
            for (const id of ["bookmark-add", "extra-actions"]) {
                expect(actions.find(`#g-card-${id}-card`).exists()).toBe(true);
            }
            expect(actions.find("#g-card-badges-card").exists()).toBe(false);
        });

        it("renders the header controls in reading order", () => {
            const header = mountHeader().find("#g-card-card-header");
            const expected = [
                "g-card-select-card",
                "g-card-title-card",
                "g-card-rename-card",
                "g-card-badges-card",
                "g-card-indicators-card",
                "g-card-bookmark-add-card",
                "g-card-extra-actions-card",
            ];
            const ids = Array.from(header.element.querySelectorAll("[id]"), (el) => el.id).filter((id) =>
                expected.includes(id),
            );

            expect(ids).toEqual(expected);
        });

        it("emits select from a named selection checkbox", async () => {
            const wrapper = mountHeader();
            const checkbox = wrapper.get("input#g-card-select-card");

            expect(checkbox.attributes("aria-label")).toBe("Select for bulk actions");
            await checkbox.setValue(true);

            expect(wrapper.emitted("select")).toHaveLength(1);
        });

        it("sizes the first row for header controls only when the card has them", () => {
            const withControls = mountHeader().find("#g-card-card-header .g-card-title-section");
            const withoutControls = mountCard({ badges: [{ id: "state", label: "ok", title: "State" }] }).find(
                "#g-card-card-header .g-card-title-section",
            );

            expect(withControls.classes()).toContain("g-card-header-line");
            expect(withoutControls.classes()).not.toContain("g-card-header-line");
        });

        it("omits the badges and actions groups when the card has nothing to show in them", () => {
            const header = mountCard({
                badges: [{ id: "hidden", label: "Hidden", title: "Hidden", visible: false }],
                extraActions: [{ id: "hidden", label: "Hidden", title: "Hidden", visible: false }],
            }).find("#g-card-card-header");

            expect(header.find(".g-card-header-badges").exists()).toBe(false);
            expect(header.find("#g-card-badges-card").exists()).toBe(false);
            expect(header.find("#g-card-indicators-card").exists()).toBe(false);
            expect(header.find(".g-card-header-actions").exists()).toBe(false);
        });

        it("renders only the badge or indicator container that has content", () => {
            const header = mountCard({
                indicators: [{ id: "published", label: "Published", title: "Published", handler: vi.fn() }],
            }).find("#g-card-card-header");

            expect(header.find(".g-card-header-badges").exists()).toBe(true);
            expect(header.find("#g-card-badges-card").exists()).toBe(false);
            expect(header.find("#g-card-indicators-card").exists()).toBe(true);
        });

        it("renders the badges group for slot content", () => {
            const header = mountCard({}, { badges: "<span id='slot-badge'>Slot badge</span>" }).find(
                "#g-card-card-header",
            );

            expect(header.find(".g-card-header-badges #slot-badge").exists()).toBe(true);
        });

        beforeEach(() => {
            vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
                callback(0);
                return 0;
            });
            vi.stubGlobal("cancelAnimationFrame", vi.fn());
        });

        function mountStackedHeader() {
            resizeCallbacks.length = 0;
            const wrapper = mountHeader();
            const header = wrapper.find("#g-card-card-header");
            const measure = resizeCallbacks.at(-1)!;
            setWidth(header.element, "clientWidth", 300);
            setWidth(header.find(".g-card-header-select").element, "offsetWidth", 20);
            setWidth(header.find("#g-card-badges-card").element, "offsetWidth", 150);
            setWidth(header.find("#g-card-indicators-card").element, "offsetWidth", 30);
            setWidth(header.find(".g-card-header-actions").element, "offsetWidth", 40);
            measure();
            return { wrapper, header, measure };
        }

        it("keeps the badges on the first row until the header has been measured", () => {
            const header = mountHeader().find("#g-card-card-header");

            expect(header.classes()).toContain("g-card-header-inline");
        });

        it("moves the badges to their own row when they do not fit beside a 10rem title", async () => {
            const { wrapper, header, measure } = mountStackedHeader();
            await wrapper.vm.$nextTick();
            expect(header.classes()).toContain("g-card-header-stacked");

            setWidth(header.element, "clientWidth", 600);
            measure();
            await wrapper.vm.$nextTick();
            expect(header.classes()).toContain("g-card-header-inline");
        });

        it("keeps the last layout while the header is hidden", async () => {
            const { wrapper, header, measure } = mountStackedHeader();
            setWidth(header.element, "clientWidth", 0);
            measure();
            await wrapper.vm.$nextTick();

            expect(header.classes()).toContain("g-card-header-stacked");
        });

        it("returns to one row when the badges are removed", async () => {
            const { wrapper, header } = mountStackedHeader();
            await wrapper.vm.$nextTick();
            await wrapper.setProps({ badges: [], indicators: [] } as never);
            await wrapper.vm.$nextTick();

            expect(header.classes()).toContain("g-card-header-inline");
        });

        it("measures again when the header controls change", async () => {
            const widths: Array<[string, number]> = [
                ["#g-card-badges-card", 120],
                [".g-card-header-actions", 40],
            ];
            const offsetWidth = vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockImplementation(function (
                this: HTMLElement,
            ) {
                return widths.find(([selector]) => this.matches(selector))?.[1] ?? 0;
            });
            try {
                resizeCallbacks.length = 0;
                const wrapper = mountCard({ badges: [{ id: "state", label: "ok", title: "State" }] });
                const header = wrapper.find("#g-card-card-header");
                setWidth(header.element, "clientWidth", 300);
                resizeCallbacks.at(-1)!();
                await wrapper.vm.$nextTick();
                expect(header.classes()).toContain("g-card-header-inline");

                await wrapper.setProps({ showBookmark: true } as never);
                await wrapper.vm.$nextTick();
                expect(header.classes()).toContain("g-card-header-column");
            } finally {
                offsetWidth.mockRestore();
            }
        });

        it("clamps the title when titleNLines is set", () => {
            const title = mountHeader().find("#g-card-title-text-card");

            expect(title.classes()).toContain("g-card-title-truncate");
        });
    });

    describe("clickable title tooltip", () => {
        const NAME = "Differential expression of liver samples, batch 2, trimmed and aligned to GRCh38";

        function setHeight(element: Element, scrollHeight: number, clientHeight: number) {
            Object.defineProperty(element, "scrollHeight", { configurable: true, value: scrollHeight });
            Object.defineProperty(element, "clientHeight", { configurable: true, value: clientHeight });
        }

        async function mountTitle(scrollHeight: number, clientHeight: number, hint = "Click to preview workflow") {
            resizeCallbacks.length = 0;
            const wrapper = mountCard({ title: { label: NAME, title: hint, handler: vi.fn() }, titleNLines: 2 });
            setHeight(wrapper.find("#g-card-title-link-card").element, scrollHeight, clientHeight);
            resizeCallbacks.forEach((measure) => measure());
            await wrapper.vm.$nextTick();
            return wrapper;
        }

        it("shows the click hint, then the full name, when the title is cut off", async () => {
            const tooltip = (await mountTitle(60, 40)).find("#g-card-title-tooltip-card");

            const hint = tooltip.find(".g-card-title-tooltip-hint");
            const name = tooltip.find(".g-card-title-tooltip-name");
            expect(hint.text()).toBe("Click to preview workflow");
            expect(name.text()).toBe(NAME);
            expect(hint.element.compareDocumentPosition(name.element)).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
        });

        it("shows only the click hint when the whole title fits", async () => {
            const tooltip = (await mountTitle(40, 40)).find("#g-card-title-tooltip-card");

            expect(tooltip.find(".g-card-title-tooltip-hint").text()).toBe("Click to preview workflow");
            expect(tooltip.find(".g-card-title-tooltip-name").exists()).toBe(false);
        });

        it("does not repeat the name when the hint already is the name", async () => {
            const tooltip = (await mountTitle(60, 40, NAME)).find("#g-card-title-tooltip-card");

            expect(tooltip.find(".g-card-title-tooltip-hint").text()).toBe(NAME);
            expect(tooltip.find(".g-card-title-tooltip-name").exists()).toBe(false);
        });

        it("keeps the full name as the link's accessible name and the tooltip as its description", async () => {
            const wrapper = await mountTitle(60, 40);
            const link = wrapper.find("#g-card-title-link-card");
            const tooltip = wrapper.find("#g-card-title-tooltip-card");

            expect(link.text()).toBe(NAME);
            expect(link.attributes("aria-label")).toBeUndefined();
            expect(link.attributes("title")).toBeUndefined();
            expect(link.attributes("aria-describedby")).toBe("g-card-title-tooltip-card");
            expect(tooltip.find(".g-card-title-tooltip-hint").attributes("aria-hidden")).toBeUndefined();
            expect(tooltip.find(".g-card-title-tooltip-name").attributes("aria-hidden")).toBe("true");
        });

        it("shows the tooltip when the link gets keyboard focus", async () => {
            const wrapper = await mountTitle(60, 40);

            await wrapper.find("#g-card-title-link-card").trigger("focus");

            expect(wrapper.find("#g-card-title-tooltip-card").attributes("data-show")).toBe("true");
        });
    });

    it.each(["titleBadges", "badges"])("makes clickable %s reachable and usable from the keyboard", async (prop) => {
        const handler = vi.fn();
        const wrapper = mountCard({
            [prop]: [
                { id: "clickable", label: "Clickable", title: "Clickable", handler },
                { id: "static", label: "Static", title: "Static" },
            ],
        });

        const clickable = wrapper.find("#g-card-badge-clickable-card");
        expect(clickable.attributes("role")).toBe("button");
        expect(clickable.attributes("tabindex")).toBe("0");
        await clickable.trigger("keydown.enter");
        await clickable.trigger("keydown.space");
        expect(handler).toHaveBeenCalledTimes(2);
        // Otherwise Space also scrolls the page.
        const space = new KeyboardEvent("keydown", { key: " ", cancelable: true, bubbles: true });
        clickable.element.dispatchEvent(space);
        expect(space.defaultPrevented).toBe(true);

        const inert = wrapper.find("#g-card-badge-static-card");
        expect(inert.attributes("role")).toBeUndefined();
        expect(inert.attributes("tabindex")).toBeUndefined();
    });

    it.each(["titleBadges", "badges"])("leaves Enter alone on link %s so they still navigate", (prop) => {
        const wrapper = mountCard({
            [prop]: [{ id: "link", label: "Link", title: "Link", href: "https://example.org" }],
        });

        const event = new KeyboardEvent("keydown", { key: "Enter", cancelable: true, bubbles: true });
        wrapper.find("#g-card-badge-link-card").element.dispatchEvent(event);

        expect(event.defaultPrevented).toBe(false);
    });
});
