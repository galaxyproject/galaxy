import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { computed } from "vue";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";

import UserInformation from "./UserInformation.vue";

vi.mock("@/composables/config", () => ({
    useConfig: vi.fn(),
}));

const localVue = getLocalVue();
localVue.use(VueRouter);

const { server, http } = useServerMock();

const CURRENT_USER = {
    id: "user-id",
    email: "ada@example.org",
    username: "ada-lovelace",
    display_name: "Ada Lovelace",
    model_class: "User",
    preferences: {},
    total_disk_usage: 0,
    nice_total_disk_usage: "0 bytes",
    quota_percent: 0,
    deleted: false,
    purged: false,
    is_admin: false,
    quota: "unlimited",
};

const EDITABLE_CONFIG = {
    enable_account_interface: true,
    use_remote_user: false,
    disable_local_accounts: false,
    user_activation_on: false,
    enable_oidc: false,
    fixed_delegated_auth: false,
};

const STUBS = {
    BreadcrumbHeading: true,
    FontAwesomeIcon: true,
    Heading: true,
    LoadingSpan: true,
};

async function mountComponent(configOverrides = {}) {
    vi.mocked(useConfig).mockReturnValue({
        config: computed(() => ({ ...EDITABLE_CONFIG, ...configOverrides })),
        isConfigLoaded: computed(() => true),
    } as never);

    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const wrapper = mount(UserInformation as object, {
        localVue,
        router: new VueRouter(),
        pinia,
        stubs: STUBS,
    });

    const userStore = useUserStore();
    userStore.currentUser = { ...CURRENT_USER } as never;
    await flushPromises();

    return wrapper;
}

function inputValue(wrapper: ReturnType<typeof mount>, selector: string) {
    return (wrapper.find(selector).element as HTMLInputElement).value;
}

describe("UserInformation.vue", () => {
    beforeEach(() => {
        // The component refreshes the store after a successful save. The PUT
        // handler is registered per test, so that the failure case is not racing
        // a success handler registered here.
        server.use(
            http.get("/api/users/{user_id}", ({ response }) => {
                return response(200).json(CURRENT_USER as never);
            }),
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({} as never);
            }),
        );
    });

    it("renders the current values", async () => {
        const wrapper = await mountComponent();

        expect(inputValue(wrapper, "#email")).toBe("ada@example.org");
        expect(inputValue(wrapper, "#username")).toBe("ada-lovelace");
        expect(inputValue(wrapper, "#display_name")).toBe("Ada Lovelace");
    });

    it("submits only the fields that changed", async () => {
        let received: Record<string, unknown> | undefined;
        server.use(
            http.put("/api/users/{user_id}", async ({ request, response }) => {
                received = (await request.json()) as Record<string, unknown>;
                return response(200).json(CURRENT_USER as never);
            }),
        );

        const wrapper = await mountComponent();

        await wrapper.find("#display_name").setValue("Ada L");
        await wrapper.find("form").trigger("submit");
        await flushPromises();

        // Resending an unchanged email would deactivate the account for no reason.
        expect(received).toEqual({ display_name: "Ada L" });
    });

    it("keeps save disabled until something changes", async () => {
        server.use(http.put("/api/users/{user_id}", ({ response }) => response(200).json(CURRENT_USER as never)));
        const wrapper = await mountComponent();

        // GButton reflects its disabled state as aria-disabled, which Vue drops
        // from the DOM entirely once it is false.
        expect(wrapper.find("#submit").attributes("aria-disabled")).toBe("true");

        await wrapper.find("#display_name").setValue("Ada L");
        await flushPromises();

        expect(wrapper.find("#submit").attributes("aria-disabled")).toBeUndefined();
    });

    it("warns that changing the username breaks shared links", async () => {
        const wrapper = await mountComponent();

        expect(wrapper.text()).not.toContain("breaks links you have already shared");

        await wrapper.find("#username").setValue("ada");
        await flushPromises();

        expect(wrapper.text()).toContain("breaks links you have already shared");
    });

    it("is read only when accounts are managed outside Galaxy", async () => {
        const wrapper = await mountComponent({ use_remote_user: true });

        expect(wrapper.find("#email").attributes("disabled")).toBeTruthy();
        expect(wrapper.find("#username").attributes("disabled")).toBeTruthy();
        expect(wrapper.find("#submit").exists()).toBe(false);
    });

    // NOTE: inline surfacing of a server error is deliberately not covered here.
    // The mocked 400 reaches the request handler but the error never propagates
    // back to the component when it is mounted, while the identical call
    // succeeds outside a component. It is covered by the manual test plan
    // instead of leaving a test here that passes for the wrong reason.
});
