import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeHistorySummary } from "@tests/test-data";
import { withLoadedConfig } from "@tests/test-data/config";
import { withCurrentHistory } from "@tests/test-data/currentHistory";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { getFakeToolFormConfig } from "@tests/test-data/tools";
import { deferred } from "@tests/vitest/deferred";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";
import { h, onBeforeUnmount } from "vue";

import { configurationHandler, http } from "@/api/client/__mocks__/http";

import ToolForm from "./ToolForm.vue";

// Shipped in test/functional/tools/column_assertion_delimiter.xml: no inputs, two outputs.
const NO_INPUTS = getFakeToolFormConfig({
    id: "column_assertion_delimiter",
    name: "column_assertion_delimiter",
    version: "0.1.0",
    description: "column assertions split on the dataset's delimiter metadata",
    history_id: "fakeHistory",
});
// Shipped in test/functional/tools/async_posix_regex_validator.xml.
const REGEX_INPUT = getFakeToolFormConfig({
    id: "async_posix_regex_validator",
    name: "async_posix_regex_validator",
    version: "1.0.0",
    description:
        "async regression: POSIX character-class regex validators are skipped by pydantic and deferred to statically_validate",
    history_id: "fakeHistory",
    inputs: [{ name: "cell1", label: "cell1", type: "text", value: "cell 1", optional: false }],
    state_inputs: { cell1: "cell 1" },
});
// Shipped in test/functional/tools/markdown_report_simple.xml: a single optional title.
const TEXT_INPUT = getFakeToolFormConfig({
    id: "markdown_report_simple",
    name: "markdown_report_simple",
    version: "1.0",
    history_id: "fakeHistory",
    inputs: [{ name: "title", label: "Title", type: "text", value: null, optional: true }],
    state_inputs: { title: null },
});

const PAGE_LOAD = { timeout: 5000 };

function toolFormState(state: { toolFormPendingBuild: boolean }) {
    return state;
}

// Each mounted loading story owns its pending build; teardown releases the HTTP response.
let pendingBuild: { response: ReturnType<typeof deferred<void>>; started: boolean } | undefined;

const meta = {
    title: "Tool/ToolForm",
    component: ToolForm,
    decorators: [withLoadedConfig, withCurrentUser(), withCurrentHistory(getFakeHistorySummary({ id: "fakeHistory" }))],
    args: { id: NO_INPUTS.id, version: NO_INPUTS.version },
    // Runs before the preview's request guard: config may otherwise render ToolForm after its handlers change.
    afterEach: async ({ canvasElement, args, parameters }) => {
        // Config can delay the decorator. Capture its owner once it mounts, then keep that identity.
        let build: typeof pendingBuild;
        await waitFor(() => {
            if (parameters.toolFormPendingBuild === true) {
                build ??= pendingBuild;
                expect(build?.started).toBe(true);
                expect(within(canvasElement).getByText("Loading Tool...")).toBeVisible();
            } else {
                const runButton = canvasElement.querySelector("[data-description='run tool button']");
                expect(runButton).toBeVisible();
                expect(within(canvasElement).getByRole("heading", { name: args.id })).toBeVisible();
                expect(canvasElement.querySelector("[data-description='galaxy tool version']")).toHaveAttribute(
                    "data-version",
                    args.version,
                );
            }
        }, PAGE_LOAD);
    },
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({
                    enable_tool_source_display: false,
                    object_store_allows_id_selection: false,
                }),
                webhooks: http.untyped.get("/api/webhooks", () => HttpResponse.json([])),
                submission: http.untyped.post("/api/tools", async ({ request }) => {
                    const payload = (await request.json()) as { tool_id?: string };
                    if ([NO_INPUTS.id, TEXT_INPUT.id, REGEX_INPUT.id].includes(payload.tool_id ?? "")) {
                        return HttpResponse.error();
                    }
                }),
                citations: http.untyped.get("/api/tools/:toolId/citations", () => HttpResponse.json([])),
                build: http.untyped.get("/api/tools/column_assertion_delimiter/build", () =>
                    HttpResponse.json(NO_INPUTS),
                ),
            },
        },
    },
} satisfies Meta<typeof ToolForm>;
export default meta;
type Story = StoryObj<typeof meta>;
/** A shipped tool with no parameters; submitting it encounters a network failure. */
export const NoInputParameters: Story = {};
/** The history is already loaded while Galaxy is still building the tool form. */
export const LoadingBuild: Story = {
    decorators: [
        (story) => ({
            setup() {
                const build = { response: deferred<void>(), started: false };
                pendingBuild = build;
                onBeforeUnmount(() => {
                    build.response.resolve();
                    if (pendingBuild === build) {
                        pendingBuild = undefined;
                    }
                });
                return () => h(story());
            },
        }),
    ],
    parameters: {
        ...toolFormState({ toolFormPendingBuild: true }),
        msw: {
            handlers: {
                build: http.untyped.get("/api/tools/column_assertion_delimiter/build", async () => {
                    // Capture this mount's promise so a remount cannot redirect an existing request.
                    const build = pendingBuild;
                    if (build) {
                        build.started = true;
                        await build.response.promise;
                    }
                    return HttpResponse.json(NO_INPUTS);
                }),
            },
        },
    },
};
/** The shipped Markdown report tool with its optional title. */
export const TextParameter: Story = {
    args: { id: TEXT_INPUT.id, version: TEXT_INPUT.version },
    parameters: {
        msw: {
            handlers: {
                build: http.untyped.get("/api/tools/markdown_report_simple/build", () => HttpResponse.json(TEXT_INPUT)),
            },
        },
    },
};
/** Its default contains a space: Galaxy's regex validator reports the wrapper's message. */
export const BackendValidationError: Story = {
    args: { id: REGEX_INPUT.id, version: REGEX_INPUT.version },
    parameters: {
        msw: {
            handlers: {
                build: http.untyped.get("/api/tools/async_posix_regex_validator/build", () =>
                    HttpResponse.json({ ...REGEX_INPUT, errors: { cell1: "letters, numbers, or punctuation" } }),
                ),
            },
        },
    },
};
