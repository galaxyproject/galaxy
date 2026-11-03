import type { ToolFormConfig } from "@/api/tools";
import type { Tool } from "@/stores/toolStore";

export function getFakeTool(overrides: Partial<Tool> = {}): Tool {
    return {
        model_class: "Tool",
        id: "test-tool",
        name: "Test Tool",
        version: "1.0",
        description: "",
        labels: [],
        edam_operations: [],
        edam_topics: [],
        hidden: false,
        is_workflow_compatible: true,
        xrefs: [],
        config_file: "",
        link: "",
        panel_section_id: "",
        panel_section_name: null,
        form_style: "regular",
        ...overrides,
    };
}

/** A tool build response, including the state fields emitted by Tool.to_json. */
export function getFakeToolFormConfig(overrides: Partial<ToolFormConfig> = {}): ToolFormConfig {
    return {
        ...getFakeTool(),
        inputs: [],
        errors: {},
        state_inputs: {},
        warnings: null,
        message: "",
        tool_errors: null,
        credentials: [],
        job_id: null,
        job_remap: null,
        job_credentials_context: null,
        history_id: null,
        action: "/tool_runner/index",
        method: "post",
        enctype: "application/x-www-form-urlencoded",
        ...overrides,
    };
}
