import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { withGalaxyInstance } from "@tests/test-data/galaxyInstance";
import type { UseScrollReturn } from "@vueuse/core";
import { zoomIdentity } from "d3-zoom";
import { HttpResponse } from "msw";
import { h, markRaw, provide, ref } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { type Step, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { MISSING_TOOL_CONNECTIONS, MISSING_TOOL_STEP, SUBWORKFLOW_STEP, TOOL_STEP } from "./node_test_fixtures";
import { mockOffset, withWorkflowStores } from "./test_fixtures";

import Node from "./Node.vue";

const WORKFLOW_ID = "quality-control";
interface EditorParameters {
    missingToolConnections?: boolean;
}

function editorParameters(parameters: EditorParameters): EditorParameters {
    return parameters;
}

const withEditorState: Decorator = (story, context) => ({
    setup() {
        provide("transform", ref(zoomIdentity));
        provide("isDragging", ref(false));
        useWorkflowStepStore(WORKFLOW_ID).addStep(context.args.step as Step);
        useConnectionStore(WORKFLOW_ID).$patch({
            stepToConnections: {
                0: (context.parameters as EditorParameters).missingToolConnections ? MISSING_TOOL_CONNECTIONS : [],
            },
        });
        return () => h("div", { style: { position: "relative", minHeight: "180px" } }, [h(story())]);
    },
});

const meta = {
    title: "Workflow/Editor/Node",
    component: Node,
    decorators: [
        withGalaxyInstance({ enable_tool_recommendations: false }),
        withWorkflowStores(WORKFLOW_ID),
        withEditorState,
    ],
    args: {
        id: 0,
        contentId: TOOL_STEP.content_id,
        activeNodeId: null,
        name: "FastQC",
        step: TOOL_STEP,
        datatypesMapper: markRaw(testDatatypesMapper),
        rootOffset: markRaw(mockOffset),
        scroll: markRaw({ x: ref(0), y: ref(0), isScrolling: ref(false) } as UseScrollReturn),
    },
    argTypes: { datatypesMapper: { control: false }, rootOffset: { control: false }, scroll: { control: false } },
} satisfies Meta<typeof Node>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Tool: Story = {};
export const ActiveTool: Story = { args: { activeNodeId: 0 } };
export const Subworkflow: Story = { args: { step: SUBWORKFLOW_STEP, contentId: null, name: "Read quality control" } };

/** A workflow opened on a server where FastQC is no longer installed. */
export const MissingTool: Story = { args: { step: MISSING_TOOL_STEP } };

/** Existing connections survive even though the missing tool's terminals cannot be resolved. */
export const MissingToolWithConnections: Story = {
    args: { step: MISSING_TOOL_STEP },
    parameters: editorParameters({ missingToolConnections: true }),
};

export const WithRecommendations: Story = {
    decorators: [withGalaxyInstance({ enable_tool_recommendations: true })],
    parameters: {
        msw: {
            handlers: {
                recommendations: http.untyped.post("/api/workflows/get_tool_predictions", async ({ request }) => {
                    const body = (await request.json()) as { tool_sequence: string };
                    return HttpResponse.json({
                        current_tool: body.tool_sequence,
                        predicted_data: {
                            o_extensions: ["html", "txt"],
                            children: [],
                            is_deprecated: false,
                            message: "",
                        },
                    });
                }),
            },
        },
    },
};
