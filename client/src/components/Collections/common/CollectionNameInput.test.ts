import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CollectionNameInput from "./CollectionNameInput.vue";

function mountInput(value = "my list") {
    return mount(CollectionNameInput as object, {
        props: { modelValue: value, shortWhatIsBeingCreated: "list" },
        global: getLocalVue(),
    });
}

function nameInput(wrapper: ReturnType<typeof mountInput>) {
    return wrapper.get("input.collection-name");
}

describe("CollectionNameInput", () => {
    it("shows the name in a small, required GFormInput", () => {
        const wrapper = mountInput();
        const input = nameInput(wrapper);
        expect(input.classes()).toEqual(expect.arrayContaining(["g-form-input", "g-small"]));
        expect(input.attributes("id")).toBe("collection-name");
        expect(input.attributes("required")).toBeDefined();
        expect(input.attributes("placeholder")).toBe("Enter a name for your new list");
        expect((input.element as HTMLInputElement).value).toBe("my list");
        expect(input.classes()).not.toContain("g-invalid");
    });

    it("emits update:modelValue with the typed name", async () => {
        const wrapper = mountInput();
        await nameInput(wrapper).setValue("renamed list");
        expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["renamed list"]);
    });

    it("marks an empty name invalid", async () => {
        const wrapper = mountInput();
        await nameInput(wrapper).setValue("");
        expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual([""]);
        expect(nameInput(wrapper).classes()).toContain("g-invalid");
        expect(nameInput(wrapper).attributes("aria-invalid")).toBe("true");
    });

    it("shows a name the parent sets", async () => {
        const wrapper = mountInput();
        await wrapper.setProps({ modelValue: "from parent" } as never);
        expect((nameInput(wrapper).element as HTMLInputElement).value).toBe("from parent");
    });
});
