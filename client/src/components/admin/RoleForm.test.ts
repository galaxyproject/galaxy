import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import Multiselect from "vue-multiselect";

import { useServerMock } from "@/api/client/__mocks__";

import RoleForm from "./RoleForm.vue";
import FormSelection from "@/components/Form/Elements/FormSelection.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

// FormSelection filters its options in a web worker, which the test environment does not provide.
vi.mock("@/composables/filter/filter.js", async () => {
    const { ref } = await import("vue");
    return {
        useFilterObjectArray: () => ({ filtered: ref([]), pending: ref(false) }),
    };
});

function useGroups(groups = [{ id: "g1", name: "Group 1", url: "/api/groups/g1", model_class: "Group" as const }]) {
    server.use(http.get("/api/groups", ({ response }) => response(200).json(groups)));
}

function captureRequests() {
    const requests: { put: unknown[]; post: unknown[] } = { put: [], post: [] };
    const role = { id: "r1", name: "Role", type: "admin", description: "", url: "/api/roles/r1", model_class: "Role" };
    server.use(
        http.post("/api/roles", async ({ request, response }) => {
            requests.post.push(await request.json());
            return response(200).json({ ...role, model_class: "Role" as const });
        }),
        http.put("/api/roles/{id}", async ({ request, response }) => {
            requests.put.push(await request.json());
            return response(200).json({ ...role, model_class: "Role" as const });
        }),
    );
    return requests;
}

async function mountTarget(propsData: { roleId?: string } = {}) {
    const wrapper = mount(RoleForm as object, {
        localVue,
        propsData,
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
    await wrapper.find("#role-submit").trigger("click");
    await flushPromises();
}

beforeEach(() => {
    // FormSelection reads a Pinia store.
    setActivePinia(createPinia());
    mockPush.mockClear();
});

describe("RoleForm.vue create mode", () => {
    it("shows a loading spinner until the groups are loaded", async () => {
        useGroups();
        const wrapper = mount(RoleForm as object, { localVue, stubs: { FontAwesomeIcon: true } });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
        expect(wrapper.find("#role-submit").exists()).toBe(true);
    });

    it("shows the error and cannot be saved if the groups fail to load", async () => {
        server.use(
            http.get("/api/groups", ({ response }) =>
                response("5XX").json({ err_msg: "Groups failed", err_code: 500 }, { status: 500 }),
            ),
        );
        const wrapper = await mountTarget();
        expect(wrapper.findComponent({ name: "BAlert" }).text()).toContain("Groups failed");
        expect(wrapper.find("#role-submit").exists()).toBe(false);
    });

    it("requires a name and a description", async () => {
        useGroups();
        const requests = captureRequests();
        const wrapper = await mountTarget();
        await submit(wrapper);
        expect(wrapper.findComponent({ name: "BAlert" }).text()).toContain("Please complete all required inputs.");
        expect(requests.post).toEqual([]);
    });

    it("creates a role with the chosen type, groups and users", async () => {
        useGroups();
        const requests = captureRequests();
        const wrapper = await mountTarget();
        await wrapper.find("#role-name").setValue("Test Role");
        await wrapper.find("#role-description").setValue("Test Description");
        const roleType = wrapper
            .findAllComponents(FormSelection)
            .wrappers.find((w) => w.attributes("id") === "role-type");
        roleType!.vm.$emit("input", "user_tool_execute");
        multiselect(wrapper, "role-groups").vm.$emit("input", [{ id: "g1", name: "Group 1" }]);
        multiselect(wrapper, "role-users").vm.$emit("input", [{ id: "u1", email: "user1@example.org" }]);
        await submit(wrapper);
        expect(requests.post).toEqual([
            {
                name: "Test Role",
                description: "Test Description",
                group_ids: ["g1"],
                user_ids: ["u1"],
                role_type: "user_tool_execute",
            },
        ]);
        expect(mockPush).toHaveBeenCalledWith("/admin/roles");
    });

    it("searches users by email", async () => {
        useGroups();
        let searchedEmail: string | null = null;
        server.use(
            http.get("/api/users", ({ request, response }) => {
                searchedEmail = new URL(request.url).searchParams.get("f_email");
                return response(200).json([{ id: "u1", email: "user1@example.org", username: "user1" }]);
            }),
        );
        const wrapper = await mountTarget();
        multiselect(wrapper, "role-users").vm.$emit("search-change", "user1");
        await flushPromises();
        expect(searchedEmail).toBe("user1");
        expect(wrapper.find("#role-users").text()).toContain("user1@example.org");
    });

    it("shows the API error if creation fails", async () => {
        useGroups();
        server.use(
            http.post("/api/roles", ({ response }) =>
                response("4XX").json({ err_msg: "Creation failed", err_code: 400 }, { status: 400 }),
            ),
        );
        const wrapper = await mountTarget();
        await wrapper.find("#role-name").setValue("Bad Role");
        await wrapper.find("#role-description").setValue("Bad Description");
        await submit(wrapper);
        expect(wrapper.findComponent({ name: "BAlert" }).text()).toContain("Failed to create role: Creation failed");
        expect(mockPush).not.toHaveBeenCalled();
    });
});

describe("RoleForm.vue edit mode", () => {
    function useRoleHandlers() {
        useGroups([
            { id: "g1", name: "Group 1", url: "/api/groups/g1", model_class: "Group" },
            { id: "g2", name: "Group 2", url: "/api/groups/g2", model_class: "Group" },
        ]);
        server.use(
            http.get("/api/roles/{id}", ({ response }) =>
                response(200).json({
                    id: "r1",
                    name: "Existing Role",
                    description: "Existing Description",
                    type: "admin",
                    url: "/api/roles/r1",
                    model_class: "Role",
                }),
            ),
            http.get("/api/roles/{id}/users", ({ response }) =>
                response(200).json([{ id: "u1", email: "user1@example.org" }]),
            ),
            http.get("/api/roles/{id}/groups", ({ response }) =>
                response(200).json([{ id: "g1", name: "Group 1", model_class: "Group" }]),
            ),
        );
    }

    it("loads the role and its associations", async () => {
        useRoleHandlers();
        const wrapper = await mountTarget({ roleId: "r1" });
        expect(wrapper.find("#role-name").element).toHaveProperty("value", "Existing Role");
        expect(wrapper.find("#role-description").element).toHaveProperty("value", "Existing Description");
        expect(wrapper.find("#role-type").exists()).toBe(false);
        expect(selectedTags(wrapper, "role-users")).toEqual(["user1@example.org"]);
        expect(selectedTags(wrapper, "role-groups")).toEqual(["Group 1"]);
    });

    it("titles the form with the saved name while the name is edited", async () => {
        useRoleHandlers();
        const wrapper = await mountTarget({ roleId: "r1" });
        await wrapper.find("#role-name").setValue("Renamed Role");
        expect(wrapper.text()).toContain("Role 'Existing Role'");
    });

    it("saves changes with PUT", async () => {
        useRoleHandlers();
        const requests = captureRequests();
        const wrapper = await mountTarget({ roleId: "r1" });
        await wrapper.find("#role-name").setValue("Renamed Role");
        multiselect(wrapper, "role-users").vm.$emit("input", []);
        multiselect(wrapper, "role-groups").vm.$emit("input", [
            { id: "g1", name: "Group 1" },
            { id: "g2", name: "Group 2" },
        ]);
        await submit(wrapper);
        expect(requests.put).toEqual([
            {
                name: "Renamed Role",
                description: "Existing Description",
                group_ids: ["g1", "g2"],
                user_ids: [],
            },
        ]);
        expect(mockPush).toHaveBeenCalledWith("/admin/roles");
    });

    it("saves a role without a description", async () => {
        useRoleHandlers();
        const requests = captureRequests();
        const wrapper = await mountTarget({ roleId: "r1" });
        await wrapper.find("#role-description").setValue("");
        await submit(wrapper);
        expect(requests.put).toMatchObject([{ description: "" }]);
    });

    it("cannot be saved when loading fails", async () => {
        useRoleHandlers();
        server.use(
            http.get("/api/roles/{id}/users", ({ response }) =>
                response("5XX").json({ err_msg: "Users failed", err_code: 500 }, { status: 500 }),
            ),
        );
        const wrapper = await mountTarget({ roleId: "r1" });
        expect(wrapper.findComponent({ name: "BAlert" }).text()).toContain("Users failed");
        expect(wrapper.find("#role-submit").exists()).toBe(false);
    });

    it("shows the API error if the update fails", async () => {
        useRoleHandlers();
        server.use(
            http.put("/api/roles/{id}", ({ response }) =>
                response("4XX").json({ err_msg: "Name taken", err_code: 409 }, { status: 409 }),
            ),
        );
        const wrapper = await mountTarget({ roleId: "r1" });
        await submit(wrapper);
        expect(wrapper.findComponent({ name: "BAlert" }).text()).toContain("Name taken");
        expect(mockPush).not.toHaveBeenCalled();
    });
});
