import $ from "jquery";
import _ from "underscore";

import { Map, View, Graticule } from "ol";
import { OSM, Vector } from "ol/source";
import { GeoJSON } from "ol/format";
import * as interaction from "ol/interaction";
import * as style from "ol/style";
import * as layer from "ol/layer";
import * as control from "ol/control";
import { saveAs } from "file-saver";

import shp from "shpjs";
import axios from "axios";

var MapViewer = (function(mv) {
    mv.gMap = null;

    /** Set the style properties of shapes */
    mv.setStyle = selectedColor => {
        const styles = {
            Polygon: new style.Style({
                stroke: new style.Stroke({
                    color: selectedColor,
                    width: 1
                }),
                fill: new style.Fill({
                    color: "rgba(0, 0, 255, 0.1)"
                })
            }),
            Circle: new style.Style({
                stroke: new style.Stroke({
                    color: selectedColor,
                    width: 1
                }),
                fill: new style.Fill({
                    color: "rgba(0, 0, 255, 0.1)"
                })
            }),
            Point: new style.Style({
                image: new style.Circle({
                    radius: 5,
                    fill: new style.Fill({
                        color: "rgba(0, 0, 255, 0.1)"
                    }),
                    stroke: new style.Stroke({ color: selectedColor, width: 1 })
                })
            }),
            LineString: new style.Style({
                stroke: new style.Stroke({
                    color: selectedColor,
                    width: 1
                })
            }),
            MultiLineString: new style.Style({
                stroke: new style.Stroke({
                    color: selectedColor,
                    width: 1
                })
            }),
            MultiPoint: new style.Style({
                image: new style.Circle({
                    radius: 5,
                    fill: new style.Fill({
                        color: "rgba(0, 0, 255, 0.1)"
                    }),
                    stroke: new style.Stroke({ color: selectedColor, width: 1 })
                })
            }),
            MultiPolygon: new style.Style({
                stroke: new style.Stroke({
                    color: selectedColor,
                    width: 1
                }),
                fill: new style.Fill({
                    color: "rgba(0, 0, 255, 0.1)"
                })
            }),
            GeometryCollection: new style.Style({
                stroke: new style.Stroke({
                    color: selectedColor,
                    width: 1
                }),
                fill: new style.Fill({
                    color: selectedColor
                }),
                image: new style.Circle({
                    radius: 10,
                    fill: null,
                    stroke: new style.Stroke({
                        color: selectedColor
                    })
                })
            })
        };
        return styles;
    };

    /** Set up events and methods for interactions with map view*/
    mv.setInteractions = (source, options) => {
        const geometryType = options.chart.settings.get("geometry_type");
        const geometryColor = options.chart.settings.get("geometry_color");
        let drawInteraction;

        const addInteraction = () => {
            if (geometryType !== "None") {
                drawInteraction = new interaction.Draw({
                    source: source,
                    type: geometryType,
                    freehand: true
                });
                drawInteraction.on("drawstart", event => {
                    const sty = new style.Style({
                        stroke: new style.Stroke({
                            color: geometryColor,
                            width: 2
                        }),
                        fill: new style.Fill({
                            color: "rgba(0, 0, 255, 0.1)"
                        })
                    });
                    event.feature.setStyle(sty);
                });
                mv.gMap.addInteraction(drawInteraction);
            }
        };
        addInteraction();
    };

    /** Export the map view to PNG image*/
    mv.exportMap = () => {
        mv.gMap.once("rendercomplete", event => {
            const canvas = event.context.canvas;
            let fileName = Math.random()
                .toString(11)
                .replace("0.", "");
            fileName += ".png";
            if (navigator.msSaveBlob) {
                navigator.msSaveBlob(canvas.msToBlob(), fileName);
            } else {
                canvas.toBlob(blob => {
                    saveAs(blob, fileName);
                });
            }
        });
        mv.gMap.renderSync();
    };

    /** Create the map view */
    mv.setMap = (vSource, target, options, styleFunction) => {
        const tile = new layer.Tile({ source: new OSM() });
        // add fullscreen handle
        const fullScreen = new control.FullScreen();
        // add scale to the map
        const scaleLineControl = new control.ScaleLine();
        // create vector with styles
        const vectorLayer = new layer.Vector({
            source: vSource,
            style: styleFunction
        });

        const view = new View({
            center: [0, 0],
            zoom: 2
        });

        // create map view
        mv.gMap = new Map({
            controls: control.defaults().extend([scaleLineControl, fullScreen]),
            interactions: interaction.defaults().extend([new interaction.DragRotateAndZoom()]),
            layers: [tile, vectorLayer],
            target: target,
            loadTilesWhileInteracting: true,
            view: view
        });

        // add grid lines
        const graticule = new Graticule({
            strokeStyle: new style.Stroke({
                color: "rgba(255, 120, 0, 0.9)",
                width: 2,
                lineDash: [0.5, 4]
            }),
            showLabels: true
        });

        mv.gMap.addInteraction(new interaction.Modify({ source: vSource }));
        mv.gMap.addControl(new control.ZoomSlider());
        graticule.setMap(mv.gMap);
        mv.setInteractions(vSource, options);
    };

    /** Load the map GeoJson and Shapefiles*/
    mv.loadFile = (filePath, fileType, options, chart) => {
        const target = options.target;
        const formatType = new GeoJSON();
        const toExport = options.chart.settings.get("export_map");
        const geometryColor = options.chart.settings.get("geometry_color");
        const selectedStyles = mv.setStyle(geometryColor);
        const styleFunction = feature => {
            return selectedStyles[feature.getGeometry().getType()];
        };

        if (toExport === "export") {
            mv.exportMap();
        }

        if (fileType === "geojson") {
            const sourceVec = new Vector({ format: formatType, url: filePath, wrapX: false });
            mv.createMap(filePath, sourceVec, options, chart, styleFunction, target);
        } else if (fileType === "shp") {
            axios.get(filePath, { responseType: "arraybuffer" }).then(shpfile => {
                console.debug(shpfile);
                shp(shpfile.data).then(
                    geojson => {
                        const url = window.URL.createObjectURL(
                            new Blob([JSON.stringify(geojson)], { type: "application/json" })
                        );
                        const sourceVec = new Vector({ format: formatType, url: url, wrapX: false });
                        mv.createMap(url, sourceVec, options, chart, styleFunction, target);
                    },
                    failure => {
                        console.debug("FAILURE!", failure);
                    }
                );
            });
        }
    };

    mv.createMap = (filePath, sourceVec, options, chart, styleFunction, target) => {
        mv.setMap(sourceVec, target, options, styleFunction);
        chart.state("ok", "Chart drawn.");
        options.process.resolve();
    };

    return mv;
})(MapViewer || {});

window.bundleEntries = window.bundleEntries || {};
window.bundleEntries.load = function (options) {
    const chart = options.chart;
    const dataset = options.dataset;
    $.ajax({
        url: dataset.download_url,
        success: () => {
            MapViewer.loadFile(dataset.download_url, dataset.extension, options, chart);
        },
        error: () => {
            chart.state("failed", "Failed to access dataset.");
            options.process.resolve();
        }
    });
}
