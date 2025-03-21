import { faFile, faFolder } from "@fortawesome/free-regular-svg-icons";
import { faPencilAlt } from "@fortawesome/free-solid-svg-icons";
import { type IconDefinition } from "font-awesome-6";

export interface WorkflowInput {
    id?: string; // unique ID. defaults to module ID
    moduleId: string;
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
            moduleId: "data_input",
            title: "输入数据集",
            description: "单个数据集输入",
            icon: faFile,
        },
        {
            moduleId: "data_collection_input",
            title: "输入数据集集合",
            description: "数据集集合的输入",
            icon: faFolder,
        },
        {
            moduleId: "parameter_input",
            title: "文本输入",
            description: "用于工作流逻辑的文本参数",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "text",
            },
        },
        {
            id: "parameter_input_integer",
            moduleId: "parameter_input",
            title: "整数输入",
            description: "用于工作流逻辑的整数参数",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "integer",
            },
        },
        {
            id: "parameter_input_float",
            moduleId: "parameter_input",
            title: "浮点数输入",
            description: "用于工作流逻辑的不精确小数参数",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "float",
            },
        },
        {
            id: "parameter_input_boolean",
            moduleId: "parameter_input",
            title: "布尔输入",
            description: "用于工作流逻辑的真/假参数",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "boolean",
            },
        },
        {
            id: "parameter_input_color",
            moduleId: "parameter_input",
            title: "颜色输入",
            description: "用于工作流逻辑的颜色参数",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "color",
            },
        },
        {
            id: "parameter_input_directory_uri",
            moduleId: "parameter_input",
            title: "目录输入",
            description: "用于工作流逻辑的目录参数",
            icon: faPencilAlt,
            stateOverwrites: {
                parameter_type: "directory_uri",
            },
        },
    ];
}
