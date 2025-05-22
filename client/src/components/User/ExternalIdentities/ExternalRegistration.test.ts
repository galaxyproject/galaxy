import { createTestingPinia } from "@pinia/testing";
import { createLocalVue, shallowMount } from "@vue/test-utils";

import { getOIDCIdpsWithRegistration, type OIDCConfig } from "./ExternalIDHelper";

import ExternalRegistration from "./ExternalRegistration.vue";

const localVue = createLocalVue();

/* Helper to mount component with a specific OIDC config --------- */
function mountExtReg(cfg: object) {
    const pinia = createTestingPinia();

    const idpsWithRegistration = getOIDCIdpsWithRegistration(cfg as OIDCConfig);
    return shallowMount(ExternalRegistration as object, {
        localVue,
        pinia,
        propsData: { idpsWithRegistration },
        stubs: {
            BAlert: true,
            BButton: true,
            BForm: true,
            BFormCheckbox: true,
            BFormGroup: true,
        },
    });
}

/* Cases ---------------------------------------------------------- */
const cases = [
    {
        name: "no OIDC providers",
        cfg: {},
        wantButtons: 0,
        wantHr: 0,
    },
    {
        name: "provider w/o registration endpoint",
        cfg: {
            example: { label: "Example", icon: "icon-example" },
        },
        wantButtons: 0,
        wantHr: 0,
    },
    {
        name: "provider with icon",
        cfg: {
            "icon-idp": {
                icon: "icon.png",
                end_user_registration_endpoint: "https://idp/icon/reg",
            },
        },
        wantButtons: 1,
    },
    {
        name: "provider with custom text",
        cfg: {
            "custom-idp": {
                custom_button_text: "Join Custom",
                end_user_registration_endpoint: "https://idp/custom/reg",
            },
        },
        wantButtons: 1,
    },
    {
        name: "provider with label only",
        cfg: {
            "label-idp": {
                label: "Label IDP",
                end_user_registration_endpoint: "https://idp/label/reg",
            },
        },
        wantButtons: 1,
    },
] as const;

/* Table-driven test --------------------------------------------- */
describe("ExternalRegistration – OIDC rendering", () => {
    it.each(cases)("$name", ({ cfg, wantButtons }) => {
        const wrapper = mountExtReg(cfg);

        expect(wrapper.findAll("[data-description='registration button']").length).toBe(wantButtons);
    });
});
