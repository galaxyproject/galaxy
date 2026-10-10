import "@/composables/__mocks__/filter";

import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it } from "vitest";
import Multiselect from "vue-multiselect";

import { useServerMock } from "@/api/client/__mocks__";

import * as RoleFormStories from "./RoleForm.stories";
import { ADMIN_GROUPS } from "./test_fixtures";

import FormSelection from "@/components/Form/Elements/FormSelection.vue";

const stories = composeStories(RoleFormStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

// The role ExistingRole loads, with its one member and group.
const ROLE_NAME = "Data managers";
const ROLE_DESCRIPTION = "Can run data manager tools";
const ROLE_MEMBER = { id: "f2db41e1fa331b3e", email: "alice@example.org" };
const ROLE_GROUP = ADMIN_GROUPS[0]!;
const OTHER_GROUP = ADMIN_GROUPS[1]!;

/** Mounts the story on its form page, so leaving it for the roles list is observable. */
async function mountRoleForm(story: StoryOf<typeof stories>, { settle = true } = {}) {
    const router = createTestRouter();
    const formPage = story.args.roleId ? "/admin/form/edit_role" : "/admin/form/create_role";
    await router.push(formPage);
    const wrapper = mountStory(story, { router });
    if (settle) {
        await flushPromises();
    }
    return { wrapper, router, formPage };
}

/** Records the bodies of role creations (POST) and updates (PUT); the story still answers. */
function captureRequests() {
    const requests: { put: unknown[]; post: unknown[] } = { put: [], post: [] };
    server.use(
        http.post("/api/roles", async ({ request }) => {
            requests.post.push(await request.clone().json());
        }),
        http.put("/api/roles/{id}", async ({ request }) => {
            requests.put.push(await request.clone().json());
        }),
    );
    return requests;
}

function multiselect(wrapper: VueWrapper, id: string) {
    return wrapper.find(`#${id}`).findComponent(Multiselect);
}

// vue-multiselect only renders its option list once the dropdown is open.
async function openDropdown(wrapper: VueWrapper, id: string) {
    await wrapper.find(`#${id}-select`).trigger("focus");
}

function selectedTags(wrapper: VueWrapper, id: string) {
    return wrapper.findAll(`#${id} .multiselect__tag`).map((tag) => tag.text());
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find("#role-submit").trigger("click");
    await flushPromises();
}

describe("RoleForm.vue create mode", () => {
    it("associates the visible field labels with editable controls", async () => {
        const { wrapper } = await mountRoleForm(stories.NewRole);
        const ids = ["role-name", "role-description", "role-type", "role-groups-select", "role-users-select"];
        for (const id of ids) {
            const label = wrapper.find(`label[for="${id}"]`);
            expect(label.exists(), `Label for ${id}`).toBe(true);
            expect(label.text().length).toBeGreaterThan(0);
            expect(wrapper.find(`input[id="${id}"]`).exists(), `Input for ${id}`).toBe(true);
        }
    });

    it("shows a loading spinner until the groups are loaded", async () => {
        const { wrapper } = await mountRoleForm(stories.NewRole, { settle: false });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
        expect(wrapper.find("#role-submit").exists()).toBe(true);
    });

    it("shows the error and cannot be saved if the groups fail to load", async () => {
        const { wrapper } = await mountRoleForm(stories.GroupsFailToLoad);
        expect(wrapper.findComponent({ name: "GAlert" }).text()).toContain("Internal server error.");
        expect(wrapper.find("#role-submit").exists()).toBe(false);
    });

    it("requires a name and a description", async () => {
        const { wrapper, router, formPage } = await mountRoleForm(stories.NewRole);
        const requests = captureRequests();
        await submit(wrapper);
        expect(wrapper.findComponent({ name: "GAlert" }).text()).toContain("Please complete all required inputs.");
        expect(requests.post).toEqual([]);
        expect(router.currentRoute.value.path).toBe(formPage);
    });

    it("creates a role with the chosen type, groups and users", async () => {
        const { wrapper, router } = await mountRoleForm(stories.NewRole);
        const requests = captureRequests();
        await wrapper.find("#role-name").setValue("Test Role");
        await wrapper.find("#role-description").setValue("Test Description");
        const roleType = wrapper.findAllComponents(FormSelection).find((w) => w.props("id") === "role-type");
        roleType!.vm.$emit("input", "user_tool_execute");
        multiselect(wrapper, "role-groups").vm.$emit("update:modelValue", [ROLE_GROUP]);
        multiselect(wrapper, "role-users").vm.$emit("update:modelValue", [ROLE_MEMBER]);
        await submit(wrapper);
        expect(requests.post).toEqual([
            {
                name: "Test Role",
                description: "Test Description",
                group_ids: [ROLE_GROUP.id],
                user_ids: [ROLE_MEMBER.id],
                role_type: "user_tool_execute",
            },
        ]);
        expect(router.currentRoute.value.path).toBe("/admin/roles");
    });

    it("searches users by email", async () => {
        const { wrapper } = await mountRoleForm(stories.NewRole);
        let searchedEmail: string | null = null;
        server.use(
            http.get("/api/users", ({ request }) => {
                searchedEmail = new URL(request.url).searchParams.get("f_email");
            }),
        );
        multiselect(wrapper, "role-users").vm.$emit("search-change", "alice");
        await flushPromises();
        expect(searchedEmail).toBe("alice");
        await openDropdown(wrapper, "role-users");
        expect(wrapper.find("#role-users").text()).toContain(ROLE_MEMBER.email);
    });

    it("shows the API error if creation fails", async () => {
        const { wrapper, router, formPage } = await mountRoleForm(stories.NewRoleNameTaken);
        await wrapper.find("#role-name").setValue(ROLE_NAME);
        await wrapper.find("#role-description").setValue("Test Description");
        await submit(wrapper);
        expect(wrapper.findComponent({ name: "GAlert" }).text()).toContain(
            `Failed to create role: A role with that name already exists [${ROLE_NAME}]`,
        );
        expect(router.currentRoute.value.path).toBe(formPage);
    });
});

describe("RoleForm.vue edit mode", () => {
    it("loads the role and its associations", async () => {
        const { wrapper } = await mountRoleForm(stories.ExistingRole);
        expect(wrapper.find("#role-name").element).toHaveProperty("value", ROLE_NAME);
        expect(wrapper.find("#role-description").element).toHaveProperty("value", ROLE_DESCRIPTION);
        expect(wrapper.find("#role-type").exists()).toBe(false);
        expect(selectedTags(wrapper, "role-users")).toEqual([ROLE_MEMBER.email]);
        expect(selectedTags(wrapper, "role-groups")).toEqual([ROLE_GROUP.name]);
    });

    it("titles the form with the saved name while the name is edited", async () => {
        const { wrapper } = await mountRoleForm(stories.ExistingRole);
        await wrapper.find("#role-name").setValue("Renamed Role");
        expect(wrapper.text()).toContain(`Role '${ROLE_NAME}'`);
    });

    it("saves changes with PUT", async () => {
        const { wrapper, router } = await mountRoleForm(stories.ExistingRole);
        const requests = captureRequests();
        await wrapper.find("#role-name").setValue("Renamed Role");
        multiselect(wrapper, "role-users").vm.$emit("update:modelValue", []);
        multiselect(wrapper, "role-groups").vm.$emit("update:modelValue", [ROLE_GROUP, OTHER_GROUP]);
        await submit(wrapper);
        expect(requests.put).toEqual([
            {
                name: "Renamed Role",
                description: ROLE_DESCRIPTION,
                group_ids: [ROLE_GROUP.id, OTHER_GROUP.id],
                user_ids: [],
            },
        ]);
        expect(router.currentRoute.value.path).toBe("/admin/roles");
    });

    it("saves a role without a description", async () => {
        const { wrapper } = await mountRoleForm(stories.ExistingRole);
        const requests = captureRequests();
        await wrapper.find("#role-description").setValue("");
        await submit(wrapper);
        expect(requests.put).toMatchObject([{ description: "" }]);
    });

    it("cannot be saved when loading fails", async () => {
        const { wrapper } = await mountRoleForm(stories.ExistingRoleGone);
        expect(wrapper.findComponent({ name: "GAlert" }).text()).toContain(
            "No accessible role found with the id provided.",
        );
        expect(wrapper.find("#role-submit").exists()).toBe(false);
    });

    it("shows the API error if the update fails", async () => {
        const { wrapper, router, formPage } = await mountRoleForm(stories.ExistingRoleNameTaken);
        await wrapper.find("#role-name").setValue("Teaching assistants");
        await submit(wrapper);
        expect(wrapper.findComponent({ name: "GAlert" }).text()).toContain(
            "Failed to update role: A role with that name already exists [Teaching assistants]",
        );
        expect(router.currentRoute.value.path).toBe(formPage);
    });
});
