// import deepAssign from "deep-assign";
import { serverPath } from "utils/serverPath";

// const defaultConfigs = {
//     options: {
//         root: getRootFromIndexLink()
//     },
//     bootstrapped: {},
//     form_input_auto_focus: false,
//     sentry: {}
// };

// There is currently no need for this to be a promise
// but I am designing it as if it were in anticipation of
// loading an external config from the server
// export async function loadConfig() {
//     let result = Object.create(defaultConfigs);
//     try {
//         let lookup = await Promise.resolve(window.galaxyConfig);
//         result = deepAssign(result, lookup);
//     } catch (err) {
//         console.warn("Lousy config", err);
//     }
//     return result;
// }

export function getAppRoot(defaultRoot = "/") {
    // try configs
    let root = defaultRoot;
    try {
        root = window.galaxyConfig.options.root;
    } catch (err) {
        // console.warn("galaxyConfig not defined");
        try {
            root = getRootFromIndexLink(defaultRoot);
        } catch (err) {
            console.warn("Unable to find index link in head", err);
        }
    }
    return root;
}

// finds <link> in head element and pulls root url fragment from there
function getRootFromIndexLink(defaultRoot = "/") {
    let links = document.getElementsByTagName("link");
    let indexLink = [...links].find(link => link.rel == "index");
    if (indexLink && indexLink.href) {
        return serverPath(indexLink.href);
    }
    return defaultRoot;
}
