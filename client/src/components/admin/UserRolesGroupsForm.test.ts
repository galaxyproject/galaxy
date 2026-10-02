import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import Multiselect from "vue-multiselect";

import { useServerMock } from "@/api/client/__mocks__";

import UserRolesGroupsForm from "./UserRolesGroupsForm.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

function detailedUser(id: string, email: string) {
    return {
        id,
        email,
        username: email.split("@")[0]!,
        deleted: false,
        purged: false,
        is_admin: false,
        preferences: {},
        quota: "unlimited",
        total_disk_usage: 0,
        nice_total_disk_usage: "0 bytes",
    };
}

function role(id: string, name: string, type = "admin") {
    return { id, name, type, description: null, url: `/api/roles/${id}`, model_class: "Role" as const };
}

function group(id: string, name: string) {
    return { id, name, url: `/api/groups/${id}`, model_class: "Group" as const };
}

function useUserHandlers() {
    server.use(
        http.get("/api/users/{user_id}", ({ response }) => response(200).json(detailedUser("u1", "user1@example.org"))),
        http.get("/api/users/{user_id}/roles", ({ response }) =>
            response(200).json([role("private1", "user1@example.org", "private"), role("r1", "Role 1")]),
        ),
        http.get("/api/users/{user_id}/groups", ({ response }) =>
            response(200).json([{ id: "g1", name: "Group 1", model_class: "Group" }]),
        ),
        http.get("/api/groups", ({ response }) => response(200).json([group("g1", "Group 1"), group("g2", "Group 2")])),
    );
}

function useRoleSearch() {
    const searches: URLSearchParams[] = [];
    server.use(
        http.get("/api/roles", ({ request, response }) => {
            searches.push(new URL(request.url).searchParams);
            return response(200).json([role("r1", "Role 1"), role("qa", "QA")]);
        }),
    );
    return searches;
}

function captureSaves() {
    const bodies: { roles?: unknown; groups?: unknown } = {};
    server.use(
        http.put("/api/users/{user_id}/roles", async ({ request, response }) => {
            bodies.roles = await request.json();
            return response(200).json([]);
        }),
        http.put("/api/users/{user_id}/groups", async ({ request, response }) => {
            bodies.groups = await request.json();
            return response(200).json([]);
        }),
    );
    return bodies;
}

async function mountTarget() {
    const wrapper = mount(UserRolesGroupsForm as object, {
        localVue,
        propsData: { userId: "u1" },
        stubs: { FontAwesomeIcon: true },
    });
    await flushPromises();
    return wrapper;
}

function multiselect(wrapper: Wrapper<Vue>, id: string) {
    return wrapper.find(`#${id}`).findComponent(Multiselect);
}

function selectedTags(wrapper: Wrapper<Vue>, id: string) {
    return wrapper.findAll(`#${id} .multiselect__tag`).wrappers.map((tag) => tag.text());
}

async function submit(wrapper: Wrapper<Vue>) {
    await wrapper.find("#admin-user-roles-groups-submit").trigger("click");
    await flushPromises();
}

describe("UserRolesGroupsForm.vue", () => {
    beforeEach(() => {
        mockPush.mockClear();
    });

    it("loads the user's roles and groups without the private role", async () => {
        useUserHandlers();
        useRoleSearch();
        const wrapper = await mountTarget();
        expect(wrapper.text()).toContain("Roles and groups for 'user1@example.org'");
        expect(selectedTags(wrapper, "admin-user-roles")).toEqual(["Role 1"]);
        expect(selectedTags(wrapper, "admin-user-groups")).toEqual(["Group 1"]);
    });

    it("lists assignable roles before anything is typed", async () => {
        useUserHandlers();
        const searches = useRoleSearch();
        const wrapper = await mountTarget();
        expect(searches).toHaveLength(1);
        expect(searches[0]!.get("search")).toBeNull();
        expect(searches[0]!.get("exclude_private")).toBe("true");
        expect(wrapper.find("#admin-user-roles").text()).toContain("QA");
    });

    it("searches roles from the first character", async () => {
        useUserHandlers();
        const searches = useRoleSearch();
        const wrapper = await mountTarget();
        multiselect(wrapper, "admin-user-roles").vm.$emit("search-change", "Q");
        await flushPromises();
        expect(searches.at(-1)!.get("search")).toBe("Q");
        expect(searches.at(-1)!.get("exclude_private")).toBe("true");
    });

    it("saves the loaded roles and groups without sending the private role back", async () => {
        useUserHandlers();
        useRoleSearch();
        const bodies = captureSaves();
        const wrapper = await mountTarget();
        await submit(wrapper);
        expect(bodies.roles).toEqual({ role_ids: ["r1"] });
        expect(bodies.groups).toEqual({ group_ids: ["g1"] });
        expect(mockPush).toHaveBeenCalledWith("/admin/users");
    });

    it("saves changed selections", async () => {
        useUserHandlers();
        useRoleSearch();
        const bodies = captureSaves();
        const wrapper = await mountTarget();
        multiselect(wrapper, "admin-user-roles").vm.$emit("input", []);
        multiselect(wrapper, "admin-user-groups").vm.$emit("input", [
            { id: "g1", name: "Group 1" },
            { id: "g2", name: "Group 2" },
        ]);
        await submit(wrapper);
        expect(bodies.roles).toEqual({ role_ids: [] });
        expect(bodies.groups).toEqual({ group_ids: ["g1", "g2"] });
    });

    it("cannot be saved when loading fails", async () => {
        useUserHandlers();
        useRoleSearch();
        server.use(
            http.get("/api/users/{user_id}/groups", ({ response }) =>
                response("5XX").json({ err_msg: "Groups failed", err_code: 500 }, { status: 500 }),
            ),
        );
        const wrapper = await mountTarget();
        expect(wrapper.text()).toContain("Groups failed");
        expect(wrapper.find("#admin-user-roles-groups-submit").exists()).toBe(false);
    });

    it("stops and shows the error when saving the roles fails", async () => {
        useUserHandlers();
        useRoleSearch();
        let groupsSaved = false;
        server.use(
            http.put("/api/users/{user_id}/roles", ({ response }) =>
                response("4XX").json({ err_msg: "Invalid role", err_code: 400 }, { status: 400 }),
            ),
            http.put("/api/users/{user_id}/groups", ({ response }) => {
                groupsSaved = true;
                return response(200).json([]);
            }),
        );
        const wrapper = await mountTarget();
        await submit(wrapper);
        expect(wrapper.text()).toContain("Invalid role");
        expect(groupsSaved).toBe(false);
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("shows the error when saving the groups fails", async () => {
        useUserHandlers();
        useRoleSearch();
        server.use(
            http.put("/api/users/{user_id}/roles", ({ response }) => response(200).json([])),
            http.put("/api/users/{user_id}/groups", ({ response }) =>
                response("4XX").json({ err_msg: "Invalid group", err_code: 400 }, { status: 400 }),
            ),
        );
        const wrapper = await mountTarget();
        await submit(wrapper);
        expect(wrapper.text()).toContain("Invalid group");
        expect(mockPush).not.toHaveBeenCalled();
    });
});
