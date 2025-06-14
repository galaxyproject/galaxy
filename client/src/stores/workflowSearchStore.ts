import { ref } from "vue";

import { type Rectangle, Transform } from "@/components/Workflow/Editor/modules/geometry";
import { defineScopedStore } from "@/stores/scopedStore";
import { useUndoRedoStore } from "@/stores/undoRedoStore";
import {
    type FrameWorkflowComment,
    type TextWorkflowComment,
    useWorkflowCommentStore,
} from "@/stores/workflowEditorCommentStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import {
    type CollectionOutput,
    type DataOutput,
    type NewStep,
    type ParameterOutput,
    useWorkflowStepStore,
} from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

export type SearchData =
    | {
          type: "step";
          id: string;
          prettyName: string;
          stepType: NewStep["type"];
          bounds: Rectangle;
          toolId?: string;
          name: string;
          label: string;
          annotation: string;
      }
    | {
          type: "input";
          id: string;
          prettyName: string;
          bounds: Rectangle;
          label: string;
          inputType: string;
      }
    | {
          type: "output";
          id: string;
          prettyName: string;
          bounds: Rectangle;
          name: string;
          label?: string;
          outputType?: string;
      }
    | {
          type: "comment";
          id: string;
          prettyName: string;
          commentType: "frame" | "markdown" | "text";
          bounds: Rectangle;
          text: string;
      };

export type SearchResult = {
    matchedKeys: string[];
    searchData: SearchData;
    score: number;
    weightedScore: number;
};

export const useWorkflowSearchStore = defineScopedStore("WorkflowSearchStore", (workflowId) => {
    const stateStore = useWorkflowStateStore(workflowId);
    const stepStore = useWorkflowStepStore(workflowId);
    const commentStore = useWorkflowCommentStore(workflowId);
    const undoRedoStore = useUndoRedoStore(workflowId);

    const searchDataCacheId = ref(0);
    const searchDataCacheData = ref<SearchData[] | null>(null);

    function $reset() {
        searchDataCacheId.value = 0;
        searchDataCacheData.value = null;
    }

    /** transform to transform screen coordinates to workflow coordinates */
    function getInverseCanvasTransform() {
        const canvasContainer = document.getElementById("canvas-container");
        assertDefined(canvasContainer);
        const containerBounds = canvasContainer.getBoundingClientRect();

        return new Transform()
            .translate([stateStore.position[0], stateStore.position[1]])
            .translate([containerBounds.x, containerBounds.y])
            .scale([stateStore.scale, stateStore.scale])
            .inverse();
    }

    /** uses a selector function to find the position and size of an element in the workflow */
    function getRect(selectorFunction: () => Element | null | undefined, inverseTransform: Transform): Rectangle {
        const element = selectorFunction();
        assertDefined(element);

        const rect = element.getBoundingClientRect();
        const position = inverseTransform.apply([rect.x, rect.y] as const);

        return {
            x: position[0],
            y: position[1],
            width: rect.width * inverseTransform.scaleX,
            height: rect.height * inverseTransform.scaleY,
        };
    }

    /** collect all workflow info into searchable data */
    function collectSearchData() {
        const inverseTransform = getInverseCanvasTransform();

        const stepSearchData: SearchData[] = Object.entries(stepStore.steps).flatMap(([_id, step]) => {
            const domId = `wf-node-step-${step.id}`;
            const bounds = getRect(() => document.getElementById(domId), inverseTransform);

            const inputs: SearchData[] = step.inputs.map((input) => {
                const domId = `node-${step.id}-input-${input.name}`;
                const bounds = getRect(() => document.getElementById(domId)?.parentElement, inverseTransform);

                return {
                    type: "input",
                    id: domId,
                    prettyName: `Input "${input.label ?? input.name}" for step ${step.id + 1}`,
                    bounds,
                    label: input.label,
                    inputType: input.input_type,
                };
            });

            const outputs: SearchData[] = step.outputs.map((output) => {
                const domId = `node-${step.id}-output-${output.name}`;
                const bounds = getRect(() => document.getElementById(domId)?.parentElement, inverseTransform);

                const workflowOutput = step.workflow_outputs?.find((o) => o.output_name === output.name);

                return {
                    type: "output",
                    id: domId,
                    prettyName: `Output "${workflowOutput?.label ?? output.name}" for step ${step.id + 1}`,
                    bounds,
                    name: output.name,
                    label: workflowOutput?.label ?? undefined,
                    outputType:
                        (output as DataOutput | ParameterOutput).type ?? (output as CollectionOutput).collection_type,
                };
            });

            return [
                {
                    type: "step",
                    id: domId,
                    prettyName: `${step.id + 1}: ${step.label ?? step.name}`,
                    stepType: step.type,
                    bounds,
                    name: step.name,
                    label: step.label ?? "",
                    annotation: step.annotation ?? "",
                },
                ...inputs,
                ...outputs,
            ];
        });

        const commentSearchData: SearchData[] = commentStore.comments.flatMap((comment) => {
            if (comment.type === "freehand") {
                return [];
            }

            const domId = `workflow-comment-${comment.id}`;
            const bounds = getRect(() => document.getElementById(domId), inverseTransform);

            return [
                {
                    type: "comment",
                    id: domId,
                    prettyName: `${comment.type} Comment ${comment.id + 1}`,
                    commentType: comment.type,
                    bounds,
                    text: (comment as TextWorkflowComment).data.text ?? (comment as FrameWorkflowComment).data.title,
                },
            ];
        });

        return [...stepSearchData, ...commentSearchData];
    }

    /** caches the results of `collectSearchData` depending on the changeId of the `undoRedoStore` */
    function collectSearchDataCached() {
        if (undoRedoStore.changeId === searchDataCacheId.value && searchDataCacheData) {
            return searchDataCacheData.value as SearchData[];
        }

        searchDataCacheData.value = collectSearchData();
        searchDataCacheId.value = undoRedoStore.changeId;

        return searchDataCacheData.value as SearchData[];
    }

    const softMatchKeys = ["name", "label", "annotation", "text"];
    const ignoreKeys = ["bounds", "id"];
    const scoreWeights = {
        toolId: 10,
        name: 2,
        type: 5,
    } as Record<string, number>;

    function searchWorkflow(query: string) {
        const data = collectSearchDataCached();

        const queryParts = query
            .toLowerCase()
            .split(" ")
            .filter((v) => v.trim() !== "");

        const results: SearchResult[] = data.map((data) => {
            const matchedKeys = new Set<string>();
            let score = 0;
            let weightedScore = 0;

            Object.entries(data).forEach(([key, value]) => {
                if (ignoreKeys.includes(key) || !value) {
                    // skip
                } else if (softMatchKeys.includes(key)) {
                    const lowerCaseValue = (value as string).toLowerCase();

                    queryParts.forEach((part) => {
                        if (lowerCaseValue.includes(part)) {
                            matchedKeys.add(key);
                            score += 1;
                            weightedScore += scoreWeights[key] ?? lowerCaseValue.split(part).length - 1;
                        }
                    });
                } else {
                    const lowerCaseValue = (value as string).toLowerCase();

                    queryParts.forEach((part) => {
                        if (lowerCaseValue === part) {
                            matchedKeys.add(key);
                            score += 1;
                            weightedScore += scoreWeights[key] ?? 1;
                        }
                    });
                }
            });

            return {
                matchedKeys: Array.from(matchedKeys),
                score,
                weightedScore,
                searchData: data,
            };
        });

        const filteredResults = results.filter((r) => r.score >= queryParts.length && r.score > 0);
        filteredResults.sort((a, b) => b.weightedScore - a.weightedScore);

        return filteredResults;
    }

    return {
        $reset,
        searchWorkflow,
        searchDataCacheId,
        searchDataCacheData,
    };
});
