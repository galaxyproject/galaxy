import $ from "./jq-loader";
import "jquery-contextmenu";
import "jquery.ui.position";
import _ from "underscore";
// Use lighter weight 'core' version of paper since we don't need paperscript
import paper from "../node_modules/paper/dist/paper-core.js";

const CommandManager = (function () {
    function CommandManager() {}

    CommandManager.executed = [];
    CommandManager.unexecuted = [];

    CommandManager.execute = function execute(cmd) {
        cmd.execute();
        CommandManager.executed.push(cmd);
    };

    CommandManager.undo = function undo() {
        const cmd1 = CommandManager.executed.pop();
        if (cmd1 !== undefined) {
            if (cmd1.unexecute !== undefined) {
                cmd1.unexecute();
            }
            CommandManager.unexecuted.push(cmd1);
        }
    };

    CommandManager.redo = function redo() {
        let cmd2 = CommandManager.unexecuted.pop();

        if (cmd2 === undefined) {
            cmd2 = CommandManager.executed.pop();
            CommandManager.executed.push(cmd2);
            CommandManager.executed.push(cmd2);
        }

        if (cmd2 !== undefined) {
            cmd2.execute();
            CommandManager.executed.push(cmd2);
        }
    };

    return CommandManager;
})();

const generateUUID = function () {
    let d = new Date().getTime();
    const uuid = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
        const r = (d + Math.random() * 16) % 16 | 0;
        d = Math.floor(d / 16);
        return (c == "x" ? r : (r & 0x7) | 0x8).toString(16);
    });
    return uuid;
};

function render(downloadUrl) {
    const defaults = { color: "red", width: 4, opacity: 0.5 };
    $.fn.createCanvas = function (options) {
        let settings = $.extend({}, defaults, options || {});
        const self = this;

        this.setOptions = function (options) {
            settings = $.extend(settings, options);
        };

        $(document).ready(function () {
            $(self).each(function (eachIndex, eachItem) {
                self.paths = [];
                const img = eachItem;
                // Get a reference to the canvas object
                const canvas = $("<canvas>")
                    .attr({
                        width: options.img_width + "px",
                        height: options.img_height + "px",
                    })
                    .addClass("image-canvas")
                    .css({
                        position: "absolute",
                        top: "0px",
                        left: "0px",
                    });
                $(img).after(canvas);
                $(img).data("paths", []);
                // Create an empty project and a view for the canvas
                paper.setup(canvas[0]);
                canvas[0].width = options.img_width;
                canvas[0].height = options.img_height;

                $(canvas).mouseenter(function () {
                    paper.projects[eachIndex].activate();
                });
                // Create a simple drawing tool:
                const tool = new paper.Tool();

                tool.onMouseMove = function (event) {
                    if (!$(".context-menu-list").is(":visible")) {
                        paper.project.activeLayer.selected = false;
                        self.setPenColor(settings.color);
                        if (event.item) {
                            event.item.selected = true;
                            selectedItem = event.item;
                            self.setCursorHandOpen();
                        } else {
                            selectedItem = null;
                        }
                    }
                };

                tool.onMouseDown = function (event) {
                    switch (event.event.button) {
                        // leftclick
                        case 0:
                            // If we produced a path before, deselect it:
                            if (path) {
                                path.selected = false;
                            }

                            path = new paper.Path();
                            path.data.id = generateUUID();
                            path.strokeColor = settings.color;
                            path.strokeWidth = settings.width;
                            path.opacity = settings.opacity;
                            break;
                        // rightclick
                        case 2:
                            break;
                    }
                };

                tool.onMouseDrag = function (event) {
                    switch (event.event.button) {
                        // leftclick
                        case 0:
                            // Every drag event, add a point to the path at the current
                            // position of the mouse:
                            if (selectedItem) {
                                if (!mouseDownPoint) {
                                    mouseDownPoint = selectedItem.position;
                                }
                                self.setCursorHandClose();
                                selectedItem.position = new paper.Point(
                                    selectedItem.position.x + event.delta.x,
                                    selectedItem.position.y + event.delta.y
                                );
                            } else if (path) {
                                path.add(event.point);
                            }
                            break;
                        // rightclick
                        case 2:
                            break;
                    }
                };

                tool.onMouseUp = function (event) {
                    switch (event.event.button) {
                        // leftclick
                        case 0:
                            if (selectedItem) {
                                if (mouseDownPoint) {
                                    const selectedItemId = selectedItem.id;
                                    const draggingStartPoint = { x: mouseDownPoint.x, y: mouseDownPoint.y };
                                    CommandManager.execute({
                                        execute: function () {
                                            //item was already moved, so do nothing
                                        },
                                        unexecute: function () {
                                            $(paper.project.activeLayer.children).each(function (index, item) {
                                                if (item.id == selectedItemId) {
                                                    if (item.segments) {
                                                        new paper.Point(
                                                            (item.segments[item.segments.length - 1].point.x -
                                                                item.segments[0].point.x) /
                                                                2,
                                                            (item.segments[item.segments.length - 1].point.y -
                                                                item.segments[0].point.y) /
                                                                2
                                                        );
                                                        item.position = new paper.Point(
                                                            draggingStartPoint.x,
                                                            draggingStartPoint.y
                                                        );
                                                    } else {
                                                        item.position = draggingStartPoint;
                                                    }
                                                    return false;
                                                }
                                            });
                                        },
                                    });
                                    mouseDownPoint = null;
                                }
                            } else {
                                // When the mouse is released, simplify it:
                                path.simplify();
                                path.remove();
                                const strPath = path.exportJSON({ asString: true });
                                const uid = generateUUID();
                                CommandManager.execute({
                                    execute: function () {
                                        path = new paper.Path();
                                        path.importJSON(strPath);
                                        path.data.uid = uid;
                                    },
                                    unexecute: function () {
                                        $(paper.project.activeLayer.children).each(function (index, item) {
                                            if (item.data && item.data.uid) {
                                                if (item.data.uid == uid) {
                                                    item.remove();
                                                }
                                            }
                                        });
                                    },
                                });
                            }
                            break;
                        // rightclick
                        case 2:
                            contextPoint = event.point;
                            //Unused?
                            //contextSelectedItemId = selectedItem ? selectedItem.data.id : "";
                            break;
                    }
                };

                tool.onKeyUp = function (event) {
                    if (selectedItem) {
                        // When a key is released, set the content of the text item:
                        if (selectedItem.content) {
                            if (event.key == "backspace") selectedItem.content = selectedItem.content.slice(0, -1);
                        } else {
                            selectedItem.content = selectedItem.content.replace("<some text>", "");
                            if (event.key == "space") selectedItem.content += " ";
                            else if (event.key.length == 1) selectedItem.content += event.key;
                        }
                    }
                };
                paper.view.draw();
            });
        });

        let path;
        let contextPoint;
        //let contextSelectedItemId;
        let selectedItem;
        let mouseDownPoint;
        this.downloadCanvas = function (canvas, filename) {
            /// create an "off-screen" anchor tag
            const lnk = document.createElement("a");

            /// the key here is to set the download attribute of the a tag
            lnk.download = filename;

            /// convert canvas content to data-uri for link. When download
            /// attribute is set the content pointed to by link will be
            /// pushed as "download" in HTML5 capable browsers
            lnk.href = canvas.toDataURL();

            /// create a "fake" click-event to trigger the download
            if (document.createEvent) {
                const e = document.createEvent("MouseEvents");
                e.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, null);
                lnk.dispatchEvent(e);
            } else if (lnk.fireEvent) {
                lnk.fireEvent("onclick");
            }
        };

        this.download = function () {
            const canvas = paper.project.activeLayer.view.element;
            const img = $(canvas)[0];
            const mergeCanvas = $("<canvas>").attr({
                width: img.width,
                height: img.height,
            });
            const mergedContext = mergeCanvas[0].getContext("2d");
            mergedContext.clearRect(0, 0, img.width, img.height);
            mergedContext.drawImage(img, 0, 0);
            mergedContext.drawImage(canvas, 0, 0);
            self.downloadCanvas(mergeCanvas[0], "only-annotations.png");

            // create canvas for original and annotations
            const annotated_img = $(canvas).parent().find("img")[0];
            const mergeCanvasAnnotated = $("<canvas>").attr({
                width: $(annotated_img).width(),
                height: $(annotated_img).height(),
            });
            const mergedContextAnnotated = mergeCanvasAnnotated[0].getContext("2d");
            mergedContextAnnotated.clearRect(0, 0, $(annotated_img).width(), $(annotated_img).height());
            mergedContextAnnotated.drawImage(annotated_img, 0, 0);
            mergedContextAnnotated.drawImage(canvas, 0, 0);
            self.downloadCanvas(mergeCanvasAnnotated[0], "original-with-annotations.png");
        };

        this.setText = function () {
            const uid = generateUUID();
            const pos = contextPoint;
            CommandManager.execute({
                execute: function () {
                    const TXT_DBL_CLICK = "<<double click to edit>>";
                    const txt = TXT_DBL_CLICK;
                    const text = new paper.PointText(pos);
                    text.content = txt;
                    text.fillColor = settings.color;
                    text.fontSize = 14;
                    text.fontFamily = "sans-serif";
                    text.data.uid = uid;
                    text.opacity = settings.opacity;
                    text.onDoubleClick = function (event) {
                        if (this.className == "PointText") {
                            const txt = window.prompt("Type in your text", this.content.replace(TXT_DBL_CLICK, ""));
                            if (txt.length > 0) this.content = txt;
                        }
                    };
                },
                unexecute: function () {
                    $(paper.project.activeLayer.children).each(function (index, item) {
                        if (item.data && item.data.uid) {
                            if (item.data.uid == uid) {
                                item.remove();
                            }
                        }
                    });
                },
            });
        };

        this.setPenColor = function (color) {
            self.setOptions({ color: color });
            $(".image-canvas").css(
                "cursor",
                "url(/static/plugins/visualizations/annotate_image/static/images/" + color + "-pen.png) 14 50, auto"
            );
        };

        this.setCursorHandOpen = function () {
            $(".image-canvas").css(
                "cursor",
                "url(/static/plugins/visualizations/annotate_image/static/images/hand-open.png) 25 25, auto"
            );
        };

        this.setCursorHandClose = function () {
            $(".image-canvas").css(
                "cursor",
                "url(/static/plugins/visualizations/annotate_image/static/images/hand-close.png) 25 25, auto"
            );
        };

        $.contextMenu({
            selector: ".image-canvas",
            callback: function (key, options) {
                switch (key) {
                    //COMMANDS
                    case "undo":
                        CommandManager.undo();
                        break;
                    case "redo":
                        CommandManager.redo();
                        break;
                    case "download":
                        self.download();
                        break;
                    //TOOLS
                    case "text":
                        self.setText();
                        break;
                    //PENS
                    case "blackPen":
                        self.setPenColor("black");
                        break;
                    case "redPen":
                        self.setPenColor("red");
                        break;
                    case "greenPen":
                        self.setPenColor("green");
                        break;
                    case "bluePen":
                        self.setPenColor("blue");
                        break;
                    case "yellowPen":
                        self.setPenColor("yellow");
                        break;
                }
            },
            items: {
                undo: { name: "Undo", icon: "undo" },
                redo: { name: "Redo", icon: "redo" },
                download: { name: "Download", icon: "download" },
                sep1: "---------",
                text: { name: "Text", icon: "text" },
                sep2: "---------",
                blackPen: { name: "Black Pen", icon: "blackpen" },
                redPen: { name: "Red Pen", icon: "redpen" },
                greenPen: { name: "Green Pen", icon: "greenpen" },
                bluePen: { name: "Blue Pen", icon: "bluepen" },
                yellowPen: { name: "Yellow Pen", icon: "yellowpen" },
            },
        });

        const $menuList = $(".context-menu-list");
        $menuList.find(".context-menu-icon-text").css({
            "background-image": "url(/static/plugins/visualizations/annotate_image/static/images/text.png)",
            "background-repeat": "no-repeat",
            "background-position": "right 96% bottom 45%",
        });
        $menuList.find(".context-menu-icon-blackpen").css({
            "background-image": "url(/static/plugins/visualizations/annotate_image/static/images/blackpen.png)",
            "background-repeat": "no-repeat",
            "background-position": "right 97% bottom 48%",
        });
        $menuList.find(".context-menu-icon-redpen").css({
            "background-image": "url(/static/plugins/visualizations/annotate_image/static/images/redpen.png)",
            "background-repeat": "no-repeat",
            "background-position": "right 97% bottom 48%",
        });
        $menuList.find(".context-menu-icon-greenpen").css({
            "background-image": "url(/static/plugins/visualizations/annotate_image/static/images/greenpen.png)",
            "background-repeat": "no-repeat",
            "background-position": "right 97% bottom 48%",
        });
        $menuList.find(".context-menu-icon-bluepen").css({
            "background-image": "url(/static/plugins/visualizations/annotate_image/static/images/bluepen.png)",
            "background-repeat": "no-repeat",
            "background-position": "right 97% bottom 48%",
        });
        $menuList.find(".context-menu-icon-yellowpen").css({
            "background-image": "url(/static/plugins/visualizations/annotate_image/static/images/yellowpen.png)",
            "background-repeat": "no-repeat",
            "background-position": "right 97% bottom 48%",
        });
    };

    fetch(downloadUrl)
        .then((response) => {
            if (!response.ok) {
                throw new Error("Failed to access dataset.");
            }

            const $chartViewer = $("#app");
            $chartViewer.html("<img id='image-annotate' src='" + downloadUrl + "' />");
            $chartViewer.css("overflow", "auto");
            $chartViewer.css("position", "relative");

            const $image = $chartViewer.find("img");
            $image.on("load", function () {
                const width = $(this).width();
                const height = $(this).height();
                $image.width(width);
                $image.height(height);
                $image.createCanvas({
                    color: "red",
                    width: 2,
                    opacity: 0.5,
                    img_width: width,
                    img_height: height,
                });
            });
        })
        .catch((error) => {
            console.error(error.message);
        });
};

const { visualization_config, root } = JSON.parse(document.getElementById("app").dataset.incoming);

const datasetId = visualization_config.dataset_id;

const downloadUrl = window.location.origin + root + "api/datasets/" + datasetId + "/display";

render(downloadUrl);
