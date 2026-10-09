import { emittedArg, getLocalVue, nth } from "@tests/vitest/helpers";
import { DOMWrapper, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import HeadlessMultiselect from "./HeadlessMultiselect.vue";

describe("HeadlessMultiselect", () => {
    const localVue = getLocalVue();

    // The component teleports its options popup to `#app` (falling back to a
    // parent `<dialog>` id, which doesn't apply here). Recreate that root so
    // the teleported content actually lands in the DOM, mirroring how the
    // real app mounts.
    let appRoot: HTMLDivElement;

    beforeEach(() => {
        appRoot = document.createElement("div");
        appRoot.id = "app";
        document.body.appendChild(appRoot);
    });

    afterEach(() => {
        appRoot.remove();
    });

    type Props = InstanceType<typeof HeadlessMultiselect>["$props"];
    const mountWithProps = (props: Props) => {
        return mount(HeadlessMultiselect as any, {
            props: props,
            global: localVue,
            attachTo: appRoot,
        });
    };

    const sampleOptions = ["name:named", "name:named_2", "name:named_3", "abc", "def", "ghi"];

    const selectors = {
        openButton: ".toggle-button",
        option: ".headless-multiselect__option",
        highlighted: ".headless-multiselect__option.highlighted",
        input: "fieldset input",
        invalid: ".headless-multiselect__option.invalid",
    } as const;

    async function keyPress(wrapper: DOMWrapper<Element>, key: string) {
        wrapper.trigger("keydown", {
            key,
            code: key,
        });
        await nextTick();
        wrapper.trigger("keyup", {
            key,
            code: key,
        });
        await nextTick();
    }

    async function open(wrapper: ReturnType<typeof mountWithProps>) {
        wrapper.find(selectors.openButton).trigger("click");
        await nextTick();
        return wrapper.find(selectors.input);
    }

    async function close(wrapper: ReturnType<typeof mountWithProps>) {
        await keyPress(wrapper.find(selectors.input), "Escape");
    }

    async function nextAnimationFrame() {
        await new Promise((resolve) => requestAnimationFrame(resolve));
        await nextTick();
    }

    // The options popup is teleported to `#app`, so it's no longer a
    // descendant of `wrapper.element` -- query the DOM directly for it.
    function findAllOptions() {
        return new DOMWrapper(document.body).findAll(selectors.option);
    }

    function findHighlighted() {
        return new DOMWrapper(document.body).find(selectors.highlighted);
    }

    describe("while toggling the popup", () => {
        it("shows and hides options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let options;

            await open(wrapper);
            options = findAllOptions();
            expect(options.length).toBe(sampleOptions.length);

            await close(wrapper);
            options = findAllOptions();
            expect(options.length).toBe(0);
        });

        it("retains focus", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            expect(input.element).toBe(document.activeElement);

            await close(wrapper);
            const button = wrapper.find(selectors.openButton);
            expect(button.element).toBe(document.activeElement);
        });

        it("stays open when opened from the keyboard", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            expect(input.element).toBe(document.activeElement);

            // the open button is removed while focused, so focusout fires without a relatedTarget
            wrapper.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
            await nextAnimationFrame();

            expect(findAllOptions().length).toBe(sampleOptions.length);
            await close(wrapper);
        });

        it("closes when focus moves outside", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            (input.element as HTMLInputElement).blur();
            wrapper.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: null }));
            await nextAnimationFrame();

            expect(findAllOptions().length).toBe(0);
        });

        it("keeps Escape in the input from reaching a parent dialog", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            const event = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
            input.element.dispatchEvent(event);
            await nextTick();

            expect(event.defaultPrevented).toBe(true);
            expect(findAllOptions().length).toBe(0);
        });

        it("keeps Escape on an option from reaching a parent dialog", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            await open(wrapper);
            const event = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
            nth(findAllOptions(), 0).element.dispatchEvent(event);
            await nextTick();

            expect(event.defaultPrevented).toBe(true);
            expect(findAllOptions().length).toBe(0);
        });

        it("keeps Escape on the close button from reaching a parent dialog", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            await open(wrapper);
            const event = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
            wrapper.find("fieldset button").element.dispatchEvent(event);
            await nextTick();

            expect(event.defaultPrevented).toBe(true);
            expect(wrapper.find(selectors.input).exists()).toBe(false);
        });
    });

    describe("while inputting text", () => {
        it("filters options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let options;

            const input = await open(wrapper);

            await input.setValue("a");
            options = findAllOptions();
            expect(options.length).toBe(5);

            await input.setValue("na");
            options = findAllOptions();
            expect(options.length).toBe(4);

            await input.setValue("");
            options = findAllOptions();
            expect(options.length).toBe(6);
        });

        it("shows the search value on top", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);

            await input.setValue("bc");
            const options = findAllOptions();

            expect(nth(options, 0).find("span").text()).toBe("bc");
            expect(nth(options, 1).find("span").text()).toBe("abc");

            await close(wrapper);
        });

        it("allows for switching the highlighted value", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let highlighted;

            const input = await open(wrapper);

            highlighted = findHighlighted();
            expect(highlighted.find("span").text()).toBe("#named");

            await keyPress(input, "ArrowDown");
            highlighted = findHighlighted();
            expect(highlighted.find("span").text()).toBe("#named_2");

            await keyPress(input, "ArrowDown");
            highlighted = findHighlighted();
            expect(highlighted.find("span").text()).toBe("#named_3");

            await keyPress(input, "ArrowUp");
            highlighted = findHighlighted();
            expect(highlighted.find("span").text()).toBe("#named_2");

            await close(wrapper);
        });

        it("resets the highlighted option on input", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            let highlighted;

            const input = await open(wrapper);

            await keyPress(input, "ArrowDown");
            highlighted = findHighlighted();
            expect(highlighted.find("span").text()).toBe("#named_2");

            await input.setValue("a");

            highlighted = findHighlighted();
            expect(highlighted.find("span").text()).toBe("a");

            await close(wrapper);
        });

        it("shows if the input value is valid", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
                validator: (value: string) => value !== "invalid",
            });

            const input = await open(wrapper);
            await input.setValue("valid");
            expect(() => new DOMWrapper(document.body).get(selectors.invalid)).toThrow();

            await input.setValue("invalid");
            expect(() => new DOMWrapper(document.body).get(selectors.invalid)).not.toThrow();
            await close(wrapper);
        });
    });

    describe("as a combobox", () => {
        it("reports the listbox it controls", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            expect(input.attributes("role")).toBe("combobox");
            expect(input.attributes("aria-expanded")).toBe("true");
            expect(input.attributes("aria-controls")).toBe("tags-options");
            expect(document.getElementById("tags-options")?.getAttribute("role")).toBe("listbox");
            await close(wrapper);
        });

        it("marks only an invalid search value as invalid", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
                validator: (value: string) => value !== "invalid",
            });

            const input = await open(wrapper);
            await input.setValue("valid");
            expect(input.attributes("aria-invalid")).not.toBe("true");

            await input.setValue("invalid");
            expect(input.attributes("aria-invalid")).toBe("true");
            await close(wrapper);
        });

        it("points to the highlighted option", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            expect(input.attributes("aria-activedescendant")).toBe("tags-option-0");

            await keyPress(input, "ArrowDown");
            expect(input.attributes("aria-activedescendant")).toBe("tags-option-1");
            await close(wrapper);
        });

        it("points to no option when there are none", async () => {
            const wrapper = mountWithProps({
                options: [] as string[],
                selected: [] as string[],
            });

            const input = await open(wrapper);
            expect(input.attributes("aria-activedescendant")).toBeUndefined();
            await close(wrapper);
        });
    });

    describe("when pressing Tab on the close button", () => {
        function tabOnCloseButton(wrapper: ReturnType<typeof mountWithProps>) {
            const event = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
            wrapper.find("fieldset button").element.dispatchEvent(event);
            return event;
        }

        it("moves focus to the first suggestion", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
            });
            await open(wrapper);

            const event = tabOnCloseButton(wrapper);

            expect(event.defaultPrevented).toBe(true);
            expect(document.activeElement?.id).toBe("tags-option-0");
            await close(wrapper);
        });

        it("keeps the native Tab when there are no suggestions", async () => {
            const wrapper = mountWithProps({
                options: [] as string[],
                selected: [] as string[],
            });
            await open(wrapper);

            const event = tabOnCloseButton(wrapper);

            expect(event.defaultPrevented).toBe(false);
            await close(wrapper);
        });
    });

    describe("with the suggestions in the page flow", () => {
        it("teleports the suggestions out of the editor by default", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
            });
            await open(wrapper);

            expect(document.getElementById("tags-options")).not.toBeNull();
            expect(wrapper.find("#tags-options").exists()).toBe(false);
            await close(wrapper);
        });

        it("renders the suggestions inside the editor", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
                listInFlow: true,
            });
            await open(wrapper);

            const listbox = wrapper.find("#tags-options");
            expect(listbox.exists()).toBe(true);
            expect(listbox.classes()).toContain("headless-multiselect__options--in-flow");
            expect(wrapper.findAll(selectors.option)).toHaveLength(sampleOptions.length);
            await close(wrapper);
        });

        it("keeps the native Tab on the last suggestion", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
                listInFlow: true,
            });
            await open(wrapper);

            const event = new KeyboardEvent("keydown", { key: "Tab", bubbles: true, cancelable: true });
            wrapper.find(`#tags-option-${sampleOptions.length - 1}`).element.dispatchEvent(event);

            expect(event.defaultPrevented).toBe(false);
            await close(wrapper);
        });

        function addOutsideButton() {
            const button = document.createElement("button");
            appRoot.appendChild(button);
            return button;
        }

        function focusOutTo(wrapper: ReturnType<typeof mountWithProps>, target: HTMLElement) {
            wrapper.element.dispatchEvent(new FocusEvent("focusout", { bubbles: true, relatedTarget: target }));
            target.focus();
        }

        it("keeps the suggestions open when focus leaves (mouse down or Tab)", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
                listInFlow: true,
            });
            await open(wrapper);

            focusOutTo(wrapper, addOutsideButton());
            await nextAnimationFrame();

            expect(wrapper.find("#tags-options").exists()).toBe(true);
            await close(wrapper);
        });

        it("closes on a click outside only after the click is delivered", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
                listInFlow: true,
            });
            await open(wrapper);
            // onClickOutside skips clicks within the same task as the opening click
            await new Promise((resolve) => setTimeout(resolve));
            const button = addOutsideButton();
            let clicked = false;
            button.addEventListener("click", () => {
                clicked = true;
            });

            button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
            await nextTick();

            expect(clicked).toBe(true);
            expect(wrapper.find("#tags-options").exists()).toBe(true);

            await new Promise((resolve) => setTimeout(resolve));
            await nextTick();
            expect(wrapper.find("#tags-options").exists()).toBe(false);
        });

        it("still closes the overlay when focus moves to an outside button", async () => {
            const wrapper = mountWithProps({
                id: "tags",
                options: sampleOptions,
                selected: [] as string[],
            });
            await open(wrapper);

            focusOutTo(wrapper, addOutsideButton());
            await nextAnimationFrame();

            expect(document.getElementById("tags-options")).toBeNull();
        });
    });

    describe("when selecting options", () => {
        it("selects options via keyboard", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);

            await keyPress(input, "Enter");
            expect(emittedArg(wrapper, "input")).toEqual(["name:named"]);

            await keyPress(input, "ArrowDown");
            await keyPress(input, "Enter");
            expect(emittedArg(wrapper, "input", 1)).toEqual(["name:named_2"]);
            await close(wrapper);
        });

        it("deselects options via keyboard", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: ["name:named", "name:named_2", "name:named_3"],
            });

            const input = await open(wrapper);

            await keyPress(input, "Enter");
            expect(emittedArg(wrapper, "input")).toEqual(["name:named_2", "name:named_3"]);

            await keyPress(input, "ArrowDown");
            await keyPress(input, "Enter");
            expect(emittedArg(wrapper, "input", 1)).toEqual(["name:named", "name:named_3"]);
            await close(wrapper);
        });

        it("allows for adding new options", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            const input = await open(wrapper);
            await input.setValue("123");
            await keyPress(input, "Enter");

            expect(emittedArg(wrapper, "addOption")).toBe("123");
            await close(wrapper);
        });

        it("selects options with mouse", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: [] as string[],
            });

            await open(wrapper);
            const options = findAllOptions();

            await nth(options, 0).trigger("click");
            expect(emittedArg(wrapper, "input")).toEqual(["name:named"]);

            await nth(options, 1).trigger("click");
            expect(emittedArg(wrapper, "input", 1)).toEqual(["name:named_2"]);
            await close(wrapper);
        });

        it("deselects options with mouse", async () => {
            const wrapper = mountWithProps({
                options: sampleOptions,
                selected: ["name:named", "name:named_2", "name:named_3"],
            });

            await open(wrapper);
            const options = findAllOptions();

            await nth(options, 0).trigger("click");
            expect(emittedArg(wrapper, "input")).toEqual(["name:named_2", "name:named_3"]);

            await nth(options, 1).trigger("click");
            expect(emittedArg(wrapper, "input", 1)).toEqual(["name:named", "name:named_3"]);
            await close(wrapper);
        });
    });
});
