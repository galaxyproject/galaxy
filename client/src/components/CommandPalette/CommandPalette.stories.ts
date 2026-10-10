import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";
import { h, onMounted, onUnmounted, watch } from "vue";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import toolsList from "@/components/ToolsView/testData/toolsList.json";
import { useCommandPalette } from "@/composables/useCommandPalette";

import CommandPalette from "./CommandPalette.vue";

/**
 * The palette lives closed in the app shell until ctrl/cmd+k opens it, which it only does once
 * the configuration has loaded. Open it then, once mounted so its dialog exists, and close it
 * again on unmount, since the open state is shared by the whole app.
 */
const withPaletteOpen: Decorator = (story) => ({
    setup() {
        const { closePalette, openPalette, paletteEnabled } = useCommandPalette();
        onMounted(() => {
            watch(paletteEnabled, (enabled) => enabled && openPalette(), { immediate: true });
        });
        onUnmounted(closePalette);
    },
    render: () => h(story()),
});

/** A listing with nothing in it, the way Galaxy answers a search that matched nothing. */
function emptyListing(path: string) {
    return http.untyped.get(path, () => HttpResponse.json([], { headers: { total_matches: "0" } }));
}

/** Answers every workflow listing and search with the given response. */
function workflowListing(answer: () => Response | Promise<Response>) {
    return http.untyped.get("/api/workflows", answer);
}

const meta = {
    title: "CommandPalette",
    component: CommandPalette,
    decorators: [withPaletteOpen, withCurrentUser()],
    parameters: {
        msw: {
            handlers: {
                // the first open loads every tool, so recent tools resolve to their names; a
                // tool search (`q`) answers with the matching ids, of which there are none
                tools: http.untyped.get("/api/tools", ({ request }) =>
                    HttpResponse.json(new URL(request.url).searchParams.has("q") ? [] : toolsList),
                ),
                unprivilegedTools: http.get("/api/unprivileged_tools", ({ response }) => response(200).json([])),
                // a typed query also searches the backend listings, which hold nothing here
                workflows: emptyListing("/api/workflows"),
                histories: emptyListing("/api/histories"),
                pages: emptyListing("/api/pages"),
            },
        },
    },
} satisfies Meta<typeof CommandPalette>;

export default meta;
type Story = StoryObj<typeof meta>;

type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The root placeholder, naming the syntax the palette understands */
const ROOT_PLACEHOLDER = "Search Galaxy…  > actions · w: t: … scopes · ? help";

/** The palette opens once the configuration has loaded, so the first wait is a long one. */
async function seeInput({ canvas, step }: PlayContext) {
    let input!: HTMLInputElement;
    await step("See the palette open with the search box focused", async () => {
        input = await canvas.findByRole("combobox", { name: "Search Galaxy" }, { timeout: 5000 });
        await waitFor(() => expect(input).toHaveFocus());
        // the palette fades in a couple of frames after it opens
        await seeOpen({ canvas } as PlayContext);
    });
    return input;
}

/** Opens the palette and pastes `query` into it, the way a whole query lands at once. */
async function openAndPaste(context: PlayContext, query: string) {
    const input = await seeInput(context);
    await context.step(`Paste "${query}"`, async () => {
        await context.userEvent.paste(query);
    });
    return input;
}

/** Opens the palette and types `query` into it. */
async function openAndType(context: PlayContext, query: string) {
    const input = await seeInput(context);
    await context.step(`Type "${query}"`, async () => {
        await context.userEvent.type(input, query);
    });
    return input;
}

function results({ canvas }: PlayContext) {
    return canvas.getByRole("listbox", { name: "Search results" });
}

/** The result sections, named by their titles, in order. */
function sectionNames(context: PlayContext) {
    return within(results(context))
        .queryAllByRole("group")
        .map((section) => section.getAttribute("aria-label"));
}

async function seeSections(context: PlayContext, names: string[]) {
    await waitFor(() => expect(sectionNames(context)).toEqual(names), { timeout: 3000 });
}

function section(context: PlayContext, name: string) {
    return within(results(context)).getByRole("group", { name });
}

/** The first result, the one enter would run. */
async function seeFirstResult(context: PlayContext, name: RegExp) {
    await waitFor(() => expect(within(results(context)).getAllByRole("option")[0]).toHaveAccessibleName(name), {
        timeout: 3000,
    });
}

/** The badge standing for the active filter; its accessible name is how it is removed. */
function badge({ canvas }: PlayContext) {
    return canvas.queryByRole("button", { name: /^Remove filter: / });
}

async function seeBadge(context: PlayContext, label: string) {
    await waitFor(() => expect(badge(context)).toHaveAccessibleName(`Remove filter: ${label}`));
    await expect(badge(context)).toHaveTextContent(new RegExp(`^\\s*${label}\\s*$`));
}

/**
 * The footer hint for `keys`, as one line ("esc close"), or null if the footer doesn't have it.
 * A narrow palette hides the optional hints (⌫, ←→, ↑↓), and the browser project renders at
 * phone width, so a hint present but hidden reads "hidden".
 */
function footerHint({ canvas }: PlayContext, keys: string) {
    const hint = within(canvas.getByRole("dialog"))
        .queryAllByText(keys, { selector: "kbd" })
        .find((key) => !key.closest("[role='option']"))?.parentElement;
    if (!hint) {
        return null;
    }
    return hint.checkVisibility() ? hint.textContent!.replace(/\s+/g, " ").trim() : "hidden";
}

/** Keys pressed with shift held, as shift+enter is typed. */
async function pressWithShift({ userEvent }: PlayContext, key: string) {
    await userEvent.keyboard(`{Shift>}{${key}}{/Shift}`);
}

/**
 * Sees the palette open and staying open. A closing palette fades out before its dialog closes,
 * so wait out any fade under way first: a palette fading in ends visible, one fading out doesn't.
 */
async function seeOpen({ canvas }: PlayContext) {
    await new Promise((resolve) => requestAnimationFrame(resolve));
    await Promise.all(
        canvas
            .getByRole("dialog")
            .getAnimations()
            .map((animation) => animation.finished),
    );
    await waitFor(() => expect(canvas.getByRole("dialog")).toBeVisible());
}

/** Waits out the search debounce, so a result that would replace a hint has had its chance. */
async function waitOutSearch() {
    await new Promise((resolve) => setTimeout(resolve, 600));
}

async function seeClosed({ canvas }: PlayContext) {
    await waitFor(() => expect(canvas.queryByRole("dialog")).not.toBeInTheDocument());
}

/** The palette's text hint below the results, such as "No results." */
function hintText({ canvas }: PlayContext, text: string | RegExp) {
    return within(canvas.getByRole("dialog")).queryByText(text);
}

/** Opened by a signed-in user with nothing typed: the actions and pages they can jump to. */
export const Open: Story = {
    play: async (context) => {
        const input = await seeInput(context);
        await context.step("See the actions, then the pages to jump to", async () => {
            await seeSections(context, ["Actions", "Navigation"]);
            await expect(within(section(context, "Actions")).getAllByRole("option")[0]).toHaveAccessibleName(
                "Upload data Upload files from disk, URL or pasted content",
            );
            await expect(input).toHaveAttribute("placeholder", ROOT_PLACEHOLDER);
        });
        await context.step("See escape close the palette and ? open the help", async () => {
            await expect(footerHint(context, "esc")).toBe("esc close");
            await expect(footerHint(context, "?")).toBe("? help");
            await expect(footerHint(context, "⌫")).toBeNull();
        });
    },
};

/**
 * Opened by a visitor without an account: fewer actions and pages, and a scope that needs an
 * account (`w:` for my workflows) offers a login instead. This Galaxy lets visitors register.
 */
export const AnonymousVisitor: Story = {
    parameters: {
        ...viewedBy(getFakeAnonymousUser()),
        msw: { handlers: { configuration: configurationHandler({ allow_local_account_creation: true }) } },
    },
};

/** A query searches everything; the matching page is the first result. */
export const FiltersWhileTyping: Story = {
    play: async (context) => {
        await openAndType(context, "workflows");
        await context.step("See the Workflows page first, then the matching action", async () => {
            await seeFirstResult(context, /^Workflows Displays a panel to search and access workflows\.$/);
            await seeSections(context, ["Navigation", "Actions"]);
        });
    },
};

/** A query offers the categories to narrow it to; a scoped one doesn't. */
export const OffersCategoriesWhileSearching: Story = {
    play: async (context) => {
        const input = await seeInput(context);
        await context.step("See no categories with nothing typed", async () => {
            await seeSections(context, ["Actions", "Navigation"]);
            await expect(context.canvas.queryByRole("tablist")).not.toBeInTheDocument();
        });
        await context.step('Type "workflows"; see a category per kind of result', async () => {
            await context.userEvent.type(input, "workflows");
            const categories = await context.canvas.findByRole("tablist", { name: "Result categories" });
            // actions have no category of their own, they only show under "All"
            await expect(
                within(categories)
                    .getAllByRole("tab")
                    .map((tab) => tab.textContent!.trim()),
            ).toEqual([
                "All",
                "Workflows",
                "Histories",
                "Datasets",
                "Visualizations",
                "Invocations",
                "Reports",
                "Tools",
                "Navigation",
            ]);
            await expect(within(categories).getByRole("tab", { name: "All" })).toHaveAttribute("aria-selected", "true");
        });
        await context.step('Search tools for "align" instead; see the categories go', async () => {
            await context.userEvent.clear(input);
            await context.userEvent.paste("t: align");
            await seeBadge(context, "Tools");
            await expect(context.canvas.queryByRole("tablist")).not.toBeInTheDocument();
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** ">" narrows the palette to its actions. */
export const ScopesToActions: Story = {
    play: async (context) => {
        await openAndType(context, ">");
        await context.step("See an Actions badge and only the actions", async () => {
            await seeBadge(context, "Actions");
            await seeSections(context, ["Actions"]);
            await expect(within(section(context, "Actions")).getAllByRole("option")[0]).toHaveAccessibleName(
                /^Upload data /,
            );
        });
    },
};

/** A scope token ("t:") turns into a badge and leaves only the query in the box. */
export const TurnsScopeIntoBadge: Story = {
    play: async (context) => {
        const input = await openAndPaste(context, "t: align");
        await context.step("See a Tools badge and the query left in the box", async () => {
            await seeBadge(context, "Tools");
            await expect(input).toHaveValue("align");
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Clicking the badge removes the filter and keeps the typed query. */
export const RemovesBadgeByClick: Story = {
    play: async (context) => {
        const input = await openAndPaste(context, "t: align");
        await seeBadge(context, "Tools");
        await context.step("Click the badge; see it gone, the query kept and the box focused", async () => {
            await context.userEvent.click(badge(context)!);
            await waitFor(() => expect(badge(context)).not.toBeInTheDocument());
            await expect(input).toHaveValue("align");
            await expect(input).toHaveFocus();
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Backspace in an empty scoped box removes the badge. */
export const PopsBadgeOnBackspace: Story = {
    play: async (context) => {
        const input = await openAndType(context, "t:");
        await context.step("See a Tools badge and a tool search box", async () => {
            await seeBadge(context, "Tools");
            await expect(input).toHaveValue("");
            await expect(input).toHaveAttribute("placeholder", "Search tools…");
        });
        await context.step("Press backspace; see the badge gone and everything searched again", async () => {
            await context.userEvent.keyboard("{Backspace}");
            await waitFor(() => expect(badge(context)).not.toBeInTheDocument());
            await seeSections(context, ["Actions", "Navigation"]);
        });
    },
};

/** Backspace inside the query edits the text and leaves the badge alone. */
export const KeepsBadgeWhileEditing: Story = {
    play: async (context) => {
        const input = await openAndPaste(context, "t: align");
        await seeBadge(context, "Tools");
        await context.step('Move the caret after "al" and press backspace; see only the "l" go', async () => {
            await context.userEvent.keyboard("{ArrowLeft>3/}{Backspace}");
            await expect(input).toHaveValue("aign");
            await seeBadge(context, "Tools");
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Escape clears the text, then removes the badge, then closes; the footer says which comes next. */
export const StepsBackOnEscape: Story = {
    play: async (context) => {
        const input = await openAndPaste(context, "t: align");
        await context.step("See escape offer to clear the text", async () => {
            await seeBadge(context, "Tools");
            await expect(footerHint(context, "esc")).toBe("esc clear");
            await expect(footerHint(context, "?")).toBeNull();
        });
        await context.step("Press escape; see the text cleared and the badge kept", async () => {
            await context.userEvent.keyboard("{Escape}");
            await expect(input).toHaveValue("");
            await seeBadge(context, "Tools");
            await seeOpen(context);
            await expect(footerHint(context, "esc")).toBe("esc back");
        });
        await context.step("Press escape; see the badge gone and the palette still open", async () => {
            await context.userEvent.keyboard("{Escape}");
            await waitFor(() => expect(badge(context)).not.toBeInTheDocument());
            await seeOpen(context);
            await expect(footerHint(context, "esc")).toBe("esc close");
            await expect(footerHint(context, "?")).toBe("? help");
        });
        await context.step("Press escape; see the palette close", async () => {
            await context.userEvent.keyboard("{Escape}");
            await seeClosed(context);
        });
    },
};

/** "?" lists the scopes, actions and keys; enter applies the first scope. */
export const ExplainsShortcuts: Story = {
    play: async (context) => {
        const input = await openAndType(context, "?");
        await context.step("See the scopes, then the actions, then the keys", async () => {
            await seeSections(context, ["Scopes", "Actions", "Keys"]);
            await expect(input).toHaveAttribute("placeholder", "Search shortcuts…");
            const scopes = within(section(context, "Scopes"));
            await expect(scopes.getAllByRole("option")[0]).toHaveAccessibleName("Search my workflows (w:)");
            // gated behind interactivetools_enable, which this Galaxy leaves off
            await expect(within(results(context)).queryByText(/interactive tools/)).not.toBeInTheDocument();
            // the key badge is decorative, so each row names its shortcut itself
            const keys = within(section(context, "Keys"));
            await expect(keys.getByRole("option", { name: "Open the selected result (↵)" })).toBeVisible();
            await expect(keys.getByRole("option", { name: "Remove the active filter (⌫)" })).toBeVisible();
        });
        await context.step("Press enter; see my workflows searched", async () => {
            await context.userEvent.keyboard("{Enter}");
            await seeBadge(context, "My workflows");
            await seeOpen(context);
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A help row for an action narrows the palette to that action. */
export const AppliesActionFromHelp: Story = {
    play: async (context) => {
        const input = await openAndType(context, "?");
        let upload!: HTMLElement;
        await context.step("See a help row per action, naming the > that reaches it", async () => {
            await seeSections(context, ["Scopes", "Actions", "Keys"]);
            const actions = within(section(context, "Actions"));
            upload = actions.getByRole("option", { name: "Upload data (>)" });
            await expect(actions.getByRole("option", { name: "Create workflow (>)" })).toBeVisible();
        });
        await context.step("Click Upload data; see the action searched, typing still in the box", async () => {
            await context.userEvent.click(upload);
            await seeBadge(context, "Actions");
            await expect(input).toHaveValue("Upload data");
            await seeFirstResult(context, /^Upload data /);
            await expect(input).toHaveFocus();
        });
    },
};

/** A clicked scope row in the help applies the scope and hands typing back to the box. */
export const AppliesScopeFromHelp: Story = {
    play: async (context) => {
        const input = await openAndType(context, "?");
        await context.step("Click Search my workflows; see the scope applied and the box focused", async () => {
            await seeSections(context, ["Scopes", "Actions", "Keys"]);
            await context.userEvent.click(context.canvas.getByRole("option", { name: "Search my workflows (w:)" }));
            await seeBadge(context, "My workflows");
            await seeOpen(context);
            await expect(input).toHaveFocus();
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Opens Upload data's argument mode with shift+enter. */
async function pickUploadMethod(context: PlayContext) {
    const input = await openAndType(context, ">upload");
    await context.step("See Upload data first, with shift+enter to pick a method", async () => {
        await seeFirstResult(context, /^Upload data /);
        await expect(footerHint(context, "⇧↵")).toBe("⇧↵ pick a method");
    });
    await context.step("Press shift+enter; see the upload methods to pick from", async () => {
        await pressWithShift(context, "Enter");
        await seeBadge(context, "Upload data");
        await expect(input).toHaveValue("");
        await expect(await context.canvas.findByRole("option", { name: /^Paste File Content/ })).toBeVisible();
        await seeOpen(context);
    });
    return input;
}

/** Shift+enter on Upload data asks how to upload, and enter will run the picked method. */
export const PicksUploadMethod: Story = {
    play: async (context) => {
        await pickUploadMethod(context);
        await context.step("See enter run the method", async () => {
            await expect(footerHint(context, "↵")).toBe("↵ run");
        });
    },
};

/** Backspace in the empty method box leaves Upload data's argument mode. */
export const LeavesUploadMethodsOnBackspace: Story = {
    play: async (context) => {
        await pickUploadMethod(context);
        await context.step("Press backspace; see the badge gone and everything searched again", async () => {
            await context.userEvent.keyboard("{Backspace}");
            await waitFor(() => expect(badge(context)).not.toBeInTheDocument());
            await seeSections(context, ["Actions", "Navigation"]);
        });
    },
};

/** Shift-clicking Upload data asks how to upload, with typing still in the box. */
export const PicksUploadMethodByClick: Story = {
    play: async (context) => {
        const input = await openAndType(context, ">upload");
        await seeFirstResult(context, /^Upload data /);
        await context.step("Shift-click Upload data; see the methods asked for, the box focused", async () => {
            const upload = within(results(context)).getAllByRole("option")[0]!;
            await context.userEvent.keyboard("{Shift>}");
            await context.userEvent.click(upload);
            await context.userEvent.keyboard("{/Shift}");
            await seeBadge(context, "Upload data");
            await seeOpen(context);
            await expect(input).toHaveFocus();
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Run workflow has no default to run, so plain enter asks which workflow. */
export const OpensWorkflowPicker: Story = {
    play: async (context) => {
        await openAndType(context, ">run workflow");
        await seeFirstResult(context, /^Run workflow /);
        await context.step("Press enter; see the palette ask which workflow to run", async () => {
            await context.userEvent.keyboard("{Enter}");
            await seeBadge(context, "Run workflow");
            await seeOpen(context);
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Create new history asks for a name instead of reporting no results. */
export const PromptsForHistoryName: Story = {
    play: async (context) => {
        const input = await openAndType(context, ">create new history");
        await seeFirstResult(context, /^Create new history /);
        await context.step("Press shift+enter; see the palette ask for a name", async () => {
            await pressWithShift(context, "Enter");
            await seeBadge(context, "Create new history");
            await waitOutSearch();
            await expect(hintText(context, /^Type a name for the new history…$/)).toBeVisible();
            await expect(hintText(context, "No results.")).not.toBeInTheDocument();
        });
        await context.step('Type "rna seq"; see the history it would create', async () => {
            await context.userEvent.type(input, "rna seq");
            await seeFirstResult(context, /^Create history named 'rna seq'/);
            await expect(hintText(context, /^Type a name/)).not.toBeInTheDocument();
        });
        await context.step("Clear the name; see the palette ask again", async () => {
            await context.userEvent.clear(input);
            await waitOutSearch();
            await expect(context.canvas.getByText(/^Type a name for the new history…$/)).toBeVisible();
            await seeBadge(context, "Create new history");
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A report title of spaces alone is still no title, so the palette keeps asking. */
export const KeepsAskingForReportTitle: Story = {
    play: async (context) => {
        const input = await openAndType(context, ">create new report");
        await seeFirstResult(context, /^Create new report /);
        await context.step("Press shift+enter and type spaces; see the palette still ask for a title", async () => {
            await pressWithShift(context, "Enter");
            await seeBadge(context, "Create new report");
            await context.userEvent.type(input, "   ");
            await waitOutSearch();
            await expect(input).toHaveValue("   ");
            await expect(hintText(context, /^Type a title for the new report…$/)).toBeVisible();
            await expect(hintText(context, "No results.")).not.toBeInTheDocument();
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A picked category hands typing back to the box, and an emptied query forgets it. */
export const ResetsCategoryOnClear: Story = {
    play: async (context) => {
        const input = await openAndType(context, "workflows");
        await context.step("Click the Tools category; see it picked and the box focused", async () => {
            const categories = await context.canvas.findByRole("tablist", { name: "Result categories" });
            await context.userEvent.click(within(categories).getByRole("tab", { name: "Tools" }));
            await waitFor(() =>
                expect(within(categories).getByRole("tab", { name: "Tools" })).toHaveAttribute("aria-selected", "true"),
            );
            await expect(input).toHaveFocus();
        });
        await context.step("Press escape; see the query and the categories gone", async () => {
            await context.userEvent.keyboard("{Escape}");
            await expect(input).toHaveValue("");
            await waitFor(() => expect(context.canvas.queryByRole("tablist")).not.toBeInTheDocument());
        });
        await context.step('Type "workflows" again; see All picked', async () => {
            await context.userEvent.type(input, "workflows");
            const categories = await context.canvas.findByRole("tablist", { name: "Result categories" });
            await expect(within(categories).getByRole("tab", { name: "All" })).toHaveAttribute("aria-selected", "true");
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Clicking around the palette, not on a control, leaves typing in the box. */
export const KeepsFocusOnChrome: Story = {
    play: async (context) => {
        const input = await seeInput(context);
        await seeSections(context, ["Actions", "Navigation"]);
        await context.step("Click the footer; see the box still focused", async () => {
            const escapeHint = within(context.canvas.getByRole("dialog")).getByText("close");
            await expect(escapeHint).toBeVisible();
            await context.userEvent.click(escapeHint);
            await expect(input).toHaveFocus();
        });
        await context.step("Click a section title; see the box still focused", async () => {
            await context.userEvent.click(within(section(context, "Actions")).getByText("Actions"));
            await expect(input).toHaveFocus();
        });
    },
};

/** A scope reaches its own search, which found nothing. */
export const SearchesScopeWithNoResults: Story = {
    play: async (context) => {
        await openAndPaste(context, "w: rna");
        await context.step("See my workflows searched and nothing found", async () => {
            await seeBadge(context, "My workflows");
            await expect(await context.canvas.findByText("No results.", {}, { timeout: 3000 })).toBeVisible();
            await expect(hintText(context, /has no results provider/)).not.toBeInTheDocument();
            // a signed-in user is never asked to log in for a scope they already have
            await expect(context.canvas.queryByRole("group", { name: "Log in required" })).not.toBeInTheDocument();
        });
    },

    // TODO a11y: aria-required-children (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** Galaxy fails to list workflows, so the scope says so instead of calling itself empty. */
export const ReportsScopeLoadFailure: Story = {
    parameters: {
        // TODO a11y: aria-required-children (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: {
            handlers: {
                workflows: workflowListing(() =>
                    HttpResponse.json({ err_msg: "Internal server error", err_code: 500 }, { status: 500 }),
                ),
            },
        },
    },
    play: async (context) => {
        const input = await openAndPaste(context, "w: rna");
        await context.step("See my workflows reported as not loaded", async () => {
            await seeBadge(context, "My workflows");
            await expect(await context.canvas.findByText(/^Couldn't load/, {}, { timeout: 3000 })).toHaveTextContent(
                /^Couldn't load my workflows\. Try again\.$/,
            );
            await expect(hintText(context, "No results.")).not.toBeInTheDocument();
        });
        await context.step("Search tools instead; see the failure gone", async () => {
            await context.userEvent.clear(input);
            await context.userEvent.paste("t: align");
            await seeBadge(context, "Tools");
            await waitFor(() => expect(hintText(context, /^Couldn't load/)).not.toBeInTheDocument());
        });
    },
};

/** Lets the workflow listings `workflowsHeld` holds answer, and every later one at once. */
let answerWorkflows: () => void = () => {};
let workflowsAnswered: Promise<void> = Promise.resolve();

/** Holds the workflow listings until the play calls `answerWorkflows`. */
function holdWorkflows() {
    workflowsAnswered = new Promise((resolve) => {
        answerWorkflows = resolve;
    });
}

/** Galaxy takes its time listing workflows, answering only once the play lets it. */
const workflowsHeld = workflowListing(async () => {
    await workflowsAnswered;
    return HttpResponse.json([], { headers: { total_matches: "0" } });
});

/** While a scope is still searching, the palette says so rather than showing the previous results. */
export const SearchesScopeFromScratch: Story = {
    parameters: {
        // TODO a11y: aria-required-children (2026-10-10 audit).
        a11y: { test: "todo" },
        msw: { handlers: { workflows: workflowsHeld } },
    },
    play: async (context) => {
        holdWorkflows();
        await seeInput(context);
        await context.step("See the actions offered", async () => {
            await seeSections(context, ["Actions", "Navigation"]);
            await expect(context.canvas.getByRole("option", { name: /^Upload data / })).toBeVisible();
        });
        await context.step('Paste "w: rna"; see it searching, the actions gone', async () => {
            await context.userEvent.paste("w: rna");
            await seeBadge(context, "My workflows");
            await expect(await context.canvas.findByText("Searching…", {}, { timeout: 3000 })).toBeVisible();
            await expect(within(results(context)).queryByText(/Upload data/)).not.toBeInTheDocument();
            await expect(hintText(context, "No results.")).not.toBeInTheDocument();
        });
        await context.step("Let Galaxy answer; see nothing found, outside any result list or group", async () => {
            answerWorkflows();
            const empty = await context.canvas.findByText("No results.", {}, { timeout: 3000 });
            await expect(empty).toBeVisible();
            await expect(hintText(context, "Searching…")).not.toBeInTheDocument();
            await expect(context.canvasElement).toContainElement(empty);
            await expect(empty.closest("[role='listbox']")).toBeNull();
            await expect(context.canvasElement.querySelector("[role='group']")).toBeNull();
        });
    },
};

/** A token for a scope this Galaxy doesn't offer ("it:" without interactive tools) stays text. */
export const KeepsUnavailableScopeAsText: Story = {
    play: async (context) => {
        const input = await openAndType(context, "it: jupyter");
        await context.step("See it searched as plain text, with no badge", async () => {
            // the category row only shows for an unscoped query
            await context.canvas.findByRole("tablist", { name: "Result categories" }, { timeout: 3000 });
            await expect(badge(context)).not.toBeInTheDocument();
            await expect(input).toHaveValue("it: jupyter");
        });
    },
};

/** A visitor typing a scope that needs an account is offered a login or an account. */
export const OffersLoginForScope: Story = {
    ...AnonymousVisitor,
    play: async (context) => {
        await openAndType(context, "w:rna");
        await context.step("See a login and registration offered in place of a badge", async () => {
            const prompt = await context.canvas.findByRole("group", { name: "Log in required" }, { timeout: 3000 });
            const options = within(prompt).getAllByRole("option");
            await expect(options).toHaveLength(2);
            await expect(options[0]).toHaveAccessibleName("Log in to search my workflows");
            await expect(options[1]).toHaveAccessibleName("Create a Galaxy account");
            await expect(badge(context)).not.toBeInTheDocument();
        });
    },
};

/** A visitor's token for a scope this Galaxy doesn't offer at all gets no login offer. */
export const IgnoresUnofferedScope: Story = {
    ...AnonymousVisitor,
    play: async (context) => {
        const input = await openAndType(context, "it:jupyter");
        await context.step("See it searched as plain text, with no login offered", async () => {
            await context.canvas.findByRole("tablist", { name: "Result categories" }, { timeout: 3000 });
            await expect(context.canvas.queryByRole("group", { name: "Log in required" })).not.toBeInTheDocument();
            await expect(input).toHaveValue("it:jupyter");
        });
    },
};

/** Where this Galaxy creates no local accounts, a visitor is only offered a login. */
export const OffersLoginWithoutRegistration: Story = {
    parameters: {
        ...viewedBy(getFakeAnonymousUser()),
        msw: { handlers: { configuration: configurationHandler({ allow_local_account_creation: false }) } },
    },
    play: async (context) => {
        await openAndType(context, "h:");
        await context.step("See only a login offered", async () => {
            const prompt = await context.canvas.findByRole("group", { name: "Log in required" }, { timeout: 3000 });
            const options = within(prompt).getAllByRole("option");
            await expect(options).toHaveLength(1);
            await expect(options[0]).toHaveAccessibleName("Log in to search my histories");
        });
    },
};

/** The help lists a visitor's scopes, then the ones an account adds; picking one offers a login. */
export const OffersLoginFromHelp: Story = {
    ...AnonymousVisitor,
    play: async (context) => {
        const input = await openAndType(context, "?");
        await context.step("See public workflows searchable", async () => {
            await seeSections(context, ["Scopes", "Actions", "Keys"]);
            await expect(context.canvas.getByRole("option", { name: "Search public workflows (wp:)" })).toBeVisible();
        });
        await context.step("Click Search my workflows; see its token typed and a login offered", async () => {
            await context.userEvent.click(context.canvas.getByRole("option", { name: "Search my workflows (w:)" }));
            await waitFor(() => expect(input).toHaveValue("w: "));
            await expect(badge(context)).not.toBeInTheDocument();
            const prompt = await context.canvas.findByRole("group", { name: "Log in required" }, { timeout: 3000 });
            await expect(within(prompt).getAllByRole("option")[0]).toHaveAccessibleName(
                "Log in to search my workflows",
            );
            await seeOpen(context);
        });
    },
};
