import { buildQuickStartExample } from "./authoringHelpTypes";

export const NEW_TOOL_YAML = buildQuickStartExample();

export const CLEAR_TOOL_YAML = `class: GalaxyUserTool
name:
version: "0.1.0"
container:
shell_command:
inputs: []
outputs: []`;
