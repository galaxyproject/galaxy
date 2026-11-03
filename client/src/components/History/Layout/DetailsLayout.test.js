import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { describe, expect, it } from "vitest";

import { useUserStore } from "@/stores/userStore";

import DetailsLayout from "./DetailsLayout.vue";

const localVue = getLocalVue();

async function createWrapper(component, localVue, userData, unwritable = false, propsData = {}) {
    const pinia = createPinia();
    const wrapper = mount(component, {
        global: localVue,
        pinia,
        props: {
            writeable: !unwritable,
            renameable: !unwritable,
            ...propsData,
        },
    });
    const userStore = useUserStore();
    userStore.currentUser = { ...userStore.currentUser, ...userData };
    return wrapper;
}

describe("DetailsLayout", () => {
    it("allows logged-in users to edit all details", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, {
            id: "user.id",
            email: "user.email",
        });

        expect(wrapper.find(".edit-button").attributes("title")).toBe("Edit");

        // Click to edit and rename
        expect(wrapper.find(".click-to-edit-label").exists()).toBe(true);
    });

    it("prompts anonymous users to log in to edit all details, but allows rename", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, {});

        expect(wrapper.find(".edit-button").attributes("title")).toContain("Log in");

        // Click to edit and rename should still be available
        expect(wrapper.find(".click-to-edit-label").exists()).toBe(true);
    });

    it("disallows editing and renaming if props set them to false", async () => {
        const wrapper = await createWrapper(
            DetailsLayout,
            localVue,
            {
                id: "user.id",
                email: "user.email",
            },
            true,
        );

        expect(wrapper.find(".edit-button").attributes("title")).toContain("Not Editable");
        expect(wrapper.find(".click-to-edit-label").exists()).toBe(false);
    });

    it("shows a summarized name as text", () => {
        const name = "Run <b>2</b> of the assembly";
        const wrapper = mount(DetailsLayout, {
            localVue,
            pinia: createPinia(),
            propsData: { name, summarized: "both" },
        });
        const nameDisplay = wrapper.find("[data-description='name display']");
        expect(nameDisplay.find("b").exists()).toBe(false);
        expect(nameDisplay.text()).toBe(name);
    });

    it("saves only the fields edited in the editor", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, { id: "user.id", email: "user.email" }, false, {
            name: "history name",
            annotation: "",
            tags: [],
        });

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        // A tag save that was still in flight when the editor opened lands now.
        await wrapper.setProps({ tags: ["saved_tag"] });
        await wrapper.find("[data-description='annotation input']").setValue("new annotation");
        await wrapper.find("[data-description='editor save button']").trigger("click");

        expect(wrapper.emitted("save")).toEqual([[{ annotation: "new annotation" }]]);
    });

    it("edits the name in a GFormInput and saves it trimmed", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, { id: "user.id", email: "user.email" }, false, {
            name: "history name",
            annotation: "",
            tags: [],
        });

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        const nameInput = wrapper.get("[data-description='name input']");
        expect(nameInput.classes()).toContain("g-form-input");
        expect(nameInput.element.value).toBe("history name");
        await nameInput.setValue("  new name  ");
        await wrapper.find("[data-description='editor save button']").trigger("click");

        expect(wrapper.emitted("save")).toEqual([[{ name: "new name" }]]);
    });

    it("leaves a stored padded name alone when only the annotation is edited", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, { id: "user.id", email: "user.email" }, false, {
            name: " padded ",
            annotation: "",
            tags: [],
        });

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        await wrapper.find("[data-description='annotation input']").setValue("new annotation");
        await wrapper.find("[data-description='editor save button']").trigger("click");

        expect(wrapper.emitted("save")).toEqual([[{ annotation: "new annotation" }]]);
    });

    it("saves the name on Enter and closes the editor on Escape", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, { id: "user.id", email: "user.email" }, false, {
            name: "history name",
            annotation: "",
            tags: [],
        });

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        const nameInput = wrapper.get("[data-description='name input']");
        await nameInput.setValue("entered name");
        await nameInput.trigger("keyup", { key: "Enter" });
        expect(wrapper.emitted("save")).toEqual([[{ name: "entered name" }]]);
        expect(wrapper.find("[data-description='edit form']").exists()).toBe(false);

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        await wrapper.get("[data-description='name input']").setValue("discarded name");
        await wrapper.get("[data-description='name input']").trigger("keyup", { key: "Escape" });
        expect(wrapper.find("[data-description='edit form']").exists()).toBe(false);
        expect(wrapper.emitted("save")).toHaveLength(1);
    });

    it("does not save a blank name", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, { id: "user.id", email: "user.email" }, false, {
            name: "history name",
            annotation: "",
            tags: [],
        });

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        await wrapper.get("[data-description='name input']").setValue("   ");
        expect(wrapper.get("[data-description='editor save button']").attributes("aria-disabled")).toBe("true");
    });

    it("does not emit a save when nothing was edited", async () => {
        const wrapper = await createWrapper(DetailsLayout, localVue, { id: "user.id", email: "user.email" }, false, {
            name: "history name",
            annotation: "annotation",
            tags: ["tag"],
        });

        await wrapper.find("[data-description='editor toggle']").trigger("click");
        await wrapper.find("[data-description='editor save button']").trigger("click");

        expect(wrapper.emitted("save")).toBeUndefined();
    });
});
