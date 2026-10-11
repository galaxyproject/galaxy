import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter, getLocalVue } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import * as GroupFormStories from "./GroupForm.stories";
import { ADMIN_GROUPS, ADMIN_ROLES, ADMIN_USER } from "./test_fixtures";

import GroupForm from "./GroupForm.vue";
import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";

const stories = composeStories(GroupFormStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();
const localVue = getLocalVue();

// The group the stories edit, with its one member and one role.
const GROUP_NAME = ADMIN_GROUPS[0]!.name;
const MEMBER_ID = ADMIN_USER.id;
const ROLE_ID = ADMIN_ROLES[0]!.id;

const SELECTORS = {
    NAME_INPUT: "#admin-group-name-input",
    SUBMIT: "#admin-group-submit",
};

/** Mounts the story with a router whose `push` is watched, to see where the form sends the admin next. */
async function mountGroupForm(story: StoryOf<typeof stories>) {
    const router = createTestRouter();
    const push = vi.spyOn(router, "push");
    const wrapper = mountStory(story, { router });
    await flushPromises();
    return { wrapper, push };
}

/** Records the bodies of group updates; the story still answers them. */
function captureUpdate() {
    const requests: unknown[] = [];
    server.use(
        http.put("/api/groups/{group_id}", async ({ request }) => {
            requests.push(await request.clone().json());
        }),
    );
    return requests;
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.SUBMIT).trigger("click");
    await flushPromises();
}

describe("GroupForm edit mode", () => {
    it("keeps the saved group name in the title while the name is edited", async () => {
        const { wrapper } = await mountGroupForm(stories.ExistingGroup);
        expect(wrapper.text()).toContain(`Group '${GROUP_NAME}'`);

        await wrapper.find(SELECTORS.NAME_INPUT).setValue("Renamed");

        expect(wrapper.text()).toContain(`Group '${GROUP_NAME}'`);
    });

    it("renames a group together with its associations", async () => {
        const { wrapper, push } = await mountGroupForm(stories.ExistingGroup);
        const requests = captureUpdate();

        await wrapper.find(SELECTORS.NAME_INPUT).setValue("Renamed");
        await submit(wrapper);

        expect(requests).toEqual([{ name: "Renamed", user_ids: [MEMBER_ID], role_ids: [ROLE_ID] }]);
        expect(push).toHaveBeenCalledWith("/admin/groups");
    });

    it("does not save an empty name", async () => {
        const { wrapper, push } = await mountGroupForm(stories.ExistingGroup);
        const requests = captureUpdate();

        await wrapper.find(SELECTORS.NAME_INPUT).setValue("");
        await submit(wrapper);

        expect(wrapper.text()).toContain("Please enter a group name.");
        expect(requests).toEqual([]);
        expect(push).not.toHaveBeenCalled();
    });

    it.each([
        {
            story: stories.GroupGone,
            path: "/api/groups/{group_id}",
            message: "Group with the provided id was not found.",
        },
        {
            story: stories.GroupGoneWhileUsersLoad,
            path: "/api/groups/{group_id}/users",
            message: "Group with the id provided was not found.",
        },
        {
            story: stories.RolesFailToLoad,
            path: "/api/groups/{group_id}/roles",
            message: "Internal server error.",
        },
    ])("cannot be saved when $path fails to load", async ({ story, message }) => {
        const { wrapper } = await mountGroupForm(story);

        expect(wrapper.text()).toContain(message);
        expect(wrapper.find(SELECTORS.SUBMIT).exists()).toBe(false);
    });
});

describe("GroupForm.vue create mode", () => {
    it("asks for a role with the same name when the checkbox is ticked", async () => {
        const requests: unknown[] = [];
        server.use(
            http.post("/api/groups", async ({ request, response }) => {
                requests.push(await request.json());
                return response(200).json([{ id: "g2", name: "New", url: "/api/groups/g2", model_class: "Group" }]);
            }),
        );
        const wrapper = mount(GroupForm as object, {
            global: { ...localVue, stubs: { ...localVue.stubs, FontAwesomeIcon: true } },
        });
        await flushPromises();
        onTestFinished(() => wrapper.unmount());
        await wrapper.find("#admin-group-name-input").setValue("New");
        await wrapper.findComponent(GCheckbox).find("input").setValue(true);
        await submit(wrapper);
        expect(requests).toEqual([{ name: "New", user_ids: [], role_ids: [], auto_create_role: true }]);
    });
});
