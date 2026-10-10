import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, onTestFinished } from "vitest";

import * as GButtonStories from "./GButton.stories";
import { createMemoryRouter } from "./test-utils";

import GButton from "./GButton.vue";

const stories = composeStories(GButtonStories);
const mountStory = useStoryMount();

const ROW_CLICKS = '[data-description="row clicks"]';

/** The button's own `click` emissions; the story mount's root is the story, not the button. */
function clicks(wrapper: VueWrapper) {
    return wrapper.getComponent(GButton).emitted("click");
}

describe("GButton.vue titles", () => {
    it("uses the regular title when enabled", () => {
        const button = mountStory(stories.Default).get("button");

        expect(button.attributes("title")).toBe("Save your changes");
        expect(button.attributes("data-title")).toBe("Save your changes");
    });

    it("uses the disabled title when disabled", () => {
        const button = mountStory(stories.Disabled).get("button");

        expect(button.attributes("title")).toBe("Nothing to save yet");
        expect(button.attributes("data-title")).toBe("Nothing to save yet");
    });

    it("falls back to the regular title when disabled without a disabled title", () => {
        const button = mountStory(stories.Default, { props: { disabled: true } }).get("button");

        expect(button.attributes("title")).toBe("Save your changes");
        expect(button.attributes("data-title")).toBe("Save your changes");
    });

    // A styled tooltip replaces the native title. RouterLink runs in Vue 3 mode, where a
    // `false` attribute renders as the string "false" instead of being dropped.
    it("leaves the native title off a router link with a tooltip", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter() });

        expect(wrapper.get("a").attributes("title")).toBeUndefined();
    });
});

describe("GButton.vue disabled", () => {
    // A disabled button must stay hoverable so the (disabled) title can surface its
    // tooltip. We mark it disabled via aria-disabled and a JS click guard rather than
    // the native `disabled` attribute (which would suppress hover events).
    it("remains hoverable when disabled", () => {
        const button = mountStory(stories.Disabled).get("button");

        expect(button.attributes("aria-disabled")).toBe("true");
        expect(button.attributes("disabled")).toBeUndefined();
    });

    it("does not emit click when disabled", async () => {
        const wrapper = mountStory(stories.Disabled);

        await wrapper.get("button").trigger("click");

        expect(clicks(wrapper)).toBeUndefined();
    });

    it("emits click when enabled", async () => {
        const wrapper = mountStory(stories.Default);

        await wrapper.get("button").trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
    });
});

describe("GButton.vue loading", () => {
    it("shows a spinner and marks itself busy while loading", () => {
        const button = mountStory(stories.Loading).get("button");

        expect(button.attributes("aria-busy")).toBe("true");
        expect(button.find('[data-icon="spinner"]').exists()).toBe(true);
    });

    it("ignores clicks while loading", async () => {
        const wrapper = mountStory(stories.Loading);

        await wrapper.get("button").trigger("click");

        expect(clicks(wrapper)).toBeUndefined();
    });

    it("renders a loading router-link button as a plain button so it cannot navigate", () => {
        const wrapper = mountStory(stories.InternalLink, { props: { loading: true }, router: createMemoryRouter() });

        expect(wrapper.element.tagName).toBe("BUTTON");
    });

    // `setProps` would remount a composed story, so this toggle mounts the button itself.
    it("drops the spinner and busy state and takes clicks again once loading ends", async () => {
        const { label, ...loadingProps } = stories.Loading.args;
        const wrapper = mount(GButton, { props: loadingProps, slots: { default: label } });
        onTestFinished(() => wrapper.unmount());
        await wrapper.setProps({ loading: false });
        const button = wrapper.get("button");

        expect(button.attributes("aria-busy")).toBeUndefined();
        expect(button.find('[data-icon="spinner"]').exists()).toBe(false);

        await button.trigger("click");
        expect(wrapper.emitted("click")).toHaveLength(1);
    });

    // Loading is a wait, not an unavailable action, so the button keeps its colour.
    it("does not look or announce itself as disabled while loading", () => {
        const button = mountStory(stories.Loading).get("button");

        expect(button.classes()).not.toContain("g-disabled");
        expect(button.attributes("aria-disabled")).toBeUndefined();
    });
});

describe("GButton.vue click propagation", () => {
    // A native disabled button dispatches no click at all, so nothing reaches clickable
    // ancestors. GButton renders `aria-disabled` instead of the native attribute, so the
    // guard in `onClick` has to stop the event itself.
    function mountInClickableRow(buttonProps: Record<string, unknown>) {
        const wrapper = mountStory(stories.InClickableRow, { props: buttonProps });

        return { rowClicks: () => wrapper.get(ROW_CLICKS).text(), button: wrapper.getComponent(GButton) };
    }

    it("does not bubble a click to clickable ancestors when disabled", async () => {
        const { rowClicks, button } = mountInClickableRow({ disabled: true, disabledTitle: "Nope" });

        await button.get("button").trigger("click");

        expect(button.emitted("click")).toBeUndefined();
        expect(rowClicks()).toBe("Row clicks: 0");
    });

    it("bubbles a click to clickable ancestors when enabled", async () => {
        const { rowClicks, button } = mountInClickableRow({});

        await button.get("button").trigger("click");

        expect(button.emitted("click")).toHaveLength(1);
        expect(rowClicks()).toBe("Row clicks: 1");
    });
});

describe("GButton.vue click per root element", () => {
    // A router link gets the click listener on its rendered anchor by fallthrough,
    // alongside RouterLink's own navigation handler; the plain roots bind the same
    // single listener directly.
    it.each([
        { root: "router-link", element: "a", story: stories.InternalLink, withRouter: true },
        { root: "plain button", element: "button", story: stories.Default, withRouter: false },
        { root: "plain anchor", element: "a", story: stories.ExternalLink, withRouter: false },
    ])("emits click exactly once from a $root root", async ({ element, story, withRouter }) => {
        const wrapper = mountStory(story, { router: withRouter ? createMemoryRouter() : undefined });

        await wrapper.get(element).trigger("click");

        expect(clicks(wrapper)).toHaveLength(1);
    });
});

describe("GButton.vue disabled navigation", () => {
    // A disabled button with a `to` prop must not navigate: an empty `to` is not a
    // reliable no-op in vue-router, so a disabled GButton renders as a plain button
    // instead and has no navigation behaviour to suppress.
    it("renders an enabled router-link button as an anchor", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter() });

        expect(wrapper.element.tagName).toBe("A");
    });

    it("renders a disabled router-link button as a plain button", () => {
        const wrapper = mountStory(stories.InternalLink, {
            props: { disabled: true, disabledTitle: "Nope" },
            router: createMemoryRouter(),
        });

        expect(wrapper.element.tagName).toBe("BUTTON");
    });

    it("does not navigate when a disabled router-link button is clicked", async () => {
        const router = createMemoryRouter({ paths: ["/start", "/pages/create"] });
        await router.push("/start?keep=me");
        const wrapper = mountStory(stories.InternalLink, { props: { disabled: true }, router });

        await wrapper.trigger("click");
        await flushPromises();

        expect(router.currentRoute.value.fullPath).toBe("/start?keep=me");
    });
});

describe("GButton.vue link targets", () => {
    // Galaxy can be served under a URL prefix, so a router link's href has to come from
    // the router, which knows the base -- open-in-new-tab and copy-link use it as is.
    it("renders a router link's href with the router base", () => {
        const wrapper = mountStory(stories.InternalLink, { router: createMemoryRouter({ base: "/galaxypf/" }) });

        expect(wrapper.get("a").attributes("href")).toBe("/galaxypf/pages/create");
    });

    it("renders a plain anchor's href as given", () => {
        const wrapper = mountStory(stories.ExternalLink);

        expect(wrapper.get("a").attributes("href")).toBe("https://example.org/data.txt");
    });

    it("renders no href when disabled", () => {
        const wrapper = mountStory(stories.ExternalLink, { props: { disabled: true } });

        expect(wrapper.get("button").attributes("href")).toBeUndefined();
    });
});
