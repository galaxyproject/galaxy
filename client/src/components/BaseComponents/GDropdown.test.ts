import type * as FloatingUI from "@floating-ui/dom";
import { autoUpdate, computePosition } from "@floating-ui/dom";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import GDropdown from "./GDropdown.vue";
import GDropdownForm from "./GDropdownForm.vue";
import GDropdownGroup from "./GDropdownGroup.vue";
import GDropdownItem from "./GDropdownItem.vue";
import GDropdownItemButton from "./GDropdownItemButton.vue";

vi.mock("@floating-ui/dom", async (importOriginal) => {
    const actual = await importOriginal<typeof FloatingUI>();
    return { ...actual, autoUpdate: vi.fn(actual.autoUpdate), computePosition: vi.fn(actual.computePosition) };
});

const localVue = getLocalVue();
localVue.use(VueRouter);

let wrapper: Wrapper<Vue> | undefined;

function mountTemplate(template: string, methods: Record<string, () => void> = {}) {
    wrapper = mount(
        {
            components: { GDropdown, GDropdownForm, GDropdownGroup, GDropdownItem, GDropdownItemButton },
            template: `<div>${template}<button id="outside">Outside</button></div>`,
            methods,
        } as object,
        { localVue, router: new VueRouter({ mode: "history" }), attachTo: document.body },
    );
    return wrapper;
}

function mountDropdown(items: string, methods: Record<string, () => void> = {}) {
    return mountTemplate(`<GDropdown text="Menu">${items}</GDropdown>`, methods);
}

const MENU = `
    <GDropdownItem>One</GDropdownItem>
    <GDropdownItem disabled>Two</GDropdownItem>
    <GDropdownItemButton>Three</GDropdownItemButton>
    <GDropdownItemButton disabled>Four</GDropdownItemButton>
    <GDropdownItem>Five</GDropdownItem>`;

function focusedText() {
    return document.activeElement?.textContent?.trim();
}

async function press(element: Wrapper<Vue> | Element, key: string, shiftKey = false) {
    const target = "element" in element ? element.element : element;
    target.dispatchEvent(new KeyboardEvent("keydown", { key, shiftKey, bubbles: true, cancelable: true }));
    await flushPromises();
}

function isMenuOpen(wrapper: Wrapper<Vue>) {
    return wrapper.get(".dropdown-menu").classes().includes("show");
}

async function openMenu(wrapper: Wrapper<Vue>) {
    await wrapper.get(".dropdown-toggle").trigger("click");
    expect(isMenuOpen(wrapper)).toBe(true);
}

afterEach(() => {
    wrapper?.destroy();
    wrapper = undefined;
});

describe("GDropdown.vue", () => {
    describe("menu button semantics", () => {
        it("links the toggle and the menu", () => {
            const wrapper = mountDropdown(`<GDropdownItem>Action</GDropdownItem>`);
            const toggle = wrapper.get(".dropdown-toggle");
            const menu = wrapper.get(".dropdown-menu");

            expect(toggle.attributes("aria-haspopup")).toBe("menu");
            expect(toggle.attributes("aria-controls")).toBe(menu.attributes("id"));
            expect(menu.attributes("role")).toBe("menu");
            expect(menu.attributes("aria-labelledby")).toBe(toggle.attributes("id"));
            expect(wrapper.get(".dropdown-item").attributes("role")).toBe("menuitem");
        });

        it("puts aria-label on the toggle, which names the menu", () => {
            const wrapper = mountTemplate(
                `<GDropdown aria-label="Upload examples"><GDropdownItem>One</GDropdownItem></GDropdown>`,
            );

            const toggle = wrapper.get(".dropdown-toggle");
            expect(toggle.attributes("aria-label")).toBe("Upload examples");
            expect(wrapper.get(".dropdown").attributes("aria-label")).toBeUndefined();
            expect(wrapper.get(".dropdown-menu").attributes("aria-labelledby")).toBe(toggle.attributes("id"));
        });

        it("names a split menu after its main button", () => {
            const wrapper = mountTemplate(
                `<GDropdown split text="Create"><GDropdownItem>List</GDropdownItem></GDropdown>`,
            );

            const [main, toggle] = wrapper.findAll(".dropdown > button").wrappers;
            expect(main?.attributes("id")).toBeTruthy();
            expect(wrapper.get(".dropdown-menu").attributes("aria-labelledby")).toBe(main?.attributes("id"));
            expect(toggle?.text()).toBe("More options for Create");
        });

        it("reflects the open state in aria-expanded", async () => {
            const wrapper = mountDropdown(`<GDropdownItem>Action</GDropdownItem>`);
            const toggle = wrapper.get(".dropdown-toggle");

            expect(toggle.attributes("aria-expanded")).toBe("false");
            await openMenu(wrapper);
            expect(toggle.attributes("aria-expanded")).toBe("true");
        });

        it("names item groups after their header", () => {
            const wrapper = mountDropdown(`
                <GDropdownGroup header="Admins Only"><GDropdownItem>Import</GDropdownItem></GDropdownGroup>
                <GDropdownGroup><GDropdownItem>Other</GDropdownItem></GDropdownGroup>`);

            const [labelled, unlabelled] = wrapper.findAll("[role='group']").wrappers;
            const header = wrapper.get(".dropdown-header");
            expect(header.attributes("id")).toBeTruthy();
            expect(labelled?.attributes("aria-labelledby")).toBe(header.attributes("id"));
            expect(header.text()).toBe("Admins Only");
            expect(unlabelled?.attributes("aria-labelledby")).toBeUndefined();
        });

        it("does not name a group after a #header slot, which can hold a control", () => {
            const wrapper = mountDropdown(`
                <GDropdownGroup aria-label="Ontologies">
                    <template v-slot:header><input placeholder="Filter ontologies" /></template>
                    <GDropdownItem>Topic</GDropdownItem>
                </GDropdownGroup>`);

            const group = wrapper.get("[role='group']");
            expect(group.attributes("aria-labelledby")).toBeUndefined();
            expect(group.attributes("aria-label")).toBe("Ontologies");
        });
    });

    describe("positioning", () => {
        function lastPositionCall() {
            const [reference, menu, options] = vi.mocked(computePosition).mock.calls.at(-1)!;
            return {
                reference,
                menu,
                placement: options?.placement,
                middleware: options?.middleware?.map((m) => (m ? m.name : m)),
            };
        }

        it.each([
            [{}, "bottom-start"],
            [{ right: true }, "bottom-end"],
            [{ dropup: true }, "top-start"],
            [{ dropright: true }, "right-start"],
            [{ dropleft: true }, "left-start"],
        ])("places the menu for %o at %s, flipping and shifting it into view", async (props, placement) => {
            wrapper = mount(GDropdown as object, {
                localVue,
                propsData: { text: "Menu", ...props },
                attachTo: document.body,
            });
            await openMenu(wrapper);
            await flushPromises();

            const call = lastPositionCall();
            expect(call.reference).toBe(wrapper.get(".dropdown-toggle").element);
            expect(call.menu).toBe(wrapper.get(".dropdown-menu").element);
            expect(call.placement).toBe(placement);
            expect(call.middleware).toEqual(["offset", "flip", "shift"]);
        });

        it("aligns split menus and right-aligned dropups with the whole group, like BDropdown", async () => {
            wrapper = mount(GDropdown as object, {
                localVue,
                propsData: { text: "Menu", split: true },
                attachTo: document.body,
            });
            await openMenu(wrapper);
            await flushPromises();

            expect(lastPositionCall().reference).toBe(wrapper.element);
        });

        it("applies the computed coordinates and stops tracking once closed", async () => {
            const stopTracking = vi.fn();
            vi.mocked(autoUpdate).mockImplementationOnce((_reference, _floating, update) => {
                update();
                return stopTracking;
            });
            vi.mocked(computePosition).mockResolvedValueOnce({
                x: 12,
                y: 34,
                placement: "bottom-end",
                strategy: "absolute",
                middlewareData: {},
            });
            wrapper = mount(GDropdown as object, { localVue, propsData: { text: "Menu" }, attachTo: document.body });
            await openMenu(wrapper);
            await flushPromises();

            const menu = wrapper.get(".dropdown-menu").element as HTMLElement;
            expect(menu.style.left).toBe("12px");
            expect(menu.style.top).toBe("34px");

            await wrapper.get(".dropdown-toggle").trigger("click");
            expect(stopTracking).toHaveBeenCalledOnce();
        });

        it.each([
            ["ArrowDown", (toggle: Wrapper<Vue>) => press(toggle, "ArrowDown")],
            ["Enter or Space", (toggle: Wrapper<Vue>) => toggle.trigger("click")],
        ])("focuses an item opened with %s only once the menu is placed", async (_key, open) => {
            let placeMenu = () => {};
            vi.mocked(computePosition).mockReturnValueOnce(
                new Promise((resolve) => {
                    placeMenu = () =>
                        resolve({ x: 0, y: 0, placement: "top-start", strategy: "absolute", middlewareData: {} });
                }),
            );
            const wrapper = mountDropdown(MENU);
            const toggle = wrapper.get(".dropdown-toggle");
            (toggle.element as HTMLElement).focus();

            await open(toggle);
            await flushPromises();
            expect(isMenuOpen(wrapper)).toBe(true);
            expect(document.activeElement).toBe(toggle.element);

            placeMenu();
            await flushPromises();
            expect(focusedText()).toBe("One");
        });

        it("stops tracking the first open when shown, hidden and shown again in one tick", async () => {
            const [stopFirst, stopSecond] = [vi.fn(), vi.fn()];
            vi.mocked(autoUpdate)
                .mockImplementationOnce(() => stopFirst)
                .mockImplementationOnce(() => stopSecond);
            wrapper = mount(GDropdown as object, { localVue, propsData: { text: "Menu" }, attachTo: document.body });
            const dropdown = wrapper.vm as unknown as { show: () => void; hide: () => void };

            dropdown.show();
            dropdown.hide();
            dropdown.show();
            await flushPromises();
            expect(stopFirst).toHaveBeenCalledOnce();
            expect(stopSecond).not.toHaveBeenCalled();

            dropdown.hide();
            expect(stopSecond).toHaveBeenCalledOnce();
        });

        it("stops tracking when unmounted while open", async () => {
            const stopTracking = vi.fn();
            vi.mocked(autoUpdate).mockImplementationOnce(() => stopTracking);
            const mounted = mount(GDropdown as object, {
                localVue,
                propsData: { text: "Menu" },
                attachTo: document.body,
            });
            await openMenu(mounted);
            await flushPromises();

            mounted.destroy();

            expect(stopTracking).toHaveBeenCalledOnce();
        });
    });

    describe("state", () => {
        it("closes when it becomes disabled", async () => {
            wrapper = mount(GDropdown as object, { localVue, propsData: { text: "Menu" }, attachTo: document.body });
            await openMenu(wrapper);

            await wrapper.setProps({ disabled: true });

            expect(isMenuOpen(wrapper)).toBe(false);
            expect(wrapper.emitted("hide")).toHaveLength(1);
        });

        it("does not listen for outside clicks once unmounted while opening", async () => {
            const addListener = vi.spyOn(document, "addEventListener");
            const mounted = mount(GDropdown as object, {
                localVue,
                propsData: { text: "Menu" },
                attachTo: document.body,
            });

            (mounted.get(".dropdown-toggle").element as HTMLElement).click();
            mounted.destroy();
            await flushPromises();

            expect(addListener).not.toHaveBeenCalledWith("click", expect.any(Function), true);
            addListener.mockRestore();
        });
    });

    describe("link items", () => {
        it("render real anchors so they can be opened in a new tab", () => {
            const wrapper = mountDropdown(`
                <GDropdownItem to="/histories/list">Histories</GDropdownItem>
                <GDropdownItem href="https://example.org/">External</GDropdownItem>`);

            const [routerItem, hrefItem] = wrapper.findAll("a.dropdown-item").wrappers;
            expect(routerItem?.attributes("href")).toBe("/histories/list");
            expect(hrefItem?.attributes("href")).toBe("https://example.org/");
        });

        it("close the menu when a router-link item is clicked", async () => {
            const wrapper = mountDropdown(`<GDropdownItem to="/histories/list">Histories</GDropdownItem>`);
            await openMenu(wrapper);

            await wrapper.get("a.dropdown-item").trigger("click");

            expect(isMenuOpen(wrapper)).toBe(false);
        });

        it("do not navigate when disabled", async () => {
            const wrapper = mountDropdown(`<GDropdownItem disabled to="/histories/list">Histories</GDropdownItem>`);
            const startPath = wrapper.vm.$router.currentRoute.fullPath;
            await openMenu(wrapper);

            const item = wrapper.get("a.dropdown-item");
            await item.trigger("click");

            expect(wrapper.vm.$router.currentRoute.fullPath).toBe(startPath);
            expect(item.attributes("href")).toBe("#");
            expect(item.attributes("aria-disabled")).toBe("true");
        });

        it("close the menu when an href item is clicked", async () => {
            const wrapper = mountDropdown(`<GDropdownItem href="https://example.org/">External</GDropdownItem>`);
            await openMenu(wrapper);

            await wrapper.get("a.dropdown-item").trigger("click");

            expect(isMenuOpen(wrapper)).toBe(false);
        });

        it("close the menu when an action item is clicked", async () => {
            const wrapper = mountDropdown(`<GDropdownItem>Action</GDropdownItem>`);
            await openMenu(wrapper);

            await wrapper.get("a.dropdown-item").trigger("click");

            expect(isMenuOpen(wrapper)).toBe(false);
        });
    });

    describe("keyboard", () => {
        it("opens with ArrowDown on the toggle and focuses the first item", async () => {
            const wrapper = mountDropdown(MENU);

            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");

            expect(isMenuOpen(wrapper)).toBe(true);
            expect(focusedText()).toBe("One");
        });

        it("opens with ArrowUp on the toggle and focuses the last item", async () => {
            const wrapper = mountDropdown(MENU);

            await press(wrapper.get(".dropdown-toggle"), "ArrowUp");

            expect(focusedText()).toBe("Five");
        });

        it("focuses the first item when opened with Enter or Space, but not with the mouse", async () => {
            const wrapper = mountDropdown(MENU);
            const toggle = wrapper.get(".dropdown-toggle");

            // keyboard activation dispatches a click with no click count
            await toggle.trigger("click");
            await flushPromises();
            expect(focusedText()).toBe("One");

            await press(document.activeElement!, "Escape");
            toggle.element.dispatchEvent(new MouseEvent("click", { bubbles: true, detail: 1 }));
            await flushPromises();
            expect(isMenuOpen(wrapper)).toBe(true);
            expect(document.activeElement).toBe(toggle.element);
        });

        it("moves between enabled items with the arrow keys, Home and End", async () => {
            const wrapper = mountDropdown(MENU);
            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");

            await press(document.activeElement!, "ArrowDown");
            expect(focusedText()).toBe("Three");
            await press(document.activeElement!, "ArrowDown");
            expect(focusedText()).toBe("Five");
            await press(document.activeElement!, "ArrowDown");
            expect(focusedText()).toBe("One");
            await press(document.activeElement!, "ArrowUp");
            expect(focusedText()).toBe("Five");
            await press(document.activeElement!, "Home");
            expect(focusedText()).toBe("One");
            await press(document.activeElement!, "End");
            expect(focusedText()).toBe("Five");
        });

        it("keeps items out of the tab order and marks disabled ones", () => {
            const wrapper = mountDropdown(MENU);

            const items = wrapper.findAll("[role='menuitem']").wrappers;
            expect(items.map((item) => item.attributes("tabindex"))).toEqual(["-1", "-1", "-1", "-1", "-1"]);
            expect(items[1]?.attributes("aria-disabled")).toBe("true");
            expect(items[3]?.attributes("disabled")).toBe("disabled");
        });

        it("closes on Escape and returns focus to the toggle", async () => {
            const wrapper = mountDropdown(MENU);
            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");

            await press(document.activeElement!, "Escape");

            expect(isMenuOpen(wrapper)).toBe(false);
            expect(document.activeElement).toBe(wrapper.get(".dropdown-toggle").element);
        });

        it("leaves Escape alone while closed so enclosing dialogs still get it", async () => {
            const wrapper = mountDropdown(MENU);
            const onParentKeydown = vi.fn();
            wrapper.element.addEventListener("keydown", onParentKeydown);

            await press(wrapper.get(".dropdown-toggle"), "Escape");

            expect(onParentKeydown).toHaveBeenCalledOnce();
        });

        it("stays open while Tab moves focus to a control inside the menu", async () => {
            const wrapper = mountDropdown(`
                <GDropdownGroup>
                    <template v-slot:header><input id="filter" /></template>
                    <GDropdownItem>One</GDropdownItem>
                </GDropdownGroup>
                <GDropdownForm><input id="remember" type="checkbox" /></GDropdownForm>`);
            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");
            expect(focusedText()).toBe("One");

            // jsdom does not move focus on Tab, so do what the browser would
            await press(document.activeElement!, "Tab", true);
            (wrapper.get("#filter").element as HTMLElement).focus();
            await flushPromises();
            expect(isMenuOpen(wrapper)).toBe(true);

            await press(document.activeElement!, "Tab");
            (wrapper.get("#remember").element as HTMLElement).focus();
            await flushPromises();
            expect(isMenuOpen(wrapper)).toBe(true);
        });

        it("closes when focus moves outside, without pulling it back to the toggle", async () => {
            const wrapper = mountDropdown(MENU);
            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");

            await press(document.activeElement!, "Tab");
            expect(isMenuOpen(wrapper)).toBe(true);
            (wrapper.get("#outside").element as HTMLElement).focus();
            await flushPromises();

            expect(isMenuOpen(wrapper)).toBe(false);
            expect(document.activeElement).toBe(wrapper.get("#outside").element);
        });

        it("activates link items with Space and returns focus to the toggle", async () => {
            const onSelect = vi.fn();
            const wrapper = mountDropdown(`<GDropdownItem @click="onSelect">One</GDropdownItem>`, { onSelect });
            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");

            await press(document.activeElement!, " ");

            expect(onSelect).toHaveBeenCalledOnce();
            expect(isMenuOpen(wrapper)).toBe(false);
            expect(document.activeElement).toBe(wrapper.get(".dropdown-toggle").element);
        });

        it("keeps the keys it handles from ancestors, such as Bootstrap's document handler", async () => {
            const wrapper = mountDropdown(MENU);
            const onAncestorKeydown = vi.fn();
            wrapper.element.addEventListener("keydown", onAncestorKeydown);

            await press(wrapper.get(".dropdown-toggle"), "ArrowDown");
            for (const key of ["ArrowDown", "ArrowUp", "Home", "End", "Enter", " "]) {
                await press(document.activeElement!, key);
            }
            expect(onAncestorKeydown).not.toHaveBeenCalled();

            await press(wrapper.get(".dropdown-toggle"), "a");
            expect(onAncestorKeydown).toHaveBeenCalledOnce();
        });

        it("keeps Enter and Space on the toggle from ancestors, which could take them as a click", async () => {
            const wrapper = mountDropdown(MENU);
            const onAncestorKeydown = vi.fn();
            wrapper.element.addEventListener("keydown", onAncestorKeydown);

            await press(wrapper.get(".dropdown-toggle"), "Enter");
            await press(wrapper.get(".dropdown-toggle"), " ");

            expect(onAncestorKeydown).not.toHaveBeenCalled();
        });

        it("leaves keys typed into a control inside the menu alone", async () => {
            const wrapper = mountDropdown(`<GDropdownForm><input id="name" /></GDropdownForm>${MENU}`);
            await openMenu(wrapper);
            // Let the open focus its first item, as it does before the user can move on
            await flushPromises();
            const input = wrapper.get("#name").element as HTMLInputElement;
            input.focus();

            for (const key of ["ArrowDown", "ArrowUp", "Home", "End", " "]) {
                const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true });
                input.dispatchEvent(event);
                await flushPromises();
                expect(event.defaultPrevented).toBe(false);
                expect(document.activeElement).toBe(input);
            }
        });

        it("lets a nested dropdown handle its own arrow keys", async () => {
            const wrapper = mountTemplate(`
                <GDropdown text="Outer">
                    <GDropdownItem>Outer one</GDropdownItem>
                    <GDropdownForm>
                        <GDropdown text="Inner">
                            <GDropdownItem>Inner one</GDropdownItem>
                            <GDropdownItem>Inner two</GDropdownItem>
                        </GDropdown>
                    </GDropdownForm>
                    <GDropdownItem>Outer two</GDropdownItem>
                </GDropdown>`);
            const [outerToggle, innerToggle] = wrapper.findAll(".dropdown-toggle").wrappers;
            await press(outerToggle!, "ArrowDown");
            (innerToggle!.element as HTMLElement).focus();
            await press(innerToggle!, "ArrowDown");
            expect(focusedText()).toBe("Inner one");

            await press(document.activeElement!, "ArrowDown");
            expect(focusedText()).toBe("Inner two");
            await press(document.activeElement!, "ArrowDown");
            expect(focusedText()).toBe("Inner one");
        });
    });
});
