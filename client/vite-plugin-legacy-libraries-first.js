const BOOTSTRAP_VUE_VUE_MODULE = "/bootstrap-vue/esm/vue.js";

/**
 * bootstrap-vue captures Vue.extend when its vue.js module is evaluated, and in
 * the production bundle that module lands in a chunk the entry imports, i.e.
 * before compat-config.js runs. Make it import the legacy marker first, so the
 * hook is in place whatever the chunking. The dev server's prebundled deps and
 * vitest don't go through this; they rely on compat-config.js importing the
 * marker first.
 */
export function legacyLibrariesFirstPlugin() {
    return {
        name: "galaxy-legacy-libraries-first",
        enforce: "pre",
        transform(code, id) {
            if (id.replace(/\\/g, "/").includes(BOOTSTRAP_VUE_VUE_MODULE)) {
                return { code: `import "@/legacy-libraries.js";\n${code}`, map: null };
            }
        },
    };
}
