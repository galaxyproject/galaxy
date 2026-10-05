import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import axios from "axios";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";

import { getRecryptServiceUrl, useDatasetProtection } from "./datasetProtection";

vi.mock("axios");
vi.mock("@/composables/toast", () => {
    const toast = { error: vi.fn(), success: vi.fn() };
    return { Toast: toast, useToast: () => toast };
});

const PROTECTION_ROUTE = "/api/datasets/{dataset_id}/protection";
const SERVICE_URL = "https://localhost:61357";
const NOT_READY = { protected: true, scheme: "crypt4gh", ready: false, expires_at: null };
const READY = { protected: true, scheme: "crypt4gh", ready: true, expires_at: "2026-10-10T12:00:00" };

const { server, http } = useServerMock();

function mountWithProtection(protectedDataset = true, extraPreferences: string | null = null) {
    const TestComponent = defineComponent({
        setup() {
            const { status, authorize } = useDatasetProtection(ref("dataset_id"), ref(protectedDataset));
            function onAuthorize() {
                authorize("user-header");
            }
            return { status, onAuthorize };
        },
        template: `
<div>
  <span class="ready">{{ status ? status.ready : "none" }}</span>
  <button class="authorize" @click="onAuthorize" />
</div>`,
    });
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        stubActions: false,
        initialState: {
            configurationStore: { config: { crypt4gh_user_service_url: SERVICE_URL }, isLoaded: true },
            userStore: { currentPreferences: { extra_user_preferences: extraPreferences } },
        },
    });
    return mount(TestComponent, { global: { plugins: [pinia] } });
}

describe("getRecryptServiceUrl", () => {
    it("uses the configured service", () => {
        expect(getRecryptServiceUrl(SERVICE_URL, undefined)).toBe("https://localhost:61357/recrypt_header");
    });

    it("lets users override the port", () => {
        const preferences = JSON.stringify({ "crypt4gh_recrypt_service|port": "8443" });
        expect(getRecryptServiceUrl(`${SERVICE_URL}/`, preferences)).toBe("https://localhost:8443/recrypt_header");
    });
});

describe("useDatasetProtection", () => {
    let grantBodies: unknown[];

    beforeEach(() => {
        grantBodies = [];
        server.use(
            http.get(PROTECTION_ROUTE, ({ response }) => response(200).json(NOT_READY)),
            http.put(PROTECTION_ROUTE, async ({ request, response }) => {
                grantBodies.push(await request.json());
                return response(200).json(READY);
            }),
        );
    });

    afterEach(() => vi.clearAllMocks());

    it("loads the status of protected datasets", async () => {
        const wrapper = mountWithProtection();
        await flushPromises();
        expect(wrapper.find(".ready").text()).toBe("false");
    });

    it("does not request a status for unprotected datasets", async () => {
        const wrapper = mountWithProtection(false);
        await flushPromises();
        expect(wrapper.find(".ready").text()).toBe("none");
    });

    it("registers the recryptor service result as a grant", async () => {
        vi.mocked(axios.post).mockResolvedValue({
            data: {
                crypt4gh_header: "compute-header",
                crypt4gh_compute_keypair_id: "cnk:1234",
                crypt4gh_compute_keypair_expiration_date: "2026-10-10T12:00:00+00:00",
            },
        });
        const wrapper = mountWithProtection(true, JSON.stringify({ "crypt4gh_recrypt_service|port": "9000" }));
        await flushPromises();

        await wrapper.find(".authorize").trigger("click");
        await flushPromises();

        expect(axios.post).toHaveBeenCalledWith("https://localhost:9000/recrypt_header", {
            crypt4gh_header: "user-header",
        });
        expect(grantBodies).toEqual([
            {
                scheme: "crypt4gh",
                crypt4gh_compute_header: "compute-header",
                crypt4gh_compute_keypair_id: "cnk:1234",
                crypt4gh_compute_keypair_expiration_date: "2026-10-10T12:00:00+00:00",
            },
        ]);
        expect(wrapper.find(".ready").text()).toBe("true");
    });

    it("does not register anything when the recryptor service fails", async () => {
        vi.mocked(axios.post).mockRejectedValue(new Error("Network Error"));
        const wrapper = mountWithProtection();
        await flushPromises();

        await wrapper.find(".authorize").trigger("click");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalled();
        expect(grantBodies).toEqual([]);
        expect(wrapper.find(".ready").text()).toBe("false");
    });
});
