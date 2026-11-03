import { createTestingPinia, type TestingOptions } from "@pinia/testing";
import { mount, type MountingOptions, type VueWrapper } from "@vue/test-utils";
import type { RequestHandler } from "msw";
import { afterEach, vi } from "vitest";
import type { FunctionalComponent } from "vue";
import type { Router } from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { appHandlers } from "@/api/client/__mocks__/http";

import { getLocalVue } from "./helpers";

type MswParameter =
    | RequestHandler[]
    | { handlers?: RequestHandler[] | Record<string, RequestHandler | RequestHandler[]> };

/** A story from `composeStories()`: a functional component carrying the story's parameters. */
type ComposedStory = FunctionalComponent & { parameters?: { msw?: MswParameter } };

/** The MSW handlers a story declares in `parameters.msw`, in any of the addon's forms. */
function storyHandlers(story: ComposedStory): RequestHandler[] {
    const msw = story.parameters?.msw;
    if (!msw) {
        return [];
    }
    if (Array.isArray(msw)) {
        return msw;
    }
    const handlers = msw.handlers ?? [];
    return Array.isArray(handlers) ? handlers : Object.values(handlers).flat();
}

/** Any story from `composeStories(Stories)`, for helpers that mount one of several. */
export type StoryOf<Stories> = Stories[keyof Stories];

type GlobalOptions = NonNullable<MountingOptions<unknown>["global"]>;

export interface StoryMountOptions {
    /** Attach to a real DOM parent for visibility/focus checks. */
    attachTo?: MountingOptions<unknown>["attachTo"];
    /** Props on top of the story's args. */
    props?: Record<string, unknown>;
    /** Added to the default test globals: plugins are appended, the rest is merged by name. */
    global?: GlobalOptions;
    /** A router with the routes the test needs, used instead of the default one. */
    router?: Router;
    /** Testing pinia options. Actions run by default, as they do in the story. */
    pinia?: Partial<TestingOptions>;
    /** Wrap plugin-localized text (`v-localize`, `l()`) as `test_localized<...>`, for `toBeLocalizationOf`. */
    instrumentLocalization?: boolean;
}

function mergeGlobal(base: GlobalOptions, extra: GlobalOptions = {}): GlobalOptions {
    return {
        ...base,
        ...extra,
        plugins: [...(base.plugins ?? []), ...(extra.plugins ?? [])],
        components: { ...base.components, ...extra.components },
        directives: { ...base.directives, ...extra.directives },
        mocks: { ...base.mocks, ...extra.mocks },
        provide: { ...base.provide, ...extra.provide },
        stubs: { ...(base.stubs as object), ...(extra.stubs as object) },
    };
}

/**
 * Mounts composed Storybook stories in a unit test, as Storybook renders them: the
 * app-wide handlers plus the story's own answer the API, and each mount gets a fresh
 * testing pinia whose actions run. Mounts are unmounted after each test. Call at
 * module level, as it registers the mock server's lifecycle hooks.
 */
export function useStoryMount() {
    const { server } = useServerMock();
    const mounted: VueWrapper[] = [];
    afterEach(() => mounted.splice(0).forEach((wrapper) => wrapper.unmount()));
    return function mountStory(
        story: ComposedStory,
        { props = {}, global, router, pinia, attachTo, instrumentLocalization = false }: StoryMountOptions = {},
    ) {
        // Handlers used later take precedence, so the story's override the app's.
        server.use(...Object.values(appHandlers));
        server.use(...storyHandlers(story));
        const testingPinia = createTestingPinia({ createSpy: vi.fn, stubActions: false, ...pinia });
        const wrapper = mount(story, {
            props,
            attachTo,
            global: mergeGlobal(getLocalVue(instrumentLocalization), global),
            pinia: testingPinia,
            router,
        });
        mounted.push(wrapper);
        return wrapper;
    };
}
