import * as phylocanvas from "@phylocanvas/phylocanvas.gl";

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}

_.extend(window.bundleEntries || {}, {
    load: function (options) {
        const chart = options.chart;
        const dataset = options.dataset;
        const settings = options.chart.settings;
        $.ajax({
            url: prefixedDownloadUrl(options.root, dataset.download_url),
            success: function (content) {
                try {
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

                    // on click of element
                    container.addEventListener("click", function (e) {
                        console.debug("clicked", e);
                        const node = tree.collapseNode(tree.selectedNode);
                        console.debug(node);
                    });
                    console.debug(tree);
                    chart.state("ok", "Done.");
                    options.process.resolve();
                } catch (err) {
                    chart.state("failed", err);
                }
            },
            error: function () {
                chart.state("failed", "Failed to access dataset.");
                options.process.resolve();
            },
        });
    },
});
