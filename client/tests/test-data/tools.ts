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
