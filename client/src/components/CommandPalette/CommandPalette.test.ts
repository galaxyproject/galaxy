import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { useServerMock } from "@/api/client/__mocks__";
import { useCommandPalette } from "@/composables/useCommandPalette";
import { useRecentPaletteItems } from "@/composables/useRecentPaletteItems";
import { usePageStore } from "@/stores/pageStore";
import { useUserStore } from "@/stores/userStore";
import { useVisualizationStore } from "@/stores/visualizationStore";

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

    async function type(query: string) {
        (input().element as HTMLInputElement).value = query;
        await input().trigger("input");
        await settle();
    }

    async function press(key: string, options: Record<string, unknown> = {}) {
        await input().trigger("keydown", { key, ...options });
        await settle();
    }

    /** Dispatches a real event, so the test can tell whether it was prevented */
    async function sendKey(key: string, options: Record<string, unknown> = {}) {
        const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...options });
        input().element.dispatchEvent(event);
        await settle();
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

    function sectionIds() {
        return wrapper
            .findAll("[data-description^='palette section ']")
            .wrappers.map((section) => section.attributes("data-description"));
    }

    async function holdModifier(down: boolean) {
        window.dispatchEvent(new KeyboardEvent(down ? "keydown" : "keyup", { key: "Control" }));
        await wrapper.vm.$nextTick();
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

        await press("Enter");
        expect(useCommandPalette().isPaletteOpen.value).toBe(true);
        expect(badge().text()).toContain("Actions");
        expect(wrapper.text()).toContain("Upload data");
    });

    it("documents every binding in the help keys section", async () => {
        await type("?");
        const text = wrapper.text();
        expect(text).toContain("Keys");
        expect(text).toContain("Open the selected result");
        expect(text).toContain("Remove the active filter");
        // the actions row stays listed above the scopes and the keys
        expect(text).toContain("Search actions");
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

        await holdModifier(true);
        expect(hint("open").classes()).not.toContain("hint-active");
        expect(hint("new-tab").classes()).toContain("hint-active");
        // only the selected row previews the external open
        expect(wrapper.findAll("[data-description='palette option external']").length).toBe(1);

        await holdModifier(false);
        expect(hint("new-tab").classes()).not.toContain("hint-active");
    });

    it("resets the held modifier when the window loses focus", async () => {
        await type("workflows");
        await holdModifier(true);
        expect(hint("new-tab").classes()).toContain("hint-active");

        // opening a new tab steals focus, so the keyup never reaches the window
        window.dispatchEvent(new Event("blur"));
        await wrapper.vm.$nextTick();
        expect(hint("new-tab").classes()).not.toContain("hint-active");
        expect(hint("open").classes()).toContain("hint-active");
    });

    it("flips the escape hint between close, clear and back", async () => {
        expect(hint("escape").text()).toContain("close");
        expect(hint("help").exists()).toBe(true);
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

    it("keeps a scope token the user may not use as plain text", async () => {
        // interactivetools_enable is off in the mocked config
        await type("it: jupyter");
        expect(badge().exists()).toBe(false);
        expect(inputValue()).toBe("it: jupyter");
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

    it("closes on escape", async () => {
        await input().trigger("keydown", { key: "Escape" });
        expect(useCommandPalette().isPaletteOpen.value).toBe(false);
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
