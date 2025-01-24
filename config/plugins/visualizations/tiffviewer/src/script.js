import { StrictMode } from "react";

import { TIFFViewer } from "react-tiff";
import { createRoot } from "react-dom/client";
import "react-tiff/dist/index.css";

const App = (props) => {
    return <TIFFViewer tiff={props.dataset_url} paginate="bottom" />;
};

const { root, visualization_config } = JSON.parse(document.getElementById("app").dataset.incoming);

const datasetId = visualization_config.dataset_id;

const url = window.location.origin + root + "api/datasets/" + datasetId + "/display";

const rootElement = createRoot(document.getElementById("app"));
rootElement.render(
    <StrictMode>
        <App dataset_url={url} />
    </StrictMode>
);
