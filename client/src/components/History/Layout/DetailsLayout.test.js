import { getFakeAnonymousUser, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { useUserStore } from "@/stores/userStore";

import DetailsLayout from "./DetailsLayout.vue";

const localVue = getLocalVue();

const SELECTORS = {
    EDITOR_TOGGLE: "[data-description='editor toggle']",
    RENAME_LABEL: ".click-to-edit-label",
    NAME_DISPLAY: "[data-description='name display']",
    ANNOTATION_INPUT: "[data-description='annotation input']",
    SAVE_BUTTON: "[data-description='editor save button']",
};

enableAutoUnmount(afterEach);

/** Mounts the layout, then signs `user` in, as the user store loads after the page renders. */
async function mountDetailsLayout({ props = {}, user = getFakeRegisteredUser() } = {}) {
    const pinia = createPinia();
    const wrapper = mount(DetailsLayout, { global: withPlugins(localVue, pinia), props });
    if (user) {
        useUserStore(pinia).currentUser = user;
        await nextTick();
    }
    return wrapper;
}

async function openEditor(wrapper) {
    await wrapper.find(SELECTORS.EDITOR_TOGGLE).trigger("click");
}

describe("DetailsLayout", () => {
    it("allows logged-in users to edit all details", async () => {
        const wrapper = await mountDetailsLayout();

        const toggle = wrapper.find(SELECTORS.EDITOR_TOGGLE);
        expect(toggle.attributes("title")).toBe("Edit");
        expect(toggle.attributes("aria-disabled")).toBeUndefined();
        expect(wrapper.find(SELECTORS.RENAME_LABEL).exists()).toBe(true);
    });

    it("prompts anonymous users to log in to edit all details, but allows rename", async () => {
        const wrapper = await mountDetailsLayout({ user: getFakeAnonymousUser() });

        const toggle = wrapper.find(SELECTORS.EDITOR_TOGGLE);
        expect(toggle.attributes("title")).toBe("Log in to Rename History");
        expect(toggle.attributes("aria-disabled")).toBe("true");
        expect(wrapper.find(SELECTORS.RENAME_LABEL).exists()).toBe(true);
    });

    it("disallows editing and renaming if props set them to false", async () => {
        const wrapper = await mountDetailsLayout({ props: { writeable: false, renameable: false } });

        const toggle = wrapper.find(SELECTORS.EDITOR_TOGGLE);
        expect(toggle.attributes("title")).toBe("Not Editable");
        expect(toggle.attributes("aria-disabled")).toBe("true");
        expect(wrapper.find(SELECTORS.RENAME_LABEL).exists()).toBe(false);
    });

    it("shows a summarized name as text", async () => {
        const name = "Run <b>2</b> of the assembly";

        const wrapper = await mountDetailsLayout({ props: { name, summarized: "both" }, user: null });

        const nameDisplay = wrapper.find(SELECTORS.NAME_DISPLAY);
        expect(nameDisplay.find("b").exists()).toBe(false);
        expect(nameDisplay.text()).toBe(name);
    });

    it("saves only the fields edited in the editor", async () => {
        const wrapper = await mountDetailsLayout({ props: { name: "history name", annotation: "", tags: [] } });

        await openEditor(wrapper);
        // A tag save that was still in flight when the editor opened lands now.
        await wrapper.setProps({ tags: ["saved_tag"] });
        await wrapper.find(SELECTORS.ANNOTATION_INPUT).setValue("new annotation");
        await wrapper.find(SELECTORS.SAVE_BUTTON).trigger("click");

        expect(wrapper.emitted("save")).toEqual([[{ annotation: "new annotation" }]]);
    });

    it("does not emit a save when nothing was edited", async () => {
        const wrapper = await mountDetailsLayout({
            props: { name: "history name", annotation: "annotation", tags: ["tag"] },
        });

        await openEditor(wrapper);
        await wrapper.find(SELECTORS.SAVE_BUTTON).trigger("click");

        expect(wrapper.emitted("save")).toBeUndefined();
    });
});
