import { type Rectangle, Transform } from "@/components/Workflow/Editor/modules/geometry";
import { useWorkflowStores } from "@/composables/workflowStores";
import type { FrameWorkflowComment, TextWorkflowComment } from "@/stores/workflowEditorCommentStore";
import type { CollectionOutput, DataOutput, NewStep, ParameterOutput } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

type SearchData =
    | {
          type: "step";
          stepType: NewStep["type"];
          bounds: Rectangle;
          toolId?: string;
          name: string;
          label: string;
          annotation: string;
      }
    | {
          type: "input";
          bounds: Rectangle;
          label: string;
          inputType: string;
      }
    | {
          type: "output";
          bounds: Rectangle;
          name: string;
          label?: string;
          outputType?: string;
      }
    | {
          type: "comment";
          commentType: "frame" | "markdown" | "text";
          bounds: Rectangle;
          text: string;
      };

/** transform to transform screen coordinates to workflow coordinates */
function getInverseCanvasTransform(workflowId: string) {
    const stores = useWorkflowStores(workflowId);

    return new Transform()
        .translate([stores.stateStore.position[0], stores.stateStore.position[1]])
        .scale([stores.stateStore.scale, stores.stateStore.scale])
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
function collectSearchData(workflowId: string) {
    const stores = useWorkflowStores(workflowId);
    const inverseTransform = getInverseCanvasTransform(workflowId);

    const stepSearchData: SearchData[] = Object.entries(stores.stepStore.steps).flatMap(([_id, step]) => {
        const domId = `wf-node-step-${step.id}`;
        const bounds = getRect(() => document.getElementById(domId), inverseTransform);

        const inputs: SearchData[] = step.inputs.map((input) => {
            const domId = `node-${step.id}-input-${input.name}`;
            const bounds = getRect(() => document.getElementById(domId)?.parentElement, inverseTransform);

            return {
                type: "input",
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

    const commentSearchData: SearchData[] = stores.commentStore.comments.flatMap((comment) => {
        if (comment.type === "freehand") {
            return [];
        }

        const domId = `workflow-comment-${comment.id}`;
        const bounds = getRect(() => document.getElementById(domId), inverseTransform);

        return [
            {
                type: "comment",
                commentType: comment.type,
                bounds,
                text: (comment as TextWorkflowComment).data.text ?? (comment as FrameWorkflowComment).data.title,
            },
        ];
    });

    return [...stepSearchData, ...commentSearchData];
}

let searchDataCacheId = 0;
let searchDataCacheData: SearchData[] | null = null;

/** caches the results of `collectSearchData` depending on the changeId of the `undoRedoStore` */
function collectSearchDataCached(workflowId: string) {
    const stores = useWorkflowStores(workflowId);

    if (stores.undoRedoStore.changeId === searchDataCacheId && searchDataCacheData) {
        return searchDataCacheData;
    }

    searchDataCacheData = collectSearchData(workflowId);
    searchDataCacheId = stores.undoRedoStore.changeId;

    return searchDataCacheData;
}

type SearchResult = {
    matchedKeys: string[];
    searchData: SearchData;
    score: number;
};

const softMatchKeys = ["name", "label", "annotation"];
const ignoreKeys = ["bounds"];

export function searchWorkflow(query: string, workflowId: string) {
    const data = collectSearchDataCached(workflowId);

    const queryParts = query
        .toLowerCase()
        .split(" ")
        .filter((v) => v.trim() !== "");

    const results: SearchResult[] = data.map((data) => {
        const matchedKeys = new Set<string>();
        let score = 0;

        Object.entries(data).forEach(([key, value]) => {
            if (ignoreKeys.includes(key)) {
                // skip
            } else if (softMatchKeys.includes(key)) {
                const lowerCaseValue = (value as string).toLowerCase();

                queryParts.forEach((part) => {
                    if (lowerCaseValue.includes(part)) {
                        matchedKeys.add(key);
                        score += 1;
                    }
                });
            } else {
                const lowerCaseValue = (value as string).toLowerCase();

                queryParts.forEach((part) => {
                    if (lowerCaseValue === part) {
                        matchedKeys.add(key);
                        score += 1;
                    }
                });
            }
        });

        return {
            matchedKeys: Array.from(matchedKeys),
            score,
            searchData: data,
        };
    });

    const filteredResults = results.filter((r) => r.score > 0);
    filteredResults.sort((a, b) => a.score - b.score);

    return filteredResults;
}
