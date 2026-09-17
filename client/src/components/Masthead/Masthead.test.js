import { faTh } from "@fortawesome/free-solid-svg-icons";
import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { PiniaVuePlugin } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useUserStore } from "@/stores/userStore";

import { loadMastheadWebhooks } from "./_webhooks";

import Masthead from "./Masthead.vue";

vi.mock("app");
vi.mock("./_webhooks");
vi.mock("vue-router/composables", () => ({
    useRoute: vi.fn(() => ({ name: "Home" })),
    useRouter: vi.fn(),
}));

const currentUser = getFakeRegisteredUser();

setupMockConfig({});

describe("Masthead.vue", () => {
    let wrapper;
    let localVue;
    let windowTab;
    let testPinia;
    let originalUrl;

    function stubLoadWebhooks(items) {
        items.push({
            id: "extension",
            title: "Extension Point",
            url: "extension_url",
        });
    }

    loadMastheadWebhooks.mockImplementation(stubLoadWebhooks);

    beforeEach(async () => {
        setupMockConfig({});
        originalUrl = window.location.href;
        localVue = getLocalVue();
        localVue.use(PiniaVuePlugin);
        testPinia = createTestingPinia({ createSpy: vi.fn });

        windowTab = {
            id: "enable-window-manager",
            icon: faTh,
            tooltip: "Enable/Disable Window Manager",
            visible: true,
            _active: false,
            onclick: function () {
                this._active = !this._active;
            },
        };

        const userStore = useUserStore();
        userStore.currentUser = currentUser;

        wrapper = mount(Masthead, {
            propsData: {
                windowTab,
            },
            localVue,
            pinia: testPinia,
        });
        await flushPromises();
    });

    afterEach(() => {
        wrapper.destroy();
        window.location.href = originalUrl;
    });

    async function remount(config, user = currentUser) {
        wrapper.destroy();
        setupMockConfig(config);
        const userStore = useUserStore();
        userStore.currentUser = user;
        wrapper = mount(Masthead, {
            propsData: { windowTab },
            localVue,
            pinia: testPinia,
        });
        await flushPromises();
    }

    it("should render simple tab item links", () => {
        expect(wrapper.findAll("li.nav-item").length).toBe(4);
        // Ensure specified link title respected.
        expect(wrapper.find("#help").text()).toBe("Support, Contact, and Community");
        expect(wrapper.find("#help a").attributes("href")).toBe("/about");
    });

    it("should display window manager button", async () => {
        expect(wrapper.find("#enable-window-manager a svg").exists()).toBe(true);
        expect(windowTab._active).toBe(false);
        await wrapper.find("#enable-window-manager a").trigger("click");
        expect(windowTab._active).toBe(true);
    });

    it("should load webhooks on creation", async () => {
        expect(wrapper.find("#extension a").text()).toBe("Extension Point");
    });

    it("does not render the site switcher without destinations", async () => {
        expect(wrapper.find("#subdomain_switcher").exists()).toBe(false);

        await remount({
            subdomain_switcher: [{ label: "Current site", url: `${window.location.origin}/` }],
        });

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(false);
    });

    it("renders exact destination URLs in configured order and omits the current origin", async () => {
        window.location.href = "http://galaxy.example.org:80/current/path?query=kept-out";
        await remount({
            subdomain_switcher: [
                { label: "Current site", url: "http://galaxy.example.org/" },
                { label: "Invalid site", url: "http://[" },
                { label: "Single Cell <Omics>", url: "https://singlecell.example.org/root/?exact=true#destination" },
                { label: "Climate", url: "https://climate.example.org" },
            ],
        });

        const switcher = wrapper.find("#subdomain_switcher");
        const links = switcher.findAll("a.dropdown-item");
        expect(switcher.exists()).toBe(true);
        expect(switcher.attributes("title")).toBe("Switch sites");
        expect(links.wrappers.map((link) => link.text())).toEqual(["Single Cell <Omics>", "Climate"]);
        expect(links.wrappers.map((link) => link.attributes("href"))).toEqual([
            "https://singlecell.example.org/root/?exact=true#destination",
            "https://climate.example.org",
        ]);
        expect(switcher.find("em").exists()).toBe(false);
    });

    it.each([
        ["registered", currentUser, {}],
        ["anonymous", { id: "anonymous", isAnonymous: true }, {}],
        ["single-user", currentUser, { single_user: true }],
    ])("renders the optional switcher for the %s masthead", async (_variant, user, variantConfig) => {
        await remount(
            {
                ...variantConfig,
                subdomain_switcher: [{ label: "Another site", url: "https://another.example.org" }],
            },
            user,
        );

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(true);
    });

    it.each([["javascript:alert(1)"], ["data:text/html,<script>alert(1)</script>"], ["vbscript:msgbox(1)"]])(
        "drops destinations using the unsafe scheme %s",
        async (url) => {
            await remount({
                subdomain_switcher: [
                    { label: "Unsafe", url },
                    { label: "Safe", url: "https://safe.example.org" },
                ],
            });

            const links = wrapper.findAll("#subdomain_switcher a.dropdown-item");
            expect(links.wrappers.map((link) => link.attributes("href"))).toEqual(["https://safe.example.org"]);
        },
    );

    it("drops destinations without a usable label instead of failing to render", async () => {
        await remount({
            subdomain_switcher: [
                { url: "https://unlabelled.example.org" },
                { label: "   ", url: "https://blank.example.org" },
                { label: "Safe", url: "https://safe.example.org" },
            ],
        });

        const links = wrapper.findAll("#subdomain_switcher a.dropdown-item");
        expect(links.wrappers.map((link) => link.text())).toEqual(["Safe"]);
    });
});
