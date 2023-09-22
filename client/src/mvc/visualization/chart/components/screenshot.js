/** This class enables users to export/download a chart as PNG, SVG or PDF. */

import domtoimage from "dom-to-image";
import { saveAs } from "file-saver";
import { jsPDF } from "jspdf";

export function createPNG(options) {
    domtoimage.toBlob(options.$el[0], { bgcolor: "#fff" }).then(function (blob) {
        saveAs(blob, `${options.title || "my-chart"}.png`);
    });
}

export function createSVG(options) {
    domtoimage.toSvg(options.$el[0]).then(function (dataUrl) {
        saveAs(dataUrl, `${options.title || "my-chart"}.svg`);
    });
}

export function createPDF(options) {
    domtoimage.toPng(options.$el[0]).then(function (dataUrl) {
        const doc = new jsPDF();
        // Calculate scaled image size.  We want to leave a small margin, but
        // fill the page width otherwise.
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const elementWidth = options.$el.width();
        const elementHeight = options.$el.height();
        const scale = Math.min(pageWidth / elementWidth, pageHeight / elementHeight) * 0.95;

        doc.addImage(
            dataUrl,
            "png",
            pageWidth * 0.025,
            pageHeight * 0.025,
            scale * elementWidth,
            scale * elementHeight
        );

        doc.save(`${options.title || "my-chart"}.pdf`);
    });
}
