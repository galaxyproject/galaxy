import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { usePageStore } from "@/stores/pageStore";
import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";
import { useVisualizationStore } from "@/stores/visualizationStore";

import { datasetsProvider } from "./providers/datasets";
import { PaletteFetchError } from "./providers/errors";
import { historiesProvider } from "./providers/histories";
import { navigationProvider } from "./providers/navigation";
import { pagesProvider } from "./providers/pages";
import { toolsProvider } from "./providers/tools";
import { workflowsProvider } from "./providers/workflows";
import type { CommandPaletteProvider, PaletteItem } from "./types";

import MountTarget from "./CommandPalette.vue";

vi.mock("@/composables/config");

const localVue = getLocalVue(true);
localVue.use(VueRouter);

const { server, http } = useServerMock();

const DEBOUNCE_WAIT = 250;

async function settle() {
    await new Promise((resolve) => setTimeout(resolve, DEBOUNCE_WAIT));
    await flushPromises();
}

interface SearchCounter {
    calls: number;
    restore: () => void;
}

/** Counts how often a provider was asked for its scoped results */
function countScopedSearches(provider: CommandPaletteProvider): SearchCounter {
    const original = provider.searchScoped;
    const counter: SearchCounter = {
        calls: 0,
        restore: () => {
            provider.searchScoped = original;
        },
    };
    provider.searchScoped = (scope, searchQuery, ctx) => {
        counter.calls++;
        return original!(scope, searchQuery, ctx);
    };
    return counter;
}

interface StalledSearch {
    /** Lets the held search answer with these items */
    land: (items: PaletteItem[]) => void;
    restore: () => void;
}

/** Holds a provider's unscoped search open until the test lets it answer */
function stallSearch(provider: CommandPaletteProvider): StalledSearch {
    const original = provider.search;
    let land: (items: PaletteItem[]) => void = () => {};
    const pending = new Promise<PaletteItem[]>((resolve) => {
        land = resolve;
    });
    provider.search = () => pending;
    return {
        land: (items) => land(items),
        restore: () => {
            provider.search = original;
        },
    };
}

/** Counts how often a provider answered a search that carried no query */
function countEmptyQuerySearches(provider: CommandPaletteProvider): SearchCounter {
    const original = provider.emptyQueryItems;
    const counter: SearchCounter = {
        calls: 0,
        restore: () => {
            provider.emptyQueryItems = original;
        },
    };
    provider.emptyQueryItems = (ctx) => {
        counter.calls++;
        return original!(ctx);
    };
    return counter;
}

describe("CommandPalette", () => {
    let wrapper: Wrapper<Vue>;
    let router: VueRouter;

    beforeEach(async () => {
        server.use(
            http.get("/api/unprivileged_tools", ({ response }) => {
                return response(200).json([]);
            }),
        );
        router = new VueRouter({ mode: "abstract" });
        wrapper = mount(MountTarget as object, {
            localVue,
            router,
            pinia: createTestingPinia({ createSpy: vi.fn, stubActions: true }),
        });
        useCommandPalette().openPalette();
        await settle();
    });

    afterEach(() => {
        useCommandPalette().closePalette();
        // the MRU list is a module level singleton, shared by every test here
        useRecentPaletteItems().clearRecentItems();
        wrapper?.destroy();
    });

    function input() {
        return wrapper.find("[data-description='palette input']");
    }

    function inputValue() {
        return (input().element as HTMLInputElement).value;
    }

    function badge() {
        return wrapper.find("[data-description='palette badge']");
    }

    /** Icon names rendered in the input row, the leading mode icon included */
    function inputIcons() {
        return wrapper.findAll(".palette-input svg").wrappers.map((icon) => icon.attributes("data-icon"));
    }

    async function type(query: string) {
        (input().element as HTMLInputElement).value = query;
        await input().trigger("input");
        await settle();
    }

    async function press(key: string, options: Record<string, unknown> = {}) {
        await input().trigger("keydown", { key, ...options });
        await settle();
    }

    /** A key press without waiting it out, for simulating a held-down key */
    async function pressNow(key: string, options: Record<string, unknown> = {}) {
        await input().trigger("keydown", { key, ...options });
    }

    /** Dispatches a real event, so the test can tell whether it was prevented */
    async function sendKey(key: string, options: Record<string, unknown> = {}) {
        const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options });
        input().element.dispatchEvent(event);
        await settle();
        return event;
    }

    /** Dispatches a real event, so the test can tell whether it was prevented */
    function sendMousedown(target: Element) {
        const event = new MouseEvent("mousedown", { bubbles: true, cancelable: true });
        target.dispatchEvent(event);
        return event;
    }

    function hint(id: string) {
        return wrapper.find(`[data-description='palette hint ${id}']`);
    }

    function categoryRow() {
        return wrapper.find("[data-description='palette categories']");
    }

    function category(id: string) {
        return wrapper.find(`[data-description='palette category ${id}']`);
    }

    async function pickCategory(id: string) {
        await category(id).trigger("click");
        await settle();
    }

    function optionRow(text: string) {
        return wrapper.findAll("[data-description='palette option']").wrappers.find((row) => row.text().includes(text));
    }

    function spyOnInputFocus() {
        return vi.spyOn(input().element as HTMLInputElement, "focus");
    }

    function sectionIds() {
        return wrapper
            .findAll("[data-description^='palette section ']")
            .wrappers.map((section) => section.attributes("data-description"));
    }

    /** Placeholder rows standing in for a provider that has not answered yet */
    function skeletons() {
        return wrapper.findAll("[data-description='palette skeleton']");
    }

    function selectedRow() {
        return wrapper.find("[data-description='palette option'][aria-selected='true']");
    }

    /** Presses or releases a modifier on the window, as holding it down would */
    async function holdKey(key: string, down: boolean) {
        window.dispatchEvent(new KeyboardEvent(down ? "keydown" : "keyup", { key }));
        await wrapper.vm.$nextTick();
    }

    function secondaryHints() {
        return wrapper.findAll("[data-description='palette option secondary']");
    }

    /** The offer standing in for a scope an anonymous visitor cannot reach */
    function loginPrompt() {
        return wrapper.find("[data-description='palette section login-prompt']");
    }

    /** Turns the current user into a visitor without an account */
    function browseAnonymously() {
        useUserStore().currentUser = { id: "anon", isAnonymous: true } as never;
    }

    it("shows actions and navigation sections for an empty query", () => {
        const text = wrapper.text();
        expect(text).toContain("Actions");
        expect(text).toContain("Navigation");
        expect(text).toContain("Upload data");
    });

    it("filters results while typing", async () => {
        await type("workflows");
        const options = wrapper.findAll("[role='option']");
        expect(options.length).toBeGreaterThan(0);
        expect(options.at(0).text()).toContain("Workflows");
    });

    it("scopes to actions with the '>' prefix", async () => {
        await type("> ");
        const text = wrapper.text();
        expect(badge().text()).toContain("Actions");
        expect(text).toContain("Upload data");
        expect(text).not.toContain("Navigation");
    });

    it("converts a scope token into a badge and strips it from the input", async () => {
        await type("t: align");
        expect(badge().text()).toContain("Tools");
        expect(inputValue()).toBe("align");
    });

    it("hands a scope to its registered provider", async () => {
        await type("w: rna");
        expect(badge().text()).toContain("My workflows");
        // the workflow store is empty here, so the scope has nothing to offer
        expect(wrapper.find("[data-description='palette scope hint']").exists()).toBe(false);
        expect(wrapper.find("[data-description='palette empty']").exists()).toBe(true);
        // a known user is never asked to log in for a scope they already have
        expect(loginPrompt().exists()).toBe(false);
    });

    it("remembers an opened entity in the palette recents", async () => {
        const visualizationStore = useVisualizationStore();
        visualizationStore.storedVisualizations = {
            "viz-1": { id: "viz-1", title: "ATAC peaks", type: "nvd3_bar" } as never,
        };
        visualizationStore.visualizationIdsByVariant.my = ["viz-1"];
        vi.spyOn(router, "push").mockResolvedValue(undefined as never);

        await type("atac");
        const option = wrapper
            .findAll("[data-description='palette option']")
            .wrappers.find((row) => row.text().includes("ATAC peaks"));
        await option?.trigger("click");

        expect(useRecentPaletteItems().recentItems("visualization")).toMatchObject([
            { id: "viz-1", name: "ATAC peaks", type: "visualization" },
        ]);
    });

    it("runs the secondary action of the selected item on shift+enter", async () => {
        const pageStore = usePageStore();
        pageStore.summariesById = { p1: { id: "p1", title: "Lab notes", slug: "lab-notes" } as never };
        pageStore.idsByVariant.my = ["p1"];
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);

        await type("lab notes");
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("Lab notes");

        await press("Enter", { shiftKey: true });
        expect(push).toHaveBeenCalledWith("/pages/editor?id=p1");
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("collects an action argument on shift+enter and runs the picked row", async () => {
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);

        await type("> upload");
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("Upload data");
        expect(hint("secondary").text()).toContain("pick a method");

        await press("Enter", { shiftKey: true });
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("Upload data");
        expect(inputValue()).toBe("");
        expect(wrapper.text()).toContain("Paste File Content");
        expect(hint("run").exists()).toBe(true);
        expect(hint("remove-action").exists()).toBe(true);

        await type("paste file content");
        await press("Enter");
        expect(push).toHaveBeenCalledWith("/upload/paste-content");
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("opens the picker on plain enter for an action without a default", async () => {
        useUserStore().currentUser = { id: "u1", email: "user@galaxy.org", username: "user" } as never;

        await type("> run workflow");
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("Run workflow");

        await press("Enter");
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("Run workflow");
    });

    it("prompts for a free text argument instead of reporting no results", async () => {
        useUserStore().currentUser = { id: "u1", email: "user@galaxy.org", username: "user" } as never;

        await type("> create new history");
        await press("Enter", { shiftKey: true });
        expect(badge().text()).toContain("Create new history");

        const prompt = () => wrapper.find("[data-description='palette argument hint']");
        expect(prompt().text()).toContain("Type a name for the new history");
        expect(wrapper.find("[data-description='palette empty']").exists()).toBe(false);

        await type("rna seq");
        expect(prompt().exists()).toBe(false);
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("rna seq");

        await type("");
        expect(prompt().exists()).toBe(true);
    });

    it("leaves an action's argument badge on backspace at the start", async () => {
        await type("> upload");
        await press("Enter", { shiftKey: true });
        expect(badge().text()).toContain("Upload data");

        await press("Backspace");
        expect(badge().exists()).toBe(false);
        expect(wrapper.text()).toContain("Navigation");
    });

    it("ignores shift+enter on an item without a secondary behavior", async () => {
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);

        await type("workflows");
        await press("Enter", { shiftKey: true });
        expect(push).not.toHaveBeenCalled();
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
    });

    it("pops the badge on backspace with the caret at the start", async () => {
        await type("t:");
        expect(badge().exists()).toBe(true);

        await press("Backspace");
        expect(badge().exists()).toBe(false);
        expect(wrapper.text()).toContain("Navigation");
    });

    it("keeps the badge on backspace while the caret is inside the text", async () => {
        await type("t: align");
        (input().element as HTMLInputElement).setSelectionRange(2, 2);

        await press("Backspace");
        expect(badge().exists()).toBe(true);
    });

    it("pops the badge when its remove button is clicked", async () => {
        await type("t: align");
        expect(badge().attributes("aria-label")).toContain("Tools");

        await badge().trigger("click");
        await settle();
        expect(badge().exists()).toBe(false);
        // the query typed after the badge is kept
        expect(inputValue()).toBe("align");
    });

    it("clears the text, then the badge, then closes on escape", async () => {
        await type("t: align");

        await press("Escape");
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().exists()).toBe(true);
        expect(inputValue()).toBe("");

        await press("Escape");
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().exists()).toBe(false);

        await press("Escape");
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("lists the scopes in help mode and applies the selected one", async () => {
        await type("?");
        const text = wrapper.text();
        expect(text).toContain("Scopes");
        expect(text).toContain("Search my workflows");
        expect(text).toContain("w:");
        // gated behind interactivetools_enable, which the mocked config leaves off
        expect(text).not.toContain("Search interactive tools");
        // the scopes lead, then the actions, then the key bindings
        expect(sectionIds()).toEqual([
            "palette section help:scopes",
            "palette section help:actions",
            "palette section help:keys",
        ]);

        await press("Enter");
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("My workflows");
    });

    it("marks help mode with a question mark in place of the search icon", async () => {
        expect(inputIcons()).toContain("search");

        await type("?");
        expect(inputIcons()).toContain("question-circle");
        expect(inputIcons()).not.toContain("search");
    });

    it("lists one help row per action, applying the action scope with it", async () => {
        await type("?");
        const uploadRow = optionRow("Upload data");
        expect(uploadRow).toBeDefined();
        // every action row documents the sigil that reaches it
        expect(uploadRow?.text()).toContain(">");
        expect(wrapper.text()).toContain("Create workflow");

        await uploadRow?.trigger("click");
        await settle();

        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("Actions");
        expect(inputValue()).toBe("Upload data");
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("Upload data");
    });

    it("documents every binding in the help keys section", async () => {
        await type("?");
        const text = wrapper.text();
        expect(text).toContain("Keys");
        expect(text).toContain("Open the selected result");
        expect(text).toContain("Remove the active filter");
        expect(input().attributes("placeholder")).toContain("shortcuts");

        // the key badge is decorative, so the row names its shortcut itself
        const keyRow = wrapper
            .findAll("[data-description='palette option']")
            .wrappers.find((row) => row.text().includes("Open the selected result"));
        expect(keyRow?.attributes("aria-label")).toBe("Open the selected result (↵)");
    });

    it("names the syntax in the root placeholder and the filter in a scoped one", async () => {
        expect(input().attributes("placeholder")).toContain("> actions");
        expect(input().attributes("placeholder")).toContain("? help");

        await type("t:");
        expect(input().attributes("placeholder")).toBe("Search tools…");
    });

    it("navigates to the selected item on enter and closes", async () => {
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);
        await type("workflows");
        await input().trigger("keydown", { key: "Enter" });
        expect(push).toHaveBeenCalledWith("/workflows/list");
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("opens in a new tab on ctrl/cmd+enter and stays open", async () => {
        const open = vi.spyOn(window, "open").mockImplementation(() => null);
        const push = vi.spyOn(router, "push");
        await type("workflows");
        await input().trigger("keydown", { key: "Enter", ctrlKey: true });
        expect(open).toHaveBeenCalledWith(router.resolve("/workflows/list").href, "_blank", "noopener");
        expect(push).not.toHaveBeenCalled();
        // several items can be sent to tabs in a row without reopening
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
    });

    it("previews the new tab binding while ctrl/cmd is held", async () => {
        await type("workflows");
        expect(hint("open").classes()).toContain("hint-active");
        expect(hint("new-tab").classes()).not.toContain("hint-active");
        expect(wrapper.find("[data-description='palette option external']").exists()).toBe(false);

        await holdKey("Control", true);
        expect(hint("open").classes()).not.toContain("hint-active");
        expect(hint("new-tab").classes()).toContain("hint-active");
        // only the selected row previews the external open
        expect(wrapper.findAll("[data-description='palette option external']").length).toBe(1);

        await holdKey("Control", false);
        expect(hint("new-tab").classes()).not.toContain("hint-active");
    });

    it("previews the secondary binding while shift is held", async () => {
        await type("> upload");
        expect(hint("secondary").classes()).not.toContain("hint-active");
        expect(secondaryHints().length).toBe(0);

        await holdKey("Shift", true);
        expect(hint("secondary").classes()).toContain("hint-active");
        expect(hint("open").classes()).not.toContain("hint-active");
        // only the selected row previews what shift + enter would do
        expect(secondaryHints().length).toBe(1);
        expect(secondaryHints().at(0).text()).toContain("pick a method");

        await holdKey("Shift", false);
        expect(hint("secondary").classes()).not.toContain("hint-active");
        expect(secondaryHints().length).toBe(0);
    });

    it("stops previewing the secondary binding once shift types a capital", async () => {
        await type("> upload");
        await holdKey("Shift", true);
        expect(hint("secondary").classes()).toContain("hint-active");

        // the capital of "Upload" is shift doing text entry, not a `⇧↵` preview
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "U", shiftKey: true }));
        await wrapper.vm.$nextTick();

        expect(hint("secondary").classes()).not.toContain("hint-active");
        expect(secondaryHints().length).toBe(0);
    });

    it("lets shift win over ctrl/cmd while both are held", async () => {
        await type("> upload");
        await holdKey("Control", true);
        expect(wrapper.findAll("[data-description='palette option external']").length).toBe(1);

        // shift+enter runs the secondary behavior, so the row previews that instead
        await holdKey("Shift", true);
        expect(hint("secondary").classes()).toContain("hint-active");
        expect(hint("new-tab").classes()).not.toContain("hint-active");
        expect(secondaryHints().length).toBe(1);
        expect(wrapper.find("[data-description='palette option external']").exists()).toBe(false);
    });

    it("resets the held modifier when the window loses focus", async () => {
        await type("workflows");
        await holdKey("Control", true);
        expect(hint("new-tab").classes()).toContain("hint-active");

        // opening a new tab steals focus, so the keyup never reaches the window
        window.dispatchEvent(new Event("blur"));
        await wrapper.vm.$nextTick();
        expect(hint("new-tab").classes()).not.toContain("hint-active");
        expect(hint("open").classes()).toContain("hint-active");
    });

    it("resets the held shift when the window loses focus", async () => {
        await type("> upload");
        await holdKey("Shift", true);
        expect(hint("secondary").classes()).toContain("hint-active");

        window.dispatchEvent(new Event("blur"));
        await wrapper.vm.$nextTick();
        expect(hint("secondary").classes()).not.toContain("hint-active");
        expect(secondaryHints().length).toBe(0);
    });

    it("flips the escape hint between close, clear and back", async () => {
        expect(hint("escape").text()).toContain("close");
        expect(hint("help").exists()).toBe(true);
        // help sits opposite the bindings it explains
        expect(hint("help").classes()).toContain("hint-right");
        expect(hint("remove-scope").exists()).toBe(false);

        await type("t: align");
        expect(hint("escape").text()).toContain("clear");
        expect(hint("remove-scope").text()).toContain("remove filter");
        expect(hint("help").exists()).toBe(false);

        await press("Escape");
        expect(hint("escape").text()).toContain("back");
    });

    it("shows the category row only for an unscoped query", async () => {
        expect(categoryRow().exists()).toBe(false);
        expect(hint("category").exists()).toBe(false);

        await type("workflows");
        expect(categoryRow().exists()).toBe(true);
        expect(categoryRow().text()).toContain("All");
        expect(categoryRow().text()).toContain("Navigation");
        // actions have no category of their own, they only show under "All"
        expect(category("actions").exists()).toBe(false);
        expect(hint("category").text()).toContain("category");

        await type("t: align");
        expect(categoryRow().exists()).toBe(false);
    });

    it("reaches the category row with arrow up and hands the selection back", async () => {
        await type("workflows");
        expect(input().attributes("aria-activedescendant")).toBeTruthy();

        await press("ArrowUp");
        expect(categoryRow().classes()).toContain("row-selected");
        expect(hint("category").classes()).toContain("hint-active");
        // no result is selected while the row is
        expect(input().attributes("aria-activedescendant")).toBeUndefined();

        await press("ArrowDown");
        expect(categoryRow().classes()).not.toContain("row-selected");
        expect(input().attributes("aria-activedescendant")).toBeTruthy();

        // enter on the row is a way back to the list, never a navigation
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);
        await press("ArrowUp");
        await press("Enter");
        expect(push).not.toHaveBeenCalled();
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(categoryRow().classes()).not.toContain("row-selected");
        expect(input().attributes("aria-activedescendant")).toBeTruthy();
    });

    it("moves the category with left and right only while the row is selected", async () => {
        await type("workflows");
        const element = input().element as HTMLInputElement;
        element.setSelectionRange(3, 3);

        // the caret keeps the arrows while a result is selected
        const ignored = await sendKey("ArrowRight");
        expect(ignored.defaultPrevented).toBe(false);
        expect(element.selectionStart).toBe(3);
        expect(category("all").attributes("aria-selected")).toBe("true");

        await press("ArrowUp");
        const handled = await sendKey("ArrowRight");
        expect(handled.defaultPrevented).toBe(true);
        expect(element.selectionStart).toBe(3);
        expect(category("all").attributes("aria-selected")).toBe("false");
        expect(category("workflows").attributes("aria-selected")).toBe("true");
        // the row keeps the selection, so the next arrow moves on
        expect(categoryRow().classes()).toContain("row-selected");

        await sendKey("ArrowLeft");
        expect(category("all").attributes("aria-selected")).toBe("true");
    });

    it("narrows the sections to the picked category", async () => {
        const pageStore = usePageStore();
        pageStore.summariesById = { p1: { id: "p1", title: "Lab notes", slug: "lab-notes" } as never };
        pageStore.idsByVariant.my = ["p1"];

        await type("lab notes");
        expect(sectionIds()).toContain("palette section pages");

        await pickCategory("pages");
        expect(category("pages").attributes("aria-selected")).toBe("true");
        // only the pages provider runs, through its own scoped search
        expect(sectionIds()).toEqual(["palette section pages:latest"]);
        expect(wrapper.text()).toContain("Lab notes");

        await pickCategory("navigation");
        expect(sectionIds()).not.toContain("palette section pages");

        await pickCategory("all");
        expect(sectionIds()).toContain("palette section pages");
    });

    it("resets the category when the query is cleared", async () => {
        await type("workflows");
        await pickCategory("tools");
        expect(category("tools").attributes("aria-selected")).toBe("true");

        await press("Escape");
        expect(categoryRow().exists()).toBe(false);

        await type("workflows");
        expect(category("all").attributes("aria-selected")).toBe("true");
    });

    it("hands focus back to the input after a category chip is clicked", async () => {
        await type("workflows");
        const focus = spyOnInputFocus();

        await pickCategory("tools");
        expect(focus).toHaveBeenCalled();
        // the row keeps the selection, so the arrows keep moving the category
        expect(categoryRow().classes()).toContain("row-selected");
    });

    it("runs a single search while the arrow keys sweep across the category row", async () => {
        await type("rna");
        await press("ArrowUp");
        expect(categoryRow().classes()).toContain("row-selected");

        const workflows = countScopedSearches(workflowsProvider);
        const histories = countScopedSearches(historiesProvider);
        const datasets = countScopedSearches(datasetsProvider);
        try {
            // a held arrow key sweeps over the categories in between
            await pressNow("ArrowRight");
            await pressNow("ArrowRight");
            await pressNow("ArrowRight");
            await settle();

            expect(category("datasets").attributes("aria-selected")).toBe("true");
            expect(workflows.calls).toBe(0);
            expect(histories.calls).toBe(0);
            expect(datasets.calls).toBe(1);
        } finally {
            workflows.restore();
            histories.restore();
            datasets.restore();
        }
    });

    it("returns focus to the input when a clicked help row keeps the palette open", async () => {
        await type("?");
        const focus = spyOnInputFocus();

        await optionRow("Search my workflows")?.trigger("click");
        await settle();

        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("My workflows");
        expect(focus).toHaveBeenCalled();
    });

    it("returns focus to the input when a clicked row enters argument mode", async () => {
        await type("> upload");
        const focus = spyOnInputFocus();

        await optionRow("Upload data")?.trigger("click", { shiftKey: true });
        await settle();

        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("Upload data");
        expect(focus).toHaveBeenCalled();
    });

    it("holds the focus in the input when the dialog chrome is pressed", async () => {
        // the footer, a section title and every other gap around the controls
        // would take the focus away, leaving the palette unusable by keyboard
        expect(sendMousedown(wrapper.find(".palette-footer").element).defaultPrevented).toBe(true);
        expect(sendMousedown(wrapper.find(".palette-section-title").element).defaultPrevented).toBe(true);

        // the input keeps its own default, so the caret and the text selection
        // still answer to the mouse
        expect(sendMousedown(input().element).defaultPrevented).toBe(false);
    });

    it("routes a native dialog cancel through the stepwise escape", async () => {
        await type("t: align");
        const dialog = wrapper.find("dialog");

        function sendCancel() {
            const event = new Event("cancel", { cancelable: true });
            dialog.element.dispatchEvent(event);
            return event;
        }

        // the browser would close the dialog outright, the palette clears first
        const cleared = sendCancel();
        await settle();
        expect(cleared.defaultPrevented).toBe(true);
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(inputValue()).toBe("");
        expect(badge().exists()).toBe(true);

        sendCancel();
        await settle();
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().exists()).toBe(false);

        sendCancel();
        await settle();
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("hands the selection back to the results when the query is emptied on the category row", async () => {
        await type("workflows");
        await press("ArrowUp");
        expect(input().attributes("aria-activedescendant")).toBeUndefined();

        (input().element as HTMLInputElement).value = "";
        await input().trigger("input");
        // the row is gone the moment the query is, so the selection may not
        // stay on it - enter has to keep working before the search catches up
        expect(categoryRow().exists()).toBe(false);
        expect(input().attributes("aria-activedescendant")).toBeTruthy();

        await settle();
        expect(input().attributes("aria-activedescendant")).toBeTruthy();
    });

    it("renders entity names verbatim instead of looking them up in the locale", async () => {
        const pageStore = usePageStore();
        // a name colliding with an object property: localizing it would render
        // whatever the locale dictionary resolves that key to
        pageStore.summariesById = { p1: { id: "p1", title: "constructor", slug: "notes" } as never };
        pageStore.idsByVariant.my = ["p1"];

        await type("constructor");
        const row = optionRow("constructor");
        expect(row).toBeDefined();
        expect(row?.text()).not.toContain("native code");
    });

    it("drops the previous results while the new scope is still fetching", async () => {
        expect(wrapper.text()).toContain("Upload data");

        const original = workflowsProvider.searchScoped;
        let land: () => void = () => {};
        const pending = new Promise<never[]>((resolve) => {
            land = () => resolve([]);
        });
        workflowsProvider.searchScoped = () => pending;
        try {
            await type("w: rna");

            expect(badge().text()).toContain("My workflows");
            // the root actions may not keep rendering under the new badge
            expect(wrapper.text()).not.toContain("Upload data");
            expect(wrapper.find("[data-description='palette searching']").exists()).toBe(true);
            expect(wrapper.find("[data-description='palette empty']").exists()).toBe(false);

            land();
            await settle();
            expect(wrapper.find("[data-description='palette searching']").exists()).toBe(false);
            expect(wrapper.find("[data-description='palette empty']").exists()).toBe(true);
        } finally {
            workflowsProvider.searchScoped = original;
        }
    });

    it("renders every provider as it answers and holds the slow one's place", async () => {
        const tools = stallSearch(toolsProvider);
        try {
            await type("workflows");

            // one slow provider may not cost the sections that already answered
            expect(optionRow("Workflows")).toBeDefined();
            expect(sectionIds()).toContain("palette section tools");
            expect(skeletons().length).toBe(3);
            expect(inputIcons()).toContain("spinner");

            tools.land([{ id: "tools:filter", title: "Filter workflows", to: "/?tool_id=filter" }]);
            await settle();

            expect(skeletons().length).toBe(0);
            expect(inputIcons()).not.toContain("spinner");
            expect(wrapper.text()).toContain("Filter workflows");
            // sorted best match first, once, now that every provider landed
            expect(sectionIds()[0]).toBe("palette section navigation");
        } finally {
            tools.restore();
        }
    });

    it("keeps the rendered rows while the next keystroke is searched", async () => {
        await type("workflows");
        expect(optionRow("Workflows")).toBeDefined();

        const navigation = stallSearch(navigationProvider);
        try {
            await type("workflowsx");

            // the rows of the previous keystroke stand until the provider answers
            expect(optionRow("Workflows")).toBeDefined();
            expect(sectionIds()).toContain("palette section navigation");
            expect(skeletons().length).toBe(0);

            navigation.land([]);
            await settle();

            expect(optionRow("Workflows")).toBeUndefined();
        } finally {
            navigation.restore();
        }
    });

    it("drops the results of a fan-out a newer search has replaced", async () => {
        const tools = stallSearch(toolsProvider);
        try {
            await type("workflows");

            // the next keystroke owns the sections now
            toolsProvider.search = () => [{ id: "tools:fresh", title: "Fresh tool", to: "/?tool_id=fresh" }];
            await type("workflow");

            tools.land([{ id: "tools:stale", title: "Stale tool", to: "/?tool_id=stale" }]);
            await settle();

            expect(wrapper.text()).not.toContain("Stale tool");
            expect(wrapper.text()).toContain("Fresh tool");
        } finally {
            tools.restore();
        }
    });

    it("keeps the selection on the same row across the final sort", async () => {
        const pages = stallSearch(pagesProvider);
        try {
            await type("workflow");
            await press("ArrowDown");
            const selected = selectedRow().text();
            expect(selected).toBeTruthy();

            // an exact match landing last outranks every section on screen, so
            // the sort pushes the selected row down the list
            pages.land([{ id: "pages:p1", title: "workflow", to: "/pages/p1" }]);
            await settle();

            expect(sectionIds()[0]).toBe("palette section pages");
            expect(selectedRow().text()).toBe(selected);
        } finally {
            pages.restore();
        }
    });

    it("keeps a selection moved back to the first row across the final sort", async () => {
        const pages = stallSearch(pagesProvider);
        try {
            await type("workflow");
            await press("ArrowDown");
            await press("ArrowUp");
            const selected = selectedRow().text();
            expect(selected).toBeTruthy();

            // the row the user pointed at may not be swapped for the exact match
            // the sort brings to the top, first row or not
            pages.land([{ id: "pages:p1", title: "workflow", to: "/pages/p1" }]);
            await settle();

            expect(sectionIds()[0]).toBe("palette section pages");
            expect(selectedRow().text()).toBe(selected);
        } finally {
            pages.restore();
        }
    });

    it("says a scope could not be loaded instead of calling it empty", async () => {
        const original = workflowsProvider.searchScoped;
        workflowsProvider.searchScoped = () => Promise.reject(new PaletteFetchError());
        try {
            await type("w: rna");

            const error = wrapper.find("[data-description='palette error']");
            expect(error.exists()).toBe(true);
            expect(error.text()).toContain("Couldn't load my workflows");
            expect(wrapper.find("[data-description='palette empty']").exists()).toBe(false);
        } finally {
            workflowsProvider.searchScoped = original;
        }

        // the next search clears it again
        await type("t: align");
        expect(wrapper.find("[data-description='palette error']").exists()).toBe(false);
    });

    it("keeps a scope token the user may not use as plain text", async () => {
        // interactivetools_enable is off in the mocked config
        await type("it: jupyter");
        expect(badge().exists()).toBe(false);
        expect(inputValue()).toBe("it: jupyter");
    });

    it("offers a login when an anonymous visitor types a scope that needs one", async () => {
        browseAnonymously();
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);

        await type("w:rna");
        // the token never became a badge, so the offer stands in its place
        expect(badge().exists()).toBe(false);
        expect(loginPrompt().text()).toContain("Log in to search my workflows");
        expect(loginPrompt().text()).toContain("Create a Galaxy account");

        // the offer is made of ordinary rows, so enter reaches it like any result
        await press("Enter");
        expect(push).toHaveBeenCalledWith(`/login/start?redirect=${encodeURIComponent("/")}`);
    });

    it("says nothing about a scope this instance does not offer at all", async () => {
        browseAnonymously();

        // interactivetools_enable is off in the mocked config, so an account
        // would not unlock the scope either
        await type("it:jupyter");
        expect(loginPrompt().exists()).toBe(false);
        expect(inputValue()).toBe("it:jupyter");
    });

    it("hides the register row where the instance creates no local accounts", async () => {
        browseAnonymously();
        setMockConfig({ allow_local_account_creation: false });
        try {
            await type("h:");
            expect(loginPrompt().text()).toContain("Log in to search my histories");
            expect(loginPrompt().text()).not.toContain("Create a Galaxy account");
        } finally {
            resetMockConfig();
        }
    });

    it("registers through the single OIDC provider where local accounts are off", async () => {
        browseAnonymously();
        setMockConfig({
            allow_local_account_creation: false,
            oidc: { okta: { end_user_registration_endpoint: "https://okta.example.org/register" } },
        });
        const assign = vi.spyOn(window.location, "assign").mockImplementation(() => undefined);
        try {
            await type("h:");
            // the masthead offers a Register button here, so the palette does too
            const register = optionRow("Create a Galaxy account");
            expect(register).toBeDefined();

            await register?.trigger("click");
            expect(assign).toHaveBeenCalledWith("https://okta.example.org/register");
        } finally {
            assign.mockRestore();
            resetMockConfig();
        }
    });

    it("lists the scopes an account would add behind a lock in help mode", async () => {
        browseAnonymously();

        await type("?");
        // what an anonymous visitor may search is listed as it always is
        expect(wrapper.text()).toContain("Search public workflows");

        const locked = optionRow("Search my workflows");
        expect(locked?.find(".item-icon svg").attributes("data-icon")).toBe("lock");

        await locked?.trigger("click");
        await settle();

        // picking one types its token, which answers with the same login offer
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().exists()).toBe(false);
        expect(inputValue()).toBe("w: ");
        expect(loginPrompt().text()).toContain("Log in to search my workflows");
    });

    it("never searches, tabs or lists a provider the instance disabled", async () => {
        wrapper.destroy();
        useCommandPalette().closePalette();
        setMockConfig({ command_palette_disabled_providers: ["workflows"] });
        const search = vi.spyOn(workflowsProvider, "search");
        try {
            wrapper = mount(MountTarget as object, {
                localVue,
                router,
                pinia: createTestingPinia({ createSpy: vi.fn, stubActions: true }),
            });
            useCommandPalette().openPalette();
            await settle();

            await type("workflow");
            expect(sectionIds()).not.toContain("palette section workflows");
            expect(search).not.toHaveBeenCalled();
            // the category row loses the tab with it, the other providers keep theirs
            expect(category("workflows").exists()).toBe(false);
            expect(category("histories").exists()).toBe(true);

            // the scopes of a disabled provider are neither typeable nor offered
            await type("w: rna");
            expect(badge().exists()).toBe(false);
            expect(inputValue()).toBe("w: rna");

            await type("?");
            expect(wrapper.text()).not.toContain("Search my workflows");
            expect(wrapper.text()).toContain("Search my histories");
        } finally {
            search.mockRestore();
            resetMockConfig();
        }
    });

    it("leads the placeholder with the phrase the instance configured", async () => {
        const hint = "…  > actions · w: t: … scopes · ? help";
        expect(input().attributes("placeholder")).toBe(`Search Galaxy${hint}`);

        try {
            setMockConfig({ command_palette_placeholder: "Search UseGalaxy.eu" });
            await wrapper.vm.$nextTick();
            expect(input().attributes("placeholder")).toBe(`Search UseGalaxy.eu${hint}`);
        } finally {
            resetMockConfig();
        }
    });

    it("re-runs the search once the tool store finishes hydrating", async () => {
        wrapper.destroy();
        useCommandPalette().closePalette();

        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: true });
        const toolStore = useToolStore();
        let hydrate: () => void = () => {};
        const fetching = new Promise<void>((resolve) => {
            hydrate = resolve;
        });
        vi.mocked(toolStore.fetchTools).mockReturnValue(fetching as never);

        const searches = countEmptyQuerySearches(navigationProvider);
        try {
            wrapper = mount(MountTarget as object, { localVue, router, pinia });
            useCommandPalette().openPalette();
            await settle();

            const beforeHydration = searches.calls;
            expect(beforeHydration).toBeGreaterThan(0);

            hydrate();
            await settle();
            // the first open searched an empty tool cache, so it is run again
            expect(searches.calls).toBeGreaterThan(beforeHydration);

            // and only once - a second open must not hydrate, nor rerun, again
            useCommandPalette().closePalette();
            await settle();
            useCommandPalette().openPalette();
            await settle();
            expect(vi.mocked(toolStore.fetchTools)).toHaveBeenCalledTimes(1);
        } finally {
            searches.restore();
        }
    });

    it("animates in and closes through the transition fallback", async () => {
        const dialog = wrapper.find("dialog");
        expect(dialog.classes()).toContain("palette-open");

        const close = vi.spyOn(dialog.element as HTMLDialogElement, "close");
        useCommandPalette().closePalette();
        await wrapper.vm.$nextTick();
        // the panel fades out first, the dialog only closes once the transition
        // ends - or, with no transition events, after the timeout fallback
        expect(dialog.classes()).not.toContain("palette-open");

        await settle();
        expect(close).toHaveBeenCalled();
    });

    it("reopens on a toggle that lands during the close transition", async () => {
        const dialog = wrapper.find("dialog");
        const close = vi.spyOn(dialog.element as HTMLDialogElement, "close");

        useCommandPalette().closePalette();
        await wrapper.vm.$nextTick();
        // fading out, the dialog itself is still open
        expect(dialog.classes()).not.toContain("palette-open");
        expect((dialog.element as HTMLDialogElement).open).toBe(true);

        // ⌘K before the fade-out finished must land in the open state
        useCommandPalette().togglePalette();
        await settle();

        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(dialog.classes()).toContain("palette-open");
        // the interrupted close is disarmed, fallback timer included
        expect(close).not.toHaveBeenCalled();
        expect(wrapper.text()).toContain("Upload data");
    });

    it("ignores a close event a reopen has already superseded", async () => {
        const dialog = wrapper.find("dialog");
        expect((dialog.element as HTMLDialogElement).open).toBe(true);

        // the browser fires `close` in a task of its own, which a ⌘K gesture is
        // allowed to overtake: by the time it lands the dialog is showing again
        dialog.element.dispatchEvent(new Event("close"));
        await settle();

        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(dialog.classes()).toContain("palette-open");
    });

    it("closes on escape", async () => {
        await input().trigger("keydown", { key: "Escape" });
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("keeps the query and the badge when the palette is closed without escape", async () => {
        await type("t: align");
        expect(badge().text()).toContain("Tools");

        useCommandPalette().togglePalette();
        await settle();
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);

        useCommandPalette().togglePalette();
        await settle();

        // a mistaken toggle or backdrop click is taken back, not typed again
        expect(inputValue()).toBe("align");
        expect(badge().text()).toContain("Tools");
    });

    it("leaves an action's argument mode behind when a toggle closes the palette", async () => {
        await type("> upload");
        await press("Enter", { shiftKey: true });
        expect(badge().text()).toContain("Upload data");

        // a toggle is not escape, but an argument mode still must not outlive it
        useCommandPalette().togglePalette();
        await settle();
        useCommandPalette().togglePalette();
        await settle();

        expect(badge().exists()).toBe(false);
        expect(inputValue()).toBe("");

        await type(">");
        expect(badge().text()).toContain("Actions");
        expect(inputValue()).toBe("");
    });

    it("ignores enter while the rendered rows still belong to the previous mode", async () => {
        const pageStore = usePageStore();
        pageStore.summariesById = { p1: { id: "p1", title: "Lab notes", slug: "lab-notes" } as never };
        pageStore.idsByVariant.my = ["p1"];
        const push = vi.spyOn(router, "push").mockResolvedValue(undefined as never);

        await type("lab notes");
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("Lab notes");

        // the switch to the actions list is debounced, so enter lands while the
        // page row is still on screen and must not run it
        (input().element as HTMLInputElement).value = "> upload";
        await input().trigger("input");
        await input().trigger("keydown", { key: "Enter", shiftKey: true });

        expect(push).not.toHaveBeenCalled();
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);

        await settle();
        expect(wrapper.findAll("[role='option']").at(0).text()).toContain("Upload data");

        await press("Enter", { shiftKey: true });
        expect(badge().text()).toContain("Upload data");
        expect(inputValue()).toBe("");
    });

    it("reopens on a clean root state after escape closed the palette", async () => {
        await type("t: align");

        // escape is stepwise: the text goes, then the badge, then the palette
        await press("Escape");
        await press("Escape");
        await press("Escape");
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);

        useCommandPalette().openPalette();
        await settle();

        expect(inputValue()).toBe("");
        expect(badge().exists()).toBe(false);
        expect(wrapper.text()).toContain("Upload data");
    });

    it("toggles on the global ctrl/cmd+k shortcut", async () => {
        useCommandPalette().closePalette();

        window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, cancelable: true }));
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);

        window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true, cancelable: true }));
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });

    it("ignores plain 'k' without the platform modifier", () => {
        useCommandPalette().closePalette();

        window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", cancelable: true }));
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
    });
});
