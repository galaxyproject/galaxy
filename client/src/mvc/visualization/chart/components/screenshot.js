/** This class enables users to export/download a chart as PNG, SVG or PDF. */

import $ from "jquery";

import domtoimage from "dom-to-image";
import { saveAs } from "file-saver";

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
    var xml = toXML(options);
    var data = {
        filename: "visualization",
        type: "application/pdf",
        height: xml.height,
        width: xml.width,
        scale: 2,
        svg: xml.string,
    };
    var $el = $("body");
    var form = $el.find("#viewer-form");
    if (form.length === 0) {
        form = $("<form>", {
            id: "viewer-form",
            method: "post",
            action: "http://export.highcharts.com/",
            display: "none",
        });
        $el.append(form);
    }
    form.empty();
    for (var name in data) {
        var input = $("<input/>", {
            type: "hidden",
            name: name,
            value: data[name],
        });
        form.append(input);
    }
    try {
        form.submit();
    } catch (err) {
        console.log(err);
    }
}

/** XML export */
function toXML(options) {
    var $svg = options.$el.find("svg");
    if ($svg.length == 0) {
        if (options.error) {
            options.error("No SVG found. This visualization type does not support SVG/PDF export.");
            return;
        }
    }
    var nsvgs = $svg.length;
    var height = parseInt($svg.first().css("height"));
    var width = parseInt($svg.first().css("width"));
    var serializer = new XMLSerializer();
    var $composite = $("<svg/>").attr({
        version: "1.1",
        xmlns: "http://www.w3.org/2000/svg",
        width: width * nsvgs,
        height: height,
    });
    var offsetX = 0;
    $svg.each(function () {
        var $svg = $(this).clone();
        var $g = $('<g transform="translate(' + offsetX + ', 0)">').attr("xmlns", "http://www.w3.org/2000/svg");
        $g.append($svg.find("g").first());
        $composite.append($g);
        offsetX += width;
    });
    return {
        string: serializer.serializeToString($composite[0]),
        height: height,
        width: width,
    };
}

export default {
    createPNG: createPNG,
    createSVG: createSVG,
    createPDF: createPDF,
};
