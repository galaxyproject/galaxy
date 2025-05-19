import { createTestingPinia } from "@pinia/testing";
import { createLocalVue, shallowMount } from "@vue/test-utils";
import BootstrapVue from "bootstrap-vue";
import { setActivePinia } from "pinia";
import { ref } from "vue";

import ExternalRegistration from "./ExternalRegistration.vue";

jest.mock("@/stores/configurationStore", () => {
    // Whatever shape your components expect:
    const configStub = {
        allow_local_account_creation: true,
        enable_oidc: false,
        // …add more keys only if a failing test complains …
    };

    return {
        useConfigStore: () => ({
            /* Pinia "state" */
            config: { value: configStub },

            /* getters */
            isLoaded: true,

            /* actions – stubbed so nothing happens */
            loadConfig: jest.fn(),
            setConfiguration: jest.fn(),
        }),
    };
});

/* ------------------------------------------------------------------ */
/* 0.  Global fetch stub – executed BEFORE any component code imports */
if (!global.fetch) {
    global.fetch = jest.fn(() =>
        Promise.resolve({
            ok: true,
            json: () => Promise.resolve({}),
        }),
    ) as unknown as typeof global.fetch;
}

/* 1.  Vue 2.7 helpers ------------------------------------------------ */
const localVue = createLocalVue();
localVue.use(BootstrapVue);

/* 2.  Mock openUrl so navigation doesn’t fire ----------------------- */
jest.mock("@/composables/openurl", () => ({
    useOpenUrl: () => ({ openUrl: jest.fn() }),
}));

/* 3.  Mock useConfig – mutable stub per test ------------------------ */
// Keep a SINGLE object reference that we mutate between tests.
const oidcConfigStub: Record<string, any> = {};
jest.mock("@/composables/config", () => ({
    useConfig: () => ({
        // make it look like the real composable: a ref
        config: ref({ oidc: oidcConfigStub }),
        isConfigLoaded: ref(true),
    }),
}));

/* 4.  Helper to mount component with a specific OIDC config --------- */
function mountExtReg(cfg: object, disableLocalAccounts = false) {
    // clear previous keys then copy new ones (keeps reference stable)
    Object.keys(oidcConfigStub).forEach((k) => delete oidcConfigStub[k]);
    Object.assign(oidcConfigStub, cfg);

    const pinia = createTestingPinia();
    setActivePinia(pinia);

    return shallowMount(ExternalRegistration as object, {
        localVue,
        pinia,
        propsData: { disableLocalAccounts },
        stubs: {
            BAlert: true,
            BButton: true,
            BForm: true,
            BFormCheckbox: true,
            BFormGroup: true,
        },
    });
}

/* 5.  Cases ---------------------------------------------------------- */
const cases = [
    {
        name: "no OIDC providers",
        cfg: {},
        disableLocal: true,
        wantButtons: 0,
        wantHr: 0,
    },
    {
        name: "provider w/o registration endpoint",
        cfg: {
            example: { label: "Example", icon: "icon-example" },
        },
        disableLocal: false,
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
        disableLocal: false,
        wantButtons: 1,
        wantHr: 1,
    },
    {
        name: "provider with custom text",
        cfg: {
            "custom-idp": {
                custom_button_text: "Join Custom",
                end_user_registration_endpoint: "https://idp/custom/reg",
            },
        },
        disableLocal: false,
        wantButtons: 1,
        wantHr: 1,
    },
    {
        name: "provider with label only",
        cfg: {
            "label-idp": {
                label: "Label IDP",
                end_user_registration_endpoint: "https://idp/label/reg",
            },
        },
        disableLocal: false,
        wantButtons: 1,
        wantHr: 1,
    },
] as const;

/* 6.  Table-driven test --------------------------------------------- */
describe("ExternalRegistration – OIDC rendering", () => {
    it.each(cases)("%s", ({ cfg, disableLocal, wantButtons, wantHr }) => {
        const wrapper = mountExtReg(cfg, disableLocal);

        expect(wrapper.findAllComponents({ name: "BButton" }).length).toBe(wantButtons);
        expect(wrapper.findAll("hr").length).toBe(wantHr);
    });
});
