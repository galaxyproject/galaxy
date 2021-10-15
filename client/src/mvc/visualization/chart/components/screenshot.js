/** This class enables users to export/download a chart as PNG, SVG or PDF. */

import $ from "jquery";

import domtoimage from "dom-to-image";
import { saveAs } from "file-saver";
import { jsPDF } from "jspdf";

function createPNG(options) {
    domtoimage.toBlob(options.$el[0]).then(function (blob) {
        saveAs(blob, `${options.title || "my-chart"}.png`);
    });
}

/** SVG export */
function createSVG(options) {
    domtoimage.toSvg(options.$el[0]).then(function (dataUrl) {
        saveAs(dataUrl, `${options.title || "my-chart"}.svg`);
    });
}

/** PDF export */
function createPDF(options) {
    domtoimage.toPng(options.$el[0]).then(function (dataUrl) {
        const doc = new jsPDF();
        doc.addImage(dataUrl, "png", 0, 0);
        doc.save(`${options.title || "my-chart"}.pdf`);
    });

}

export default {
    createPNG: createPNG,
    createSVG: createSVG,
    createPDF: createPDF,
};
