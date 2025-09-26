import {
    faArrowRightFromBracket,
    faArrowRightToBracket,
    faComment,
    faFile,
    faFolderOpen,
    faMessage,
    faObjectGroup,
    faPause,
    faCodeBranch,
    faPen,
    faSitemap,
    faWrench,
} from "font-awesome-6";

import type { SearchData } from "@/stores/workflowSearchStore";

export const iconForType = {
    step: {
        tool: faWrench,
        data_input: faFile,
        data_collection_input: faFolderOpen,
        parameter_input: faPen,
        subworkflow: faSitemap,
        pause: faPause,
        regex_switch: faCodeBranch,
    },
    input: faArrowRightToBracket,
    output: faArrowRightFromBracket,
    comment: {
        frame: faObjectGroup,
        text: faComment,
        markdown: faMessage,
    },
} as const;

export function getIconForSearchData(searchData: SearchData) {
    if (searchData.type === "step") {
        return iconForType.step[searchData.stepType];
    } else if (searchData.type === "comment") {
        return iconForType.comment[searchData.commentType];
    } else {
        return iconForType[searchData.type];
    }
}
