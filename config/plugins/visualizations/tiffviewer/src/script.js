import { StrictMode } from "react";

import { TIFFViewer } from "react-tiff";
import { createRoot } from "react-dom/client";
import "react-tiff/dist/index.css";

const App = (props) => {
    return <TIFFViewer tiff={props.dataset_url} paginate="bottom" />;
};

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
    return `${root}/${path}`.replace(slashCleanup, "/");
}

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    const dataset = options.dataset;
    const url = prefixedDownloadUrl(options.root, dataset.download_url);
    const root = createRoot(document.getElementById(options.target));
    root.render(
        <StrictMode>
            <App dataset_url={url} />
        </StrictMode>
    );
    options.chart.state("ok", "Done.");
    options.process.resolve();
};
