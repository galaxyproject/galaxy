import $ from "jquery";
import paper from "../node_modules/paper/dist/paper-full.min.js";
import "jquery-contextmenu";
import "jquery.ui.position";
import _ from "underscore";
//import paper from "../node_modules/paper/dist/paper-core.js";

import "../node_modules/jquery-contextmenu/dist/jquery.contextMenu.css";


var CommandManager = (function() {
    function CommandManager() {}

    CommandManager.executed = [];
    CommandManager.unexecuted = [];

    CommandManager.execute = function execute(cmd) {
        cmd.execute();
        CommandManager.executed.push(cmd);
    };

    CommandManager.undo = function undo() {
        var cmd1 = CommandManager.executed.pop();
        if (cmd1 !== undefined) {
            if (cmd1.unexecute !== undefined) {
                cmd1.unexecute();
            }
            CommandManager.unexecuted.push(cmd1);
        }
    };

    CommandManager.redo = function redo() {
        var cmd2 = CommandManager.unexecuted.pop();

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

var generateUUID = function() {
    var d = new Date().getTime();
    var uuid = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function(c) {
        var r = (d + Math.random() * 16) % 16 | 0;
        d = Math.floor(d / 16);
        return (c == "x" ? r : (r & 0x7) | 0x8).toString(16);
    });
    return uuid;
};

_.extend(window.bundleEntries || {}, {
    load: function(opt) {
        let chart = opt.chart;
        let dataset = opt.dataset;
        let defaults = {color: "red", width: 4, opacity: 0.5};
        $.fn.createCanvas = function(options) {
            console.log(options);
            let settings = $.extend({}, defaults, options || {});
            let self = this;

            this.setOptions = function(options) {
                settings = $.extend(settings, options);
            };
            
            $(document).ready(function() {
                $(self).each(function(eachIndex, eachItem) {
                    self.paths = [];
                    var img = eachItem;
                    // Get a reference to the canvas object
                    var canvas = $("<canvas>")
                        .attr({
                            width: options.img_width + "px",
                            height: options.img_height + "px"
                        })
                        .addClass("image-canvas")
                        .css({
                            position: "absolute",
                            top: "0px",
                            left: "0px"
                        });
                    $(img).after(canvas);
                    $(img).data("paths", []);
                    // Create an empty project and a view for the canvas
                    paper.setup(canvas[0]);
                    canvas[0].width = options.img_width;
                    canvas[0].height = options.img_height;
                    console.log(paper);
                    
                    $(canvas).mouseenter(function() {
                        paper.projects[eachIndex].activate();
                    });
                    // Create a simple drawing tool:
                    var tool = new paper.Tool();
                    
                    tool.onMouseMove = function(event) {
                        if (!$(".context-menu-list").is(":visible")) {
                            position = event.point;
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
                    
                    tool.onMouseDown = function(event) {
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
                    
                    tool.onMouseDrag = function(event) {
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
                                } 
                                else if (path) {
                                    path.add(event.point);
                                }
                                break;
                                // rightclick
                            case 2:
                                break;
                        }
                    };
                    
                    tool.onMouseUp = function(event) {
                        switch (event.event.button) {
                            // leftclick
                            case 0:
                                if (selectedItem) {
                                    if (mouseDownPoint) {
                                        var selectedItemId = selectedItem.id;
                                        var draggingStartPoint = { x: mouseDownPoint.x, y: mouseDownPoint.y };
                                        CommandManager.execute({
                                            execute: function() {
                                                //item was already moved, so do nothing
                                            },
                                            unexecute: function() {
                                                $(paper.project.activeLayer.children).each(function(index, item) {
                                                    if (item.id == selectedItemId) {
                                                        if (item.segments) {
                                                            var middlePoint = new paper.Point(
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
                                            }
                                        });
                                        mouseDownPoint = null;
                                    }
                                } else {
                                    // When the mouse is released, simplify it:
                                    path.simplify();
                                    path.remove();
                                    var strPath = path.exportJSON({ asString: true });
                                    var uid = generateUUID();
                                    CommandManager.execute({
                                        execute: function() {
                                            path = new paper.Path();
                                            path.importJSON(strPath);
                                            path.data.uid = uid;
                                        },
                                        unexecute: function() {
                                            $(paper.project.activeLayer.children).each(function(index, item) {
                                                if (item.data && item.data.uid) {
                                                    if (item.data.uid == uid) {
                                                            item.remove();
                                                    }
                                                }
                                            });
                                        }
                                    });
                                }
                                break;
                            // rightclick
                            case 2:
                                contextPoint = event.point;
                                contextSelectedItemId = selectedItem ? selectedItem.data.id : "";
                                break;
                        }
                    };
                    
                    tool.onKeyUp = function (event) {
                        if (selectedItem) {
                            // When a key is released, set the content of the text item:
                            if (selectedItem.content) {
                                if (event.key == 'backspace') selectedItem.content = selectedItem.content.slice(0, -1);
                            }
                            else {
                                selectedItem.content = selectedItem.content.replace('<some text>', '');
                                if (event.key == 'space') selectedItem.content += ' ';
                                else if (event.key.length == 1) selectedItem.content += event.key;
                            }
                        }
                    };
                    paper.view.draw();
                });
            });
            
            
            var path;
            var position;
            var contextPoint;
            var contextSelectedItemId;
            var selectedItem;
            var mouseDownPoint;
 
            this.erase = function () {
                var strPathArray = new Array();
                $(paper.project.activeLayer.children).each(function (index, item) {
                    if (contextSelectedItemId) {
                        if (contextSelectedItemId.length == 0 || item.data.id == contextSelectedItemId) {
                            var strPath = item.exportJSON({ asString: true });
                            strPathArray.push(strPath);
                        }
                    }
                });
 
                CommandManager.execute({
                    execute: function () {
                        $(paper.project.activeLayer.children).each(function (index, item) {
                            if (contextSelectedItemId) {
                                if (contextSelectedItemId.length == 0 || item.data.id == contextSelectedItemId) {
                                    item.remove();
                                }
                            }
                        });
                    },
                    unexecute: function () {
                        $(strPathArray).each(function (index, strPath) {
                            path = new paper.Path();
                            path.importJSON(strPath);
                        });
                    }
                });
            }
            
            
            
            this.setPenColor = function (color) {
                self.setOptions({ color: color });
                $('.image-canvas').css('cursor', "url(/static/plugins/visualizations/annotate_image/static/images/" + color + "-pen.png) 14 50, auto");
            }
 
            this.setCursorHandOpen = function () {
                $('.image-canvas').css('cursor', "url(/static/plugins/visualizations/annotate_image/static/images/hand-open.png) 25 25, auto");
            }
 
            this.setCursorHandClose = function () {
                $('.image-canvas').css('cursor', "url(/static/plugins/visualizations/annotate_image/static/images/hand-close.png) 25 25, auto");
            }
 
            $.contextMenu({
                selector: '.image-canvas',
                callback: function (key, options) {
                    switch (key) {
                        //COMMANDS
                        case 'undo':
                            CommandManager.undo();
                            break;
                        case 'redo':
                            CommandManager.redo();
                            break;
                        case 'erase':
                            self.erase();
                            break;
                        case 'download':
                            self.download();
                            break;
                            //TOOLS
                        case 'text':
                            self.setText();
                            break;
                            //PENS
                        case 'blackPen':
                            self.setPenColor('black');
                            break;
                        case 'redPen':
                            self.setPenColor('red');
                            break;
                        case 'greenPen':
                            self.setPenColor('green');
                            break;
                        case 'bluePen':
                            self.setPenColor('blue');
                            break;
                        case 'yellowPen':
                            self.setPenColor('yellow');
                            break;
                    }
                },
                items: {
                    "undo": { name: "Undo", icon: "undo" },
                    "redo": { name: "Redo", icon: "redo" },
                    "erase": { name: "Erase", icon: "erase" },
                    "download": { name: "Download", icon: "download" },
                    "sep1": "---------",
                    "text": { name: "Text", icon: "text" },
                    "sep2": "---------",
                    "blackPen": { name: "Black Pen", icon: "blackpen" },
                    "redPen": { name: "Red Pen", icon: "redpen" },
                    "greenPen": { name: "Green Pen", icon: "greenpen" },
                    "bluePen": { name: "Blue Pen", icon: "bluepen" },
                    "yellowPen": { name: "Yellow Pen", icon: "yellowpen" },
                }
            });
            
        }

        $.ajax({
            url: dataset.download_url,
            success: function(content) {
                //console.log(opt);
                let $chartViewer = $("#" + opt.targets[0]);
                $("#" + opt.targets[0]).html("<img id='image-annotate' src='" + dataset.download_url + "' />");
                let $image = $("#" + opt.targets[0] + " img");
                console.log($image);
                $image.on("load", function() {
                    let width = $(this).width();
                    let height = $(this).height();
                    $image.width(width);
                    $image.height(height);
                    $image.createCanvas({
                        color: "red",
                        width: 2,
                        opacity: 0.5,
                        img_width: width,
                        img_height: height
                    });
                });
                chart.state("ok", "Chart drawn.");
                opt.process.resolve();
            },
            error: function() {
                chart.state("failed", "Failed to access dataset.");
                opt.process.resolve();
            }
        });
    }
});
