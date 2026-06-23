// Type declarations for Vite-specific imports

// Monaco editor workers with ?worker suffix
declare module "monaco-editor/esm/vs/editor/editor.worker?worker" {
    const workerConstructor: new () => Worker;
    export default workerConstructor;
}

declare module "monaco-editor/esm/vs/language/json/json.worker?worker" {
    const workerConstructor: new () => Worker;
    export default workerConstructor;
}

declare module "monaco-editor/esm/vs/language/typescript/ts.worker?worker" {
    const workerConstructor: new () => Worker;
    export default workerConstructor;
}

declare module "monaco-yaml/yaml.worker?worker" {
    const workerConstructor: new () => Worker;
    export default workerConstructor;
}
