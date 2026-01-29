import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";

import RoleForm from "./RoleForm.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = jest.fn();

jest.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args) => mockPush(...args),
    }),
}));

jest.mock("@/composables/filter/filter.js", () => {
    const { ref } = require("vue");
    return {
        useFilterObjectArray: () => ref([]),
    };
});

function mountTarget() {
    setActivePinia(createPinia());
    return mount(RoleForm, {
        localVue,
        stubs: {
            FontAwesomeIcon: true,
            FormSelection: true,
            BButton: true,
            BAlert: true,
        },
        directives: {
            localize: () => {},
        },
    });
}

describe("RoleForm.vue", () => {
    it("renders loading spinner initially", async () => {
        const wrapper = mountTarget();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
    });

    it("shows error alert if groups fetch fails", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(500).json({ err_msg: "Groups failed" })));
        const wrapper = mountTarget();
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Groups failed");
    });

    it("shows error alert if roles fetch fails", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([{ id: "g1", name: "Group 1" }])));
        server.use(http.get("/api/roles", ({ response }) => response(500).json({ err_msg: "Roles failed" })));
        const wrapper = mountTarget();
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Roles failed");
    });

    it("shows validation error if required fields are missing", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([])));
        server.use(http.get("/api/roles", ({ response }) => response(200).json([])));
        const wrapper = mountTarget();
        await flushPromises();
        await wrapper.find("#role-submit").trigger("click");
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Please complete all required inputs.");
    });

    it("submits with correct data", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([{ id: "g1", name: "Group 1" }])));
        server.use(http.get("/api/roles", ({ response }) => response(200).json([{ id: "u1", name: "User 1" }])));
        server.use(
            http.post("/api/roles", async ({ request, response }) => {
                const body = await request.json();
                expect(body.name).toBe("Test Role");
                expect(body.description).toBe("Test Description");
                expect(body.group_ids).toEqual(["g1"]);
                expect(body.user_ids).toEqual(["u1"]);
                return response(200).json({ id: "new-role" });
            }),
        );
        const wrapper = mountTarget();
        await flushPromises();
        await wrapper.find("#role-name").setValue("Test Role");
        await wrapper.find("#role-description").setValue("Test Description");
        wrapper.vm.groupIds = ["g1"];
        wrapper.vm.userIds = ["u1"];
        await wrapper.find("#role-submit").trigger("click");
        await flushPromises();
        expect(mockPush).toHaveBeenCalledWith("/admin/roles");
    });

    it("shows API error if creation fails", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([])));
        server.use(http.get("/api/roles", ({ response }) => response(200).json([])));
        server.use(http.post("/api/roles", ({ response }) => response(400).json({ err_msg: "Creation failed" })));
        const wrapper = mountTarget();
        await flushPromises();
        await wrapper.find("#role-name").setValue("Bad Role");
        await wrapper.find("#role-description").setValue("Bad Description");
        await wrapper.find("#role-submit").trigger("click");
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Failed to create role");
    });
});
