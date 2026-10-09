import { emittedArg, getLocalVue, nth } from "@tests/vitest/helpers";
import { DOMWrapper, enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import HeadlessMultiselect from "./HeadlessMultiselect.vue";

describe("HeadlessMultiselect", () => {
    enableAutoUnmount(afterEach);

    // Keep the real teleport and focus behavior by mounting into its popup target.
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
    const mountWithProps = (props: Partial<Props> = {}) => {
        return mount(HeadlessMultiselect, {
            props: { options: sampleOptions, selected: [], ...props },
            global: getLocalVue(),
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

    async function keyPress(wrapper: Pick<DOMWrapper<Element>, "trigger">, key: string) {
        await wrapper.trigger("keydown", {
            key,
            code: key,
        });
        await wrapper.trigger("keyup", {
            key,
            code: key,
        });
    }

    async function open(wrapper: ReturnType<typeof mountWithProps>) {
        await wrapper.get(selectors.openButton).trigger("click");
        return wrapper.get(selectors.input);
    }

    async function close(wrapper: ReturnType<typeof mountWithProps>) {
        await keyPress(wrapper.get(selectors.input), "Escape");
    }

    // Teleported options belong to the app root, outside wrapper.element.
    function findAllOptions() {
        return new DOMWrapper(appRoot).findAll(selectors.option);
    }

    function findHighlighted() {
        return new DOMWrapper(appRoot).find(selectors.highlighted);
    }

    describe("while toggling the popup", () => {
        it("shows and hides options", async () => {
            const wrapper = mountWithProps();

            await open(wrapper);
            expect(findAllOptions()).toHaveLength(sampleOptions.length);

            await close(wrapper);
            expect(findAllOptions()).toHaveLength(0);
        });

        it("retains focus", async () => {
            const wrapper = mountWithProps();

            const input = await open(wrapper);
            expect(input.element).toBe(document.activeElement);

            await close(wrapper);
            const button = wrapper.find(selectors.openButton);
            expect(button.element).toBe(document.activeElement);
        });
    });

    describe("while inputting text", () => {
        it("filters options", async () => {
            const wrapper = mountWithProps();

            const input = await open(wrapper);

            await input.setValue("a");
            expect(findAllOptions()).toHaveLength(5);

            await input.setValue("na");
            expect(findAllOptions()).toHaveLength(4);

            await input.setValue("");
            expect(findAllOptions()).toHaveLength(6);
        });

        it("shows the search value on top", async () => {
            const wrapper = mountWithProps();

            const input = await open(wrapper);

            await input.setValue("bc");
            const options = findAllOptions();

            expect(nth(options, 0).find("span").text()).toBe("bc");
            expect(nth(options, 1).find("span").text()).toBe("abc");

            await close(wrapper);
        });

        it("allows for switching the highlighted value", async () => {
            const wrapper = mountWithProps();

            const input = await open(wrapper);

            expect(findHighlighted().find("span").text()).toBe("#named");

            await keyPress(input, "ArrowDown");
            expect(findHighlighted().find("span").text()).toBe("#named_2");

            await keyPress(input, "ArrowDown");
            expect(findHighlighted().find("span").text()).toBe("#named_3");

            await keyPress(input, "ArrowUp");
            expect(findHighlighted().find("span").text()).toBe("#named_2");

            await close(wrapper);
        });

        it("resets the highlighted option on input", async () => {
            const wrapper = mountWithProps();

            const input = await open(wrapper);

            await keyPress(input, "ArrowDown");
            expect(findHighlighted().find("span").text()).toBe("#named_2");

            await input.setValue("a");

            expect(findHighlighted().find("span").text()).toBe("a");

            await close(wrapper);
        });

        it("shows if the input value is valid", async () => {
            const wrapper = mountWithProps({
                validator: (value: string) => value !== "invalid",
            });

            const input = await open(wrapper);
            await input.setValue("valid");
            expect(new DOMWrapper(appRoot).find(selectors.invalid).exists()).toBe(false);

            await input.setValue("invalid");
            expect(new DOMWrapper(appRoot).get(selectors.invalid).find("span").text()).toBe("invalid");
            await close(wrapper);
        });
    });

    describe("when selecting options", () => {
        it("selects options via keyboard", async () => {
            const wrapper = mountWithProps();

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
            const wrapper = mountWithProps();

            const input = await open(wrapper);
            await input.setValue("123");
            await keyPress(input, "Enter");

            expect(emittedArg(wrapper, "addOption")).toBe("123");
            await close(wrapper);
        });

        it("selects options with mouse", async () => {
            const wrapper = mountWithProps();

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
