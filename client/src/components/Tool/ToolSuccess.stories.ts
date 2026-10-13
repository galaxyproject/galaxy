import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withLoadedConfig } from "@tests/test-data/config";
import { getFakeDatasetDetails } from "@tests/test-data/datasets";
import { getFakeTool } from "@tests/test-data/tools";
import { HttpResponse } from "msw";
import { expect, waitFor, within } from "storybook/test";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import { typesAndMappingHandler } from "@/components/Datatypes/test_fixtures";
import jobInformationResponse from "@/components/JobInformation/testData/jobInformationResponse.json";
import { toolBoxState, withToolBoxState } from "@/components/Panels/test_fixtures";
import { PREDICTIONS, toolPredictions } from "@/components/ToolRecommendation/test_fixtures";

import { CAT_SUBMISSION, QUEUED_CAT_JOB, withToolSubmission } from "./test_fixtures";

import ToolSuccess from "./ToolSuccess.vue";

interface ToolSuccessParameters {
    toolSuccessRecommendations?: boolean;
}

function recommendations(enabled: boolean) {
    return {
        toolSuccessRecommendations: enabled,
        msw: { handlers: { configuration: configurationHandler({ enable_tool_recommendations: enabled }) } },
    };
}

const meta = {
    title: "Tool/ToolSuccess",
    component: ToolSuccess,
    decorators: [withToolBoxState, withLoadedConfig, withToolSubmission()],
    parameters: {
        ...toolBoxState({
            tools: [getFakeTool({ id: "cat1", name: "Concatenate multiple datasets or collections" })],
            toolSections: { default: {} },
        }),
        toolSuccessRecommendations: true,
        msw: {
            handlers: {
                configuration: configurationHandler({ enable_tool_recommendations: true }),
                jobDetails: http.get("/api/jobs/{job_id}", ({ params, response }) =>
                    response(200).json({ ...jobInformationResponse, ...QUEUED_CAT_JOB, id: params.job_id } as never),
                ),
                consoleOutput: http.get("/api/jobs/{job_id}/console_output", ({ response }) =>
                    response(200).json({ stdout: "", stderr: "", state: "new" }),
                ),
                dataset: http.get("/api/datasets/{dataset_id}", ({ params, response }) =>
                    response.untyped(
                        HttpResponse.json(
                            getFakeDatasetDetails({
                                id: params.dataset_id,
                                hid: 3,
                                history_id: QUEUED_CAT_JOB.history_id,
                                name: CAT_SUBMISSION.jobResponse.outputs[0]!.name,
                                state: "new",
                            }),
                        ),
                    ),
                ),
                invocations: http.get("/api/invocations", ({ response }) => response(200).json([])),
                objectStores: http.get("/api/object_stores", ({ response }) => response(200).json([])),
                predictions: toolPredictions(PREDICTIONS),
                datatypes: typesAndMappingHandler,
                webhooks: http.untyped.get("/api/webhooks", () => HttpResponse.json([])),
            },
        },
    },
    afterEach: async ({ canvasElement, parameters }) => {
        await waitFor(() =>
            expect(canvasElement.querySelector(".job-header-title")).toHaveTextContent(
                "Concatenate multiple datasets or collections",
            ),
        );
        expect(canvasElement.querySelector(".job-information-state-badge")).toHaveTextContent("new");
        canvasElement.querySelector("#tool-run-outputs")?.scrollIntoView();
        await waitFor(
            () =>
                expect(
                    within(canvasElement).getByText(
                        "Concatenate multiple datasets or collections on data 1 and data 2",
                    ),
                ).toBeVisible(),
            {
                timeout: 5000,
            },
        );
        const storyParameters = parameters as ToolSuccessParameters;
        if (storyParameters.toolSuccessRecommendations !== false) {
            await waitFor(() => expect(within(canvasElement).getByText("Cut", { exact: true })).toBeVisible(), {
                timeout: 5000,
            });
        } else {
            expect(canvasElement.querySelector("#tool-recommendation")).not.toBeInTheDocument();
        }
    },
} satisfies Meta<typeof ToolSuccess>;
export default meta;
type Story = StoryObj<typeof meta>;

/** Concatenating two inputs queues one job and offers compatible tools to run next. */
export const WithRecommendations: Story = {};

/** An instance with recommendations disabled still shows the queued job and its output. */
export const WithoutRecommendations: Story = { parameters: recommendations(false) };
