import type { DatatypeConverter } from "@/api/datatypes";
import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import type { Tool, ToolDataInput } from "@/stores/toolStore";

/** How a dataset fits a tool input: its own datatype, a converted one, or an input that accepts any datatype. */
export type InteractiveToolMatch = "direct" | "converted" | "generic";

export interface InteractiveToolForDataset {
    tool: Tool;
    /** Form path to prefill with the dataset, or null when the form cannot prefill the matching input. */
    inputName: string | null;
    match: InteractiveToolMatch;
}

const MATCH_RANK: Record<InteractiveToolMatch, number> = { direct: 0, converted: 1, generic: 2 };

/** Extensions a dataset can be converted to, including converters registered on its parent datatypes. */
function conversionTargets(extension: string, mapper: DatatypesMapperModel, converters: DatatypeConverter[]) {
    return converters
        .filter((converter) => converter.target !== extension && mapper.isSubType(extension, converter.source))
        .map((converter) => converter.target);
}

function matchInput(
    input: ToolDataInput,
    extension: string,
    mapper: DatatypesMapperModel,
    targets: string[],
): InteractiveToolMatch | null {
    if (input.extensions.includes("data")) {
        return "generic";
    }
    if (mapper.isSubTypeOfAny(extension, input.extensions)) {
        return "direct";
    }
    if (targets.some((target) => mapper.isSubTypeOfAny(target, input.extensions))) {
        return "converted";
    }
    return null;
}

function compareCandidates(a: InteractiveToolForDataset, b: InteractiveToolForDataset) {
    return MATCH_RANK[a.match] - MATCH_RANK[b.match] || Number(a.inputName === null) - Number(b.inputName === null);
}

/**
 * Interactive tools with a dataset input that accepts a dataset of `extension`, best match first, then by name.
 * Each tool is matched through its best input; on a tie the input the form can prefill wins. Collection inputs
 * are skipped.
 */
export function matchInteractiveTools(
    tools: Tool[],
    extension: string,
    mapper: DatatypesMapperModel,
    converters: DatatypeConverter[],
): InteractiveToolForDataset[] {
    const targets = conversionTargets(extension, mapper, converters);
    const results: InteractiveToolForDataset[] = [];
    for (const tool of tools) {
        const candidates: InteractiveToolForDataset[] = [];
        for (const input of tool.data_inputs ?? []) {
            if (input.type !== "data") {
                continue;
            }
            const match = matchInput(input, extension, mapper, targets);
            if (match) {
                candidates.push({ tool, inputName: input.name, match });
            }
        }
        const best = candidates.sort(compareCandidates)[0];
        if (best) {
            results.push(best);
        }
    }
    return results.sort((a, b) => MATCH_RANK[a.match] - MATCH_RANK[b.match] || a.tool.name.localeCompare(b.tool.name));
}
