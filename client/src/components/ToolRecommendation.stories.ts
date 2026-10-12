import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { http as transport, HttpResponse } from "msw";
import { expect, userEvent, waitFor, within } from "storybook/test";

import { http } from "@/api/client/__mocks__/http";
import { typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";
import { PREDICTIONS, toolPredictions } from "@/components/ToolRecommendation/test_fixtures";

import ToolRecommendation from "./ToolRecommendation.vue";

const meta = {
    title: "ToolRecommendation",
    component: ToolRecommendation,
    args: { toolId: "cat1" },
    decorators: [withCurrentUser()],
    parameters: {
        msw: {
            handlers: {
                predictions: toolPredictions(PREDICTIONS),
                datatypes: typesAndMappingHandler,
            },
        },
    },
} satisfies Meta<typeof ToolRecommendation>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Galaxy recommends Cut after concatenating datasets; its text input accepts the inherited output type. */
export const CompatibleTools: Story = {};

/** The prediction request fails before the datatype compatibility check can begin. */
export const PredictionNetworkFailure: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Read the prediction request failure", async () => {
            const alert = await canvas.findByRole("alert", {}, { timeout: 5000 });
            await expect(alert).toBeVisible();
            await expect(alert).toHaveTextContent(/^Tool recommendations could not be loaded: Network Error$/);
        });
    },
    parameters: {
        msw: {
            handlers: {
                predictions: transport.post("/api/workflows/get_tool_predictions", () => HttpResponse.error()),
            },
        },
    },
};

/** Predictions arrive, but the datatype registry cannot be loaded to check compatibility. */
export const DatatypesNetworkFailure: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Read the datatype request failure", async () => {
            const alert = await canvas.findByRole("alert", {}, { timeout: 5000 });
            await expect(alert).toBeVisible();
            await expect(alert).toHaveTextContent(/^Tool recommendations could not be loaded: Failed to fetch$/);
        });
    },
    parameters: {
        msw: {
            handlers: {
                datatypes: transport.get("/api/datatypes/types_and_mapping", () => HttpResponse.error()),
            },
        },
    },
};

/** An instance with no configured prediction model returns JSON null and offers no recommendations. */
export const NoPredictionModel: Story = {
    parameters: {
        msw: {
            handlers: {
                predictions: http.untyped.post("/api/workflows/get_tool_predictions", () => HttpResponse.json(null)),
            },
        },
    },
};

/** Collapse the current tool's recommendations, then reopen them for further analysis. */
export const TogglesRecommendations: Story = {
    play: async ({ canvasElement, step }) => {
        const canvas = within(canvasElement);
        await step("Read the recommended tool", async () => {
            await expect(
                await canvas.findByRole("heading", { name: "Tool Recommendation" }, { timeout: 5000 }),
            ).toBeVisible();
            await waitFor(() => expect(canvas.getByText("Cut", { exact: true })).toBeVisible(), { timeout: 5000 });
        });
        await step("Collapse recommendations from the current tool", async () => {
            await userEvent.click(canvas.getByText("Concatenate multiple...", { exact: true }));
            await waitFor(() => expect(canvas.queryByText("Cut", { exact: true })).not.toBeInTheDocument(), {
                timeout: 5000,
            });
            await expect(canvas.getByRole("heading", { name: "Tool Recommendation" })).toBeVisible();
        });
        await step("Reopen the recommended tool", async () => {
            await userEvent.click(canvas.getByText("Concatenate multiple...", { exact: true }));
            await waitFor(() => expect(canvas.getByText("Cut", { exact: true })).toBeVisible(), { timeout: 5000 });
        });
    },
};
