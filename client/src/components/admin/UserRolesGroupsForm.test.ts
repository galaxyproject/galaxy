import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter, nth } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import type { components } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";

import { ADMIN_GROUPS, ADMIN_ROLES, ADMIN_USER } from "./test_fixtures";
import * as UserRolesGroupsFormStories from "./UserRolesGroupsForm.stories";

const stories = composeStories(UserRolesGroupsFormStories);
const mountStory = useStoryMount();
const { server, http } = useServerMock();

/** Observe requests while the story answers them, including the initial role search. */
async function mountTarget(story: StoryOf<typeof stories> = stories.ExistingUser) {
    const router = createTestRouter();
    await router.push("/admin/form/manage_user");
    const mockPush = vi.spyOn(router, "push");
    const wrapper = mountStory(story, { router });
    const searches: URLSearchParams[] = [];
    server.use(
        http.get("/api/roles", ({ request }) => {
            searches.push(new URL(request.url).searchParams);
        }),
    );
    await flushPromises();
    return { wrapper, searches, mockPush };
}

function captureSaves() {
    const bodies: {
        roles?: components["schemas"]["UserRolesUpdatePayload"];
        groups?: components["schemas"]["UserGroupsUpdatePayload"];
    } = {};
    server.use(
        http.put("/api/users/{user_id}/roles", async ({ request }) => {
            bodies.roles = await request.clone().json();
        }),
        http.put("/api/users/{user_id}/groups", async ({ request }) => {
            bodies.groups = await request.clone().json();
        }),
    );
    return bodies;
}

function multiselect(wrapper: VueWrapper, id: string) {
    return wrapper.get(`#${id}`).getComponent(Multiselect);
}

// vue-multiselect only renders its option list once the dropdown is open.
async function openDropdown(wrapper: VueWrapper, id: string) {
    await wrapper.get(`#${id}-select`).trigger("focus");
}

function selectedTags(wrapper: VueWrapper, id: string) {
    return wrapper.findAll(`#${id} .multiselect__tag`).map((tag) => tag.text());
}

async function submit(wrapper: VueWrapper) {
    await wrapper.get("#admin-user-roles-groups-submit").trigger("click");
    await flushPromises();
}

describe("UserRolesGroupsForm.vue", () => {
    it("loads the user's roles and groups without the private role", async () => {
        const { wrapper } = await mountTarget();
        expect(wrapper.text()).toContain(`Roles and groups for '${ADMIN_USER.email}'`);
        expect(selectedTags(wrapper, "admin-user-roles")).toEqual([ADMIN_ROLES[0]!.name]);
        expect(selectedTags(wrapper, "admin-user-groups")).toEqual([ADMIN_GROUPS[0]!.name]);
    });

    it("lists assignable roles before anything is typed", async () => {
        const { wrapper, searches } = await mountTarget();
        expect(searches).toHaveLength(1);
        expect(nth(searches, 0).get("search")).toBeNull();
        expect(nth(searches, 0).get("exclude_private")).toBe("true");
        await openDropdown(wrapper, "admin-user-roles");
        expect(wrapper.get("#admin-user-roles").text()).toContain("QA");
    });

    it("searches roles from the first character", async () => {
        const { wrapper, searches } = await mountTarget();
        multiselect(wrapper, "admin-user-roles").vm.$emit("search-change", "Q");
        await flushPromises();
        expect(nth(searches, -1).get("search")).toBe("Q");
        expect(nth(searches, -1).get("exclude_private")).toBe("true");
    });

    it("saves the loaded roles and groups without sending the private role back", async () => {
        const { wrapper, mockPush } = await mountTarget();
        const bodies = captureSaves();
        await submit(wrapper);
        expect(bodies.roles).toEqual({ role_ids: [ADMIN_ROLES[0]!.id] });
        expect(bodies.groups).toEqual({ group_ids: [ADMIN_GROUPS[0]!.id] });
        expect(mockPush).toHaveBeenCalledWith("/admin/users");
    });

    it("saves changed selections", async () => {
        const { wrapper } = await mountTarget();
        const bodies = captureSaves();
        multiselect(wrapper, "admin-user-roles").vm.$emit("update:modelValue", []);
        multiselect(wrapper, "admin-user-groups").vm.$emit(
            "update:modelValue",
            ADMIN_GROUPS.map(({ id, name }) => ({ id, name })),
        );
        await submit(wrapper);
        expect(bodies.roles).toEqual({ role_ids: [] });
        expect(bodies.groups).toEqual({ group_ids: ADMIN_GROUPS.map(({ id }) => id) });
    });

    it("cannot be saved when loading fails", async () => {
        const { wrapper } = await mountTarget(stories.GroupsUnavailable);
        expect(wrapper.text()).toContain("Internal server error.");
        expect(wrapper.find("#admin-user-roles-groups-submit").exists()).toBe(false);
    });

    it("stops and shows the error when saving the roles fails", async () => {
        const { wrapper, mockPush } = await mountTarget(stories.RoleSaveDenied);
        let groupsSaved = false;
        server.use(
            http.put("/api/users/{user_id}/groups", () => {
                groupsSaved = true;
            }),
        );
        await submit(wrapper);
        expect(wrapper.text()).toContain("You must be an administrator to access this feature.");
        expect(groupsSaved).toBe(false);
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("shows the error when saving the groups fails", async () => {
        const { wrapper, mockPush } = await mountTarget(stories.UserGoneBeforeGroupSave);
        await submit(wrapper);
        expect(wrapper.text()).toContain("User not found.");
        expect(mockPush).not.toHaveBeenCalled();
    });
});
