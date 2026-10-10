import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import GroupForm from "./GroupForm.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

enableAutoUnmount(afterEach);

const GROUP = { id: "g1", name: "Group 1", url: "/api/groups/g1", model_class: "Group" as const };
const GROUP_USER = { id: "u1", email: "user1@example.org", url: "/api/groups/g1/users/u1" };
const GROUP_ROLE = { id: "r1", name: "Role 1", url: "/api/groups/g1/roles/r1" };

const SELECTORS = {
    NAME_INPUT: "#admin-group-name-input",
    SUBMIT: "#admin-group-submit",
};

function serveGroup() {
    server.use(
        http.get("/api/groups/{group_id}", ({ response }) => response(200).json(GROUP)),
        http.get("/api/groups/{group_id}/users", ({ response }) => response(200).json([GROUP_USER])),
        http.get("/api/groups/{group_id}/roles", ({ response }) => response(200).json([GROUP_ROLE])),
    );
}

function captureUpdate() {
    const requests: unknown[] = [];
    server.use(
        http.put("/api/groups/{group_id}", async ({ request, response }) => {
            requests.push(await request.json());
            return response(200).json({ ...GROUP, name: "Renamed" });
        }),
    );
    return requests;
}

async function mountGroupForm() {
    const wrapper = mount(GroupForm, {
        props: { groupId: GROUP.id },
        global: { ...localVue, stubs: { ...localVue.stubs, FontAwesomeIcon: true } },
    });
    await flushPromises();
    return wrapper;
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.SUBMIT).trigger("click");
    await flushPromises();
}

describe("GroupForm edit mode", () => {
    beforeEach(() => {
        mockPush.mockClear();
        serveGroup();
    });

    it("keeps the saved group name in the title while the name is edited", async () => {
        const wrapper = await mountGroupForm();
        expect(wrapper.text()).toContain("Group 'Group 1'");

        await wrapper.find(SELECTORS.NAME_INPUT).setValue("Renamed");

        expect(wrapper.text()).toContain("Group 'Group 1'");
    });

    it("renames a group together with its associations", async () => {
        const requests = captureUpdate();
        const wrapper = await mountGroupForm();

        await wrapper.find(SELECTORS.NAME_INPUT).setValue("Renamed");
        await submit(wrapper);

        expect(requests).toEqual([{ name: "Renamed", user_ids: ["u1"], role_ids: ["r1"] }]);
        expect(mockPush).toHaveBeenCalledWith("/admin/groups");
    });

    it("does not save an empty name", async () => {
        const requests = captureUpdate();
        const wrapper = await mountGroupForm();

        await wrapper.find(SELECTORS.NAME_INPUT).setValue("");
        await submit(wrapper);

        expect(wrapper.text()).toContain("Please enter a group name.");
        expect(requests).toEqual([]);
        expect(mockPush).not.toHaveBeenCalled();
    });

    it.each([
        { path: "/api/groups/{group_id}", message: "Group failed" },
        { path: "/api/groups/{group_id}/users", message: "Users failed" },
        { path: "/api/groups/{group_id}/roles", message: "Roles failed" },
    ] as const)("cannot be saved when $path fails to load", async ({ path, message }) => {
        server.use(
            http.get(path, ({ response }) =>
                response("5XX").json({ err_msg: message, err_code: 500 }, { status: 500 }),
            ),
        );

        const wrapper = await mountGroupForm();

        expect(wrapper.text()).toContain(message);
        expect(wrapper.find(SELECTORS.SUBMIT).exists()).toBe(false);
    });
});
