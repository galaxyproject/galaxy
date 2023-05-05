/**
 * Visualizer interface for h5web (https://github.com/silx-kit/h5web)
 * 
 * This relies on Galaxy being able to serve files using the
 * h5grove protocol (https://silx-kit.github.io/h5grove/). 
 * This provides efficient access to the contents of the
 * HDF5 file and avoids having to read the whole file at any
 * point.
 */

import './styles.css';
import React, { StrictMode } from 'react'
import {render as reactRender} from 'react-dom'
import {App, H5GroveProvider} from '@h5web/app'

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
    var dataset = options.dataset;
    var settings = options.chart.settings;
    var explorer = settings.get('explorer');
    var url = window.location.origin + "/api/datasets/" + dataset.id + "/content";
    reactRender(
      <MyApp 
        url={url} 
        name={dataset.name} 
        filepath={dataset.file_name} 
        explorer={explorer}
      />,
      document.getElementById(options.target)
    )
    options.chart.state('ok', 'Chart drawn.');
    options.process.resolve();
};

export default MyApp;
