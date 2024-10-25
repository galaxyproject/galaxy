import { createViewer } from "vizarr/dist/index";

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = async function (options) {
    const targetElement = document.getElementById(options.target);

    const viewer = await createViewer(targetElement);

    const dataset = options.dataset;

    const url = dataset.metadata_remote_uri
        ? dataset.metadata_remote_uri
        : window.location.origin +
          prefixedDownloadUrl(options.root, `datasets/${dataset.id}/display/${dataset.metadata_store_root}`);

    const config = {
        source: url,
        name: dataset.name,
    };
    viewer.addImage(config);

    options.chart.state("ok", "Done.");
    options.process.resolve();
};
