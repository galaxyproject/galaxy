/**
 * Visualizer interface for h5web (https://github.com/silx-kit/h5web)
 *
 * This relies on Galaxy being able to serve files using the
 * h5grove protocol (https://silx-kit.github.io/h5grove/).
 * This provides efficient access to the contents of the
 * HDF5 file and avoids having to read the whole file at any
 * point.
 */

import "./styles.css";
import React from "react";
import { createRoot } from "react-dom/client";
import { App, H5GroveProvider } from "@h5web/app";

/* This will be part of the charts/viz standard lib in 23.1 */
const slashCleanup = /(\/)+/g;
function prefixedDownloadUrl(root, path) {
  return `${root}/${path}`.replace(slashCleanup, "/");
}

function MyApp(props) {
  return (
    <H5GroveProvider
      url={props.url}
      filepath={props.name}
      axiosConfig={{ params: { file: props.name } }}
    >
      <App explorerOpen={props.explorer} />
    </H5GroveProvider>
  );
}

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
  const dataset = options.dataset;
  const settings = options.chart.settings;
  const explorer = settings.get("explorer");
  const url =
    window.location.origin +
    prefixedDownloadUrl(
      options.root,
      "/api/datasets/" + dataset.id + "/content"
    );
  const root = createRoot(document.getElementById(options.target));
  root.render(
    <MyApp
      url={url}
      name={dataset.name}
      filepath={dataset.file_name}
      explorer={explorer}
    />
  );
  options.chart.state("ok", "Chart drawn.");
  options.process.resolve();
};

export default MyApp;
