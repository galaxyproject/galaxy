// import deepAssign from "deep-assign";
import { serverPath } from "utils/serverPath";

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
