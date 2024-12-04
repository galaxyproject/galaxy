import { faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faPencilAlt } from "@fortawesome/free-solid-svg-icons";
import { type IconDefinition } from "font-awesome-6";

export interface WorkflowInput {
    id: string;
    title: string;
    description: string;
    stateOverwrites?: {
        parameter_type?: "text" | "integer" | "boolean" | "color" | "float" | "directory_uri";
    };
    icon: IconDefinition;
}

export function getWorkflowInputs(): WorkflowInput[] {
    return [
        {
            id: "data_input",
            title: "Input Dataset",
            description: "Single dataset input",
            icon: faFile,
        },
        {
            id: "data_collection_input",
            title: "Input Dataset Collection",
            description: "Input for a collection of datasets",
            icon: faFolder,
        },
        {
            id: "parameter_input",
            title: "Text Input",
            description: "Text parameter used for workflow logic",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "text",
            },
        },
        {
            id: "parameter_input",
            title: "Integer Input",
            description: "Whole number parameter used for workflow logic",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "integer",
            },
        },
        {
            id: "parameter_input",
            title: "Float Input",
            description: "Imprecise decimal number parameter used for workflow logic",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "float",
            },
        },
        {
            id: "parameter_input",
            title: "Boolean Input",
            description: "True / False parameter used for workflow logic",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "boolean",
            },
        },
        {
            id: "parameter_input",
            title: "Color Input",
            description: "Color parameter used for workflow logic",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "color",
            },
        },
        {
            id: "parameter_input",
            title: "Directory Input",
            description: "Directory parameter used for workflow logic",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "directory_uri",
            },
        },
    ];
}
