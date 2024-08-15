import fs from "fs";
import YAML from "yaml";

const inputFilePath = "src/utils/navigation/navigation.yml";
const file = fs.readFileSync(inputFilePath, "utf8");
const rootComponent = YAML.parse(file);

function generateName(prefix, componentName) {
    return `${prefix}${componentName}`;
}

let tsFile =
    'import type { Component, SelectorTemplate } from "./index";\nimport { ROOT_COMPONENT as raw_root_component } from "./index";\n';

function writeComponentInterface(prefix, componentName, definition) {
    const interfaceName = generateName(prefix, componentName);
    let tsInterface = "";
    if (typeof definition != "string") {
        for (const [key, value] of Object.entries(definition)) {
            if (key == "selectors") {
                for (const [selectorName] of Object.entries(value)) {
                    tsInterface += `${selectorName}: SelectorTemplate;\n`;
                }
            } else if (key == "labels" || key == "text") {
                // not implemented in ES client yet
            } else {
                const childInterfaceName = writeComponentInterface(interfaceName, key, value);
                tsInterface += `${key}: ${childInterfaceName};\n`;
            }
        }
    }
    const empty = tsInterface == "";
    let schemaDefinition = "";
    if (!empty) {
        schemaDefinition += `interface ${interfaceName} extends Component {\n`;
        schemaDefinition += tsInterface;
        schemaDefinition += `}\n`;
    } else {
        schemaDefinition += `type ${interfaceName} = Component;\n`;
    }
    tsFile += schemaDefinition;
    return interfaceName;
}

let tsInterface = "export interface root_component {\n";
for (const [key, value] of Object.entries(rootComponent)) {
    const interfaceName = writeComponentInterface("Root", key, value);
    tsInterface += `${key}: ${interfaceName};\n`;
}
tsInterface += "}\n";
tsFile += tsInterface;
tsFile += "export const ROOT_COMPONENT = raw_root_component as unknown as root_component;";
const outputFilePath = "src/utils/navigation/schema.ts";
fs.writeFileSync(outputFilePath, tsFile);
