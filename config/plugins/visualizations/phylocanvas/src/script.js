import * as phylocanvas from "@phylocanvas/phylocanvas.gl";

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}
window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    const chart = options.chart;
    const dataset = options.dataset;
    const settings = options.chart.settings;
    fetch(prefixedDownloadUrl(options.root, dataset.download_url)).then((response) => {
        if (response.ok) {
            response.text().then((content) => {
                const container = document.getElementById(options.target);
                const tree = new phylocanvas.PhylocanvasGL(
                    container,
                    {
                        source: content,
                        showLabels: settings.get("show_labels") === "true" ? true : false,
                        showLeafLabels: settings.get("show_labels") === "true" ? true : false,
                        interactive: true,
                        nodeShape: settings.get("node_shape"),
                        type: settings.get("tree_type"),
                        alignLabels: settings.get("align_labels") === "true" ? true : false,
                        strokeColour: settings.get("edge_color"),
                        highlightColour: settings.get("highlighted_color"),
                        fillColour: settings.get("node_color"),
                        showInternalNodeLabels: settings.get("show_bootstrap") === "true" ? true : false,
                    },
                    [phylocanvas.plugins.scalebar]
                );

                tree.resize(container.parentElement.clientWidth, container.parentElement.clientHeight);
                chart.state("ok", "Done.");
                options.process.resolve();
                // resize tree on window resize
                window.addEventListener("resize", () => {
                    tree.resize(container.parentElement.clientWidth, container.parentElement.clientHeight);
                });
            });
        } else {
            chart.state("failed", "Failed to access dataset.");
            options.process.resolve();
        }
    });
};
