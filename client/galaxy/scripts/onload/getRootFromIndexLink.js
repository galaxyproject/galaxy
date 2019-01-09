// Finds <link rel="index"> in head element and pulls root url fragment from
// there That should probably be a <base> tag instead since that's how
// they're using <link rel="index" />

import { serverPath } from "utils/serverPath";

export function getRootFromIndexLink(defaultRoot = "/") {
    let links = document.getElementsByTagName("link");
    let indexLink = Array.from(links).find(link => link.rel == "index");
    return indexLink && indexLink.href ? serverPath(indexLink.href) : defaultRoot;
}
