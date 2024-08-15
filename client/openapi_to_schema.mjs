// this is a helper script that fixes const values
// upstream fix in https://github.com/drwpow/openapi-typescript/pull/1014
import openapiTS from "openapi-typescript";

const inputFilePath = process.argv[2];

const localPath = new URL(inputFilePath, import.meta.url);
openapiTS(localPath, {
    transform(schemaObject, metadata) {
        if ("const" in schemaObject) {
            const constType = typeof schemaObject.const;
            switch (constType) {
                case "number":
                case "boolean":
                    return `${schemaObject.const}`;
                default:
                    return `"${schemaObject.const}"`;
            }
        }
    },
}).then((output) => console.log(output));
