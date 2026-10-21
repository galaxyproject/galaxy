import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { describe, expect, it, onTestFinished } from "vitest";

import * as GButtonStories from "./GButton.stories";
import { createMemoryRouter } from "./test-utils";

import GButton from "./GButton.vue";

const stories = composeStories(GButtonStories);
const mountStory = useStoryMount();

/** The button's own `click` emissions; the story mount's root is the story, not the button. */
function clicks(wrapper: VueWrapper) {
    return wrapper.getComponent(GButton).emitted("click");
}

// The native title and tooltip are checked in the stories' plays. `data-title` has no
// user-visible equivalent, but Selenium selectors find buttons by it.
describe("GButton.vue titles", () => {
    it("sets the regular title as data-title when enabled", () => {
        const button = mountStory(stories.Default).get("button");

        expect(button.attributes("data-title")).toBe("Save your changes");
    });

    it("sets the disabled title as data-title when disabled", () => {
        const button = mountStory(stories.Disabled).get("button");

        expect(button.attributes("data-title")).toBe("Nothing to save yet");
    });

    it("falls back to the regular title when disabled without a disabled title", () => {
        const button = mountStory(stories.Default, { props: { disabled: true } }).get("button");

        expect(button.attributes("title")).toBe("Save your changes");
        expect(button.attributes("data-title")).toBe("Save your changes");
    });
});

describe("GButton.vue loading", () => {
    it("shows a spinner while loading", () => {
        const button = mountStory(stories.Loading).get("button");

        expect(button.find('[data-icon="spinner"]').exists()).toBe(true);
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
    it("does not look disabled while loading", () => {
        const button = mountStory(stories.Loading).get("button");

        expect(button.classes()).not.toContain("g-disabled");
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

    it("renders no href when disabled", () => {
        const wrapper = mountStory(stories.ExternalLink, { props: { disabled: true } });

        expect(wrapper.get("button").attributes("href")).toBeUndefined();
    });
});
