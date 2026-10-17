import { faTh } from "@fortawesome/free-solid-svg-icons";
import { createTestingPinia } from "@pinia/testing";
import { getFakeAnonymousUser, getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useCommandPalette } from "@/composables/useCommandPalette";

import { loadMastheadWebhooks } from "./_webhooks";

import Masthead from "./Masthead.vue";

vi.mock("app");
vi.mock("./_webhooks");
vi.mock("vue-router", () => ({
    useRoute: vi.fn(() => ({ name: "Home" })),
    useRouter: vi.fn(),
}));

const SEARCH_BUTTON = "[data-description='masthead search button']";
const LOGIN_BUTTON = "[data-description='login masthead button']";
const USER_MENU_ITEMS = "#user.loggedin-only a.dropdown-item";

const EXTENSION_TAB = { id: "extension", title: "Extension Point", url: "extension_url" };

function createWindowTab() {
    return {
        id: "enable-window-manager",
        icon: faTh,
        tooltip: "Enable/Disable Window Manager",
        visible: true,
        onclick: vi.fn(),
    };
}

/** `useConfig()` and the command palette both read the configuration store, so seeding it configures the masthead. */
async function mountMasthead({ config = {}, user = getFakeRegisteredUser(), windowTab = createWindowTab() } = {}) {
    const pinia = createTestingPinia({
        createSpy: vi.fn,
        initialState: {
            configurationStore: { config },
            userStore: { currentUser: user },
        },
    });
    const wrapper = mount(Masthead, {
        props: { windowTab },
        global: withPlugins(getLocalVue(), pinia),
    });
    await flushPromises();
    return wrapper;
}

function switcherConfig(...destinations) {
    return { subdomain_switcher: destinations };
}

describe("Masthead.vue", () => {
    enableAutoUnmount(afterEach);

    beforeEach(() => {
        vi.mocked(loadMastheadWebhooks).mockImplementation((items) => {
            items.push({ ...EXTENSION_TAB });
        });
    });

    afterEach(() => {
        // The palette's open state is module-level, so it outlives each test's pinia.
        useCommandPalette().closePalette();
    });

    it("renders the simple tab item links", async () => {
        const wrapper = await mountMasthead();

        // window manager, extension tab, command palette search, help, user
        expect(wrapper.findAll("li.nav-item").length).toBe(5);
        expect(wrapper.find("#help").text()).toBe("Support, Contact, and Community");
        expect(wrapper.find("#help a").attributes("href")).toBe("/about");
    });

    it("opens the command palette from the search button", async () => {
        const wrapper = await mountMasthead();
        const { isPaletteOpen } = useCommandPalette();
        expect(isPaletteOpen.value).toBe(false);

        await wrapper.find(SEARCH_BUTTON).trigger("click");

        expect(isPaletteOpen.value).toBe(true);
    });

    it("labels the search button with the localized search phrase", async () => {
        const wrapper = await mountMasthead();

        const button = wrapper.find(SEARCH_BUTTON);
        expect(button.find(".search-placeholder").text()).toBe("Search Galaxy");
        expect(button.attributes("title")).toBe("Search Galaxy (Ctrl+K)");
    });

    it("hides the search button when the palette is disabled", async () => {
        const wrapper = await mountMasthead({ config: { enable_command_palette: false } });

        expect(wrapper.find(SEARCH_BUTTON).exists()).toBe(false);
    });

    it("toggles the window manager from its button", async () => {
        const windowTab = createWindowTab();
        const wrapper = await mountMasthead({ windowTab });
        expect(wrapper.find("#enable-window-manager a svg").exists()).toBe(true);
        expect(wrapper.find("#enable-window-manager .nav-note").exists()).toBe(false);

        await wrapper.find("#enable-window-manager a").trigger("click");

        expect(windowTab.onclick).toHaveBeenCalledOnce();
        expect(wrapper.find("#enable-window-manager .nav-note").exists()).toBe(true);
    });

    it("renders the tabs loaded from masthead webhooks", async () => {
        const wrapper = await mountMasthead();

        expect(wrapper.find("#extension a").text()).toBe("Extension Point");
    });

    it("does not render the site switcher without configured destinations", async () => {
        const wrapper = await mountMasthead();

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(false);
    });

    it("does not render the site switcher when the only destination is the current site", async () => {
        const wrapper = await mountMasthead({
            config: switcherConfig({ label: "Current site", url: `${window.location.origin}/` }),
        });

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(false);
    });

    it("renders exact destination URLs in configured order and omits the current origin", async () => {
        window.location.href = "http://galaxy.example.org:80/current/path?query=kept-out";
        const wrapper = await mountMasthead({
            config: switcherConfig(
                { label: "Current site", url: "http://galaxy.example.org/" },
                { label: "Invalid site", url: "http://[" },
                { label: "Single Cell <Omics>", url: "https://singlecell.example.org/root/?exact=true#destination" },
                { label: "Climate", url: "https://climate.example.org" },
            ),
        });

        const switcher = wrapper.find("#subdomain_switcher");
        const links = switcher.findAll("a.dropdown-item");
        expect(switcher.exists()).toBe(true);
        expect(switcher.attributes("title")).toBe("Switch sites");
        expect(links.map((link) => link.text())).toEqual(["Single Cell <Omics>", "Climate"]);
        expect(links.map((link) => link.attributes("href"))).toEqual([
            "https://singlecell.example.org/root/?exact=true#destination",
            "https://climate.example.org",
        ]);
        expect(switcher.find("em").exists()).toBe(false);
    });

    it("renders the switcher beside a registered user's menu", async () => {
        const wrapper = await mountMasthead({
            config: switcherConfig({ label: "Another site", url: "https://another.example.org" }),
            user: getFakeRegisteredUser(),
        });

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(true);
        expect(wrapper.findAll(USER_MENU_ITEMS).map((item) => item.text())).toEqual(["Preferences", "Sign Out"]);
    });

    it("renders the switcher beside an anonymous user's login button", async () => {
        const wrapper = await mountMasthead({
            config: switcherConfig({ label: "Another site", url: "https://another.example.org" }),
            user: getFakeAnonymousUser(),
        });

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(true);
        expect(wrapper.find(LOGIN_BUTTON).exists()).toBe(true);
    });

    it("renders the switcher beside a single-user instance's menu, which has no sign out", async () => {
        const wrapper = await mountMasthead({
            config: {
                single_user: true,
                ...switcherConfig({ label: "Another site", url: "https://another.example.org" }),
            },
            user: getFakeRegisteredUser(),
        });

        expect(wrapper.find("#subdomain_switcher").exists()).toBe(true);
        expect(wrapper.findAll(USER_MENU_ITEMS).map((item) => item.text())).toEqual(["Preferences"]);
    });

    it.each([["javascript:alert(1)"], ["data:text/html,<script>alert(1)</script>"], ["vbscript:msgbox(1)"]])(
        "drops destinations using the unsafe scheme %s",
        async (url) => {
            const wrapper = await mountMasthead({
                config: switcherConfig({ label: "Unsafe", url }, { label: "Safe", url: "https://safe.example.org" }),
            });

            const links = wrapper.findAll("#subdomain_switcher a.dropdown-item");
            expect(links.map((link) => link.attributes("href"))).toEqual(["https://safe.example.org"]);
        },
    );

    it("drops destinations without a usable label instead of failing to render", async () => {
        const wrapper = await mountMasthead({
            config: switcherConfig(
                { url: "https://unlabelled.example.org" },
                { label: "   ", url: "https://blank.example.org" },
                { label: "Safe", url: "https://safe.example.org" },
            ),
        });

        const links = wrapper.findAll("#subdomain_switcher a.dropdown-item");
        expect(links.map((link) => link.text())).toEqual(["Safe"]);
    });
});
