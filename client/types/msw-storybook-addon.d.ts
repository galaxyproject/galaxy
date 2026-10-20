// Only reachable through package.json "exports", which resolvePackageJsonExports:
// false in tsconfig.json turns off. Not a tsconfig "paths" entry: vite resolves
// those too (resolve.tsconfigPaths) and would load the declaration file.
declare module "msw-storybook-addon/csf3" {
    export * from "msw-storybook-addon/build/csf3.mjs";
}
