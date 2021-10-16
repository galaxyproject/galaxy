/** This class enables users to export/download a chart as PNG, SVG or PDF. */

import domtoimage from "dom-to-image";
import { saveAs } from "file-saver";
import { jsPDF } from "jspdf";

export function createPNG(options) {
    domtoimage.toBlob(options.$el[0], { bgcolor: "#fff" }).then(function (blob) {
        saveAs(blob, `${options.title || "my-chart"}.png`);
    });
}

/** SVG export */
export function createSVG(options) {
    domtoimage.toSvg(options.$el[0]).then(function (dataUrl) {
        saveAs(dataUrl, `${options.title || "my-chart"}.svg`);
    });
}

/** PDF export */
export function createPDF(options) {
    domtoimage.toPng(options.$el[0]).then(function (dataUrl) {
        const doc = new jsPDF();
        const w = doc.internal.pageSize.getWidth();
        const h = doc.internal.pageSize.getHeight();
        doc.addImage(dataUrl, "png", w * 0.1, h * 0.1, w * 0.8, h * 0.8);
        doc.save(`${options.title || "my-chart"}.pdf`);
    });
}
