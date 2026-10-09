import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
});
