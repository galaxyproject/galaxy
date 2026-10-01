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

    async function keyPress(wrapper: ReturnType<typeof mountWithProps>, key: string) {
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
