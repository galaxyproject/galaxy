import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import GroupForm from "./GroupForm.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

function useGroupHandlers() {
    server.use(
        http.get("/api/groups/{group_id}", ({ response }) =>
            response(200).json({ id: "g1", name: "Group 1", url: "/api/groups/g1", model_class: "Group" }),
        ),
        http.get("/api/groups/{group_id}/users", ({ response }) =>
            response(200).json([{ id: "u1", email: "user1@example.org", url: "/api/groups/g1/users/u1" }]),
        ),
        http.get("/api/groups/{group_id}/roles", ({ response }) =>
            response(200).json([{ id: "r1", name: "Role 1", url: "/api/groups/g1/roles/r1" }]),
        ),
    );
}

function captureUpdate() {
    const requests: unknown[] = [];
    server.use(
        http.put("/api/groups/{group_id}", async ({ request, response }) => {
            requests.push(await request.json());
            return response(200).json({ id: "g1", name: "Renamed", url: "/api/groups/g1", model_class: "Group" });
        }),
    );
    return requests;
}

async function mountTarget() {
    const wrapper = mount(GroupForm as object, {
        localVue,
        propsData: { groupId: "g1" },
        stubs: { FontAwesomeIcon: true },
    });
    await flushPromises();
    return wrapper;
}

async function submit(wrapper: Wrapper<Vue>) {
    await wrapper.find("#admin-group-submit").trigger("click");
    await flushPromises();
}

describe("GroupForm.vue edit mode", () => {
    beforeEach(() => {
        mockPush.mockClear();
    });

    it("renames a group together with its associations", async () => {
        useGroupHandlers();
        const requests = captureUpdate();
        const wrapper = await mountTarget();
        expect(wrapper.text()).toContain("Group 'Group 1'");
        await wrapper.find("#admin-group-name-input").setValue("Renamed");
        expect(wrapper.text()).toContain("Group 'Group 1'");
        await submit(wrapper);
        expect(requests).toEqual([{ name: "Renamed", user_ids: ["u1"], role_ids: ["r1"] }]);
        expect(mockPush).toHaveBeenCalledWith("/admin/groups");
    });

    it("does not save an empty name", async () => {
        useGroupHandlers();
        const requests = captureUpdate();
        const wrapper = await mountTarget();
        await wrapper.find("#admin-group-name-input").setValue("");
        await submit(wrapper);
        expect(wrapper.text()).toContain("Please enter a group name.");
        expect(requests).toEqual([]);
        expect(mockPush).not.toHaveBeenCalled();
    });

    it("cannot be saved when the group's users fail to load", async () => {
        useGroupHandlers();
        server.use(
            http.get("/api/groups/{group_id}/users", ({ response }) =>
                response("5XX").json({ err_msg: "Users failed", err_code: 500 }, { status: 500 }),
            ),
        );
        const wrapper = await mountTarget();
        expect(wrapper.text()).toContain("Users failed");
        expect(wrapper.find("#admin-group-submit").exists()).toBe(false);
    });
});
