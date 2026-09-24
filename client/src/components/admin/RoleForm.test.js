import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import Multiselect from "vue-multiselect";

import { useServerMock } from "@/api/client/__mocks__";

import RoleForm from "./RoleForm.vue";

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args) => mockPush(...args),
    }),
}));

vi.mock("@/composables/filter/filter.js", () => {
    const { ref } = require("vue");
    return {
        useFilterObjectArray: () => ({ filtered: ref([]), pending: ref(false) }),
    };
});

function mountTarget() {
    setActivePinia(createPinia());
    return mount(RoleForm, {
        localVue,
        stubs: {
            FontAwesomeIcon: true,
            FormSelection: true,
            GButton: true,
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

    it("shows validation error if required fields are missing", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([])));
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
        let postedBody;
        server.use(
            http.post("/api/roles", async ({ request, response }) => {
                postedBody = await request.json();
                return response(200).json({ id: "new-role" });
            }),
        );
        const wrapper = mountTarget();
        await flushPromises();
        await wrapper.find("#role-name").setValue("Test Role");
        await wrapper.find("#role-description").setValue("Test Description");
        wrapper.vm.selectedGroups = [{ id: "g1", name: "Group 1" }];
        wrapper.vm.selectedUsers = [{ id: "u1", email: "user1@example.org" }];
        await wrapper.find("#role-submit").trigger("click");
        await flushPromises();
        expect(postedBody.name).toBe("Test Role");
        expect(postedBody.description).toBe("Test Description");
        expect(postedBody.group_ids).toEqual(["g1"]);
        expect(postedBody.user_ids).toEqual(["u1"]);
        expect(mockPush).toHaveBeenCalledWith("/admin/roles");
    });

    it("offers users from the user search, not roles", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([])));
        let searchedEmail;
        server.use(
            http.get("/api/users", ({ request, response }) => {
                searchedEmail = new URL(request.url).searchParams.get("f_email");
                return response(200).json([{ id: "u1", email: "user1@example.org" }]);
            }),
        );
        const wrapper = mountTarget();
        await flushPromises();
        wrapper.find("#role-users").findComponent(Multiselect).vm.$emit("search-change", "user1");
        await flushPromises();
        expect(searchedEmail).toBe("user1");
        expect(wrapper.find("#role-users").text()).toContain("user1@example.org");
    });

    it("shows API error if creation fails", async () => {
        server.use(http.get("/api/groups", ({ response }) => response(200).json([])));
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
