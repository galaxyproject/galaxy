import { faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import FormCardSticky from "./FormCardSticky.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const DEFAULT_PROPS = {
    name: "Tool Name",
    description: "This is a test tool",
    version: "23.0",
    icon: faWrench,
    logo: "/static/logo.svg",
    errorMessage: "",
    isLoading: false,
};

const SELECTORS = {
    ERROR_ALERT: ".alert.alert-danger",
    LOGO: "img[alt='logo']",
    NAME: "h1",
    DESCRIPTION: "[itemprop='description']",
    VERSION: "[data-description='galaxy tool version']",
    NEWER_VERSION_BADGE: "[data-description='newer tool version']",
    BODY: "#tool-card-body",
};

function mountFormCardSticky(props = {}, slots = {}) {
    return mount(FormCardSticky, {
        props: { ...DEFAULT_PROPS, ...props },
        slots,
    });
}

describe("FormCardSticky", () => {
    it("renders error alert when errorMessage is present", () => {
        const wrapper = mountFormCardSticky({ errorMessage: "Something went wrong" });

        const alert = wrapper.find(SELECTORS.ERROR_ALERT);
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Something went wrong");
    });

    it("renders loading state when isLoading is true", () => {
        const wrapper = mountFormCardSticky({ isLoading: true, errorMessage: "" });

        expect(wrapper.findComponent(LoadingSpan).exists()).toBe(true);
    });

    it("renders logo when provided", () => {
        const wrapper = mountFormCardSticky();

        const logo = wrapper.find(SELECTORS.LOGO);
        expect(logo.exists()).toBe(true);
        expect(logo.attributes("src")).toBe("http://localhost/static/logo.svg");
    });

    it("renders icon fallback when logo is not provided", () => {
        const wrapper = mountFormCardSticky({ logo: undefined });

        const icon = wrapper.findComponent(FontAwesomeIcon);
        expect(icon.exists()).toBe(true);
        expect(icon.classes()).toContain("fa-fw");
        expect(wrapper.find(SELECTORS.LOGO).exists()).toBe(false);
    });

    it("renders name, description, and version", () => {
        const wrapper = mountFormCardSticky();

        expect(wrapper.find(SELECTORS.NAME).text()).toBe("Tool Name");
        expect(wrapper.find(SELECTORS.DESCRIPTION).text()).toBe("This is a test tool");
        expect(wrapper.find(SELECTORS.VERSION).text()).toBe("(Galaxy Version 23.0)");
    });

    it("renders clickable newer version badge with a tooltip when requested", async () => {
        const wrapper = mountFormCardSticky({ isNotLatestVersion: true });

        const badge = wrapper.find(SELECTORS.NEWER_VERSION_BADGE);
        expect(badge.exists()).toBe(true);
        expect(badge.text()).toBe("Newer version available");
        expect(badge.attributes("title")).toBe("Switch to the latest available tool version");
        expect(badge.element.tagName).toBe("BUTTON");
        expect(badge.attributes("type")).toBe("button");

        await badge.trigger("click");

        expect(wrapper.emitted("newer-version-click")).toHaveLength(1);
    });

    it("does not render newer version badge by default", () => {
        const wrapper = mountFormCardSticky();

        expect(wrapper.find(SELECTORS.NEWER_VERSION_BADGE).exists()).toBe(false);
    });

    it("renders slot content: buttons, default, footer", () => {
        const wrapper = mountFormCardSticky(
            {},
            {
                buttons: "<button>Click me</button>",
                default: "<p>Main content</p>",
                footer: "<footer>Footer content</footer>",
            },
        );

        expect(wrapper.find("button").text()).toBe("Click me");
        expect(wrapper.find(SELECTORS.BODY).text()).toContain("Main content");
        expect(wrapper.find("footer").text()).toContain("Footer content");
    });
});
