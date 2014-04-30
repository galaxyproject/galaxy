// dependencies
define(['utils/utils'], function(Utils) {

// widget
return Backbone.View.extend(
{
    // number of columns and rows
    colNumber: 0,
    rowNumber: 0,
    
    // indices
    rowIndex: [],
    colIndex: [],
    
    // labels
    rowLabel: [],
    colLabel: [],
    
    // cell size
    cellSize: 0,
    
    // color buckets
    colorBuckets: 0,
        
    // default settings
    optionsDefault: {
        margin : {
            top         : 50,
            right       : 10,
            bottom      : 50,
            left        : 100
        },
        colors : ['#005824','#1A693B','#347B53','#4F8D6B','#699F83','#83B09B','#9EC2B3','#B8D4CB','#D2E6E3','#EDF8FB','#FFFFFF','#F1EEF6','#E6D3E1','#DBB9CD','#D19EB9','#C684A4','#BB6990','#B14F7C','#A63467','#9B1A53','#91003F']
    },

    // initialize
    initialize: function(options) {
        // load options
        this.options = Utils.merge(options, this.optionsDefault)
        
        // add ui elements
        this.options.div.append(this._templateTooltip());
        this.options.div.append(this._templateSelect());
        
        // access data
        var data = this.options.data;
        
        // identify unique labels
        var col_hash = {};
        var row_hash = {};
        
        // create label indices
        this.colNumber = 0;
        this.rowNumber = 0;
        for (var i in data) {
            var cell = data[i];
            
            // add label to index list
            var col_label = cell.col_label;
            if (col_hash[col_label] === undefined) {
                col_hash[col_label] = ++this.colNumber;
            }
            var row_label = cell.row_label;
            if (row_hash[row_label] === undefined) {
                row_hash[row_label] = ++this.rowNumber;
            }
        }
        
        // add indices to data
        for (var i in data) {
            var cell = data[i];
            cell.col = col_hash[cell.col_label];
            cell.row = row_hash[cell.row_label];
        }
        
        // add row labels
        this.rowIndex = []
        for (var key in row_hash) {
            this.rowLabel.push(key);
            this.rowIndex.push(row_hash[key]);
        }
        
        // add col labels
        this.colIndex = []
        for (var key in col_hash) {
            this.colLabel.push(key);
            this.colIndex.push(col_hash[key]);
        }
        console.log(this.rowIndex);
        console.log(this.colIndex);
        
        // identify buckets
        this.colorBuckets = this.options.colors.length;
        
        // draw
        this._draw(this.options.div, this.options.data);
    },
    
    _draw: function(container, data) {
        // get height
        this.width = parseInt(container.width()) - this.options.margin.left;
        this.height = parseInt(container.height()) - 2*this.options.margin.top;
        
        // calculate cell size
        this.cellSize = Math.min(   this.height / (this.rowNumber),
                                    this.width / (this.colNumber));
        
        // set width/height for plugin
        this.width  = this.options.cellSize * this.colNumber;
        this.height = this.options.cellSize * this.rowNumber;
        
        // set legend width
        this.legendElementWidth = this.options.cellSize * 2.5;
      
        // configure
        var margin = this.options.margin;
        var cellSize = this.cellSize;
        var colNumber = this.colNumber;
        var rowNumber = this.rowNumber;
        var colorBuckets = this.colorBuckets;
        var colors = this.options.colors;
        var rowIndex = this.rowIndex;
        var colIndex = this.colIndex;
        var colLabel = this.colLabel;
        var rowLabel = this.rowLabel;
        var width = this.width;
        var height = this.height;
        var legendElementWidth = this.legendElementWidth;
        
        // color scale
        var colorScale = d3.scale.quantile()
            .domain([ -10, 0, 10])
            .range(colors);
        
        // add graph
        var svg = d3.select(container[0]).append('svg')
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")")
      
        // row labels
        var rowSortOrder=false;
        var colSortOrder=false;
        var rowLabels = svg.append("g")
            .selectAll(".rowLabelg")
            .data(rowLabel)
            .enter()
            .append("text")
            .text(function (d) { return d; })
            .attr("x", 0)
            .attr("y", function (d, i) { return rowIndex.indexOf(i+1) * cellSize; })
            .style("font-size", cellSize + "px")
            .style("text-anchor", "end")
            .attr("transform", "translate(-10," + cellSize / 1.5 + ")")
            .attr("class", function (d,i) { return "rowLabel mono r"+i;} ) 
            .on("mouseover", function(d) {
                d3.select(this).classed("text-hover",true);
                d3.select(this).style("font-size", parseInt(cellSize * 1.3) + "px");
            })
            .on("mouseout" , function(d) {
                d3.select(this).classed("text-hover",false);
                d3.select(this).style("font-size", parseInt(cellSize) + "px");
            })
            .on("click", function(d,i) {rowSortOrder=!rowSortOrder; sortbylabel("r",i,rowSortOrder);d3.select("#order").property("selectedIndex", 4).node().focus();;});
        
        // column labels
        var colLabels = svg.append("g")
            .selectAll(".colLabelg")
            .data(colLabel)
            .enter()
            .append("text")
            .text(function (d) { return d; })
            .attr("x", 0)
            .attr("y", function (d, i) { return colIndex.indexOf(i+1) * cellSize; })
            .style("font-size", cellSize + "px")
            .style("text-anchor", "left")
            .attr("transform", "translate("+cellSize/2 + ",-17) rotate (-90)")
            .attr("class",  function (d,i) { return "colLabel mono c"+i;} )
            .on("mouseover", function(d) {
                d3.select(this).classed("text-hover",true);
                d3.select(this).style("font-size", parseInt(cellSize * 1.3) + "px");
            })
            .on("mouseout" , function(d) {
                d3.select(this).classed("text-hover",false);
                d3.select(this).style("font-size", parseInt(cellSize) + "px");
            })
            .on("click", function(d,i) {colSortOrder=!colSortOrder;  sortbylabel("c",i,colSortOrder);d3.select("#order").property("selectedIndex", 4).node().focus();;});

        // heat map
        var heatMap = svg.append("g").attr("class","g3")
            .selectAll(".cellg")
            .data(data,function(d){return d.row+":"+d.col;})
            .enter()
            .append("rect")
            .attr("x", function(d) { return colIndex.indexOf(d.col) * cellSize; })
            .attr("y", function(d) { return rowIndex.indexOf(d.row) * cellSize; })
            .attr("class", function(d){return "cell cell-border cr"+(d.row-1)+" cc"+(d.col-1);})
            .attr("width", cellSize)
            .attr("height", cellSize)
            .style("fill", function(d) { return colorScale(d.value); })
            // .on("click", function(d) {
            //       var rowtext=d3.select(".r"+(d.row-1));
            //       if(rowtext.classed("text-selected")==false){
            //           rowtext.classed("text-selected",true);
            //       }else{
            //           rowtext.classed("text-selected",false);
            //       }
            //})
            .on("mouseover", function(d){
                //highlight text
                d3.select(this).classed("cell-hover",true);
                d3.selectAll(".rowLabel").classed("text-highlight",function(r,ri){ return ri==(d.row-1);});
                d3.selectAll(".colLabel").classed("text-highlight",function(c,ci){ return ci==(d.col-1);});
                //d3.selectAll(".colLabel").style("font-size", parseInt(cellSize * 1.3) + "px");
                //d3.selectAll(".rowLabel").style("font-size", parseInt(cellSize * 1.3) + "px");
                
                //Update the tooltip position and value
                d3.select("#heatmap-tooltip")
                    .style("left", (d3.event.pageX+10) + "px")
                    .style("top", (d3.event.pageY-10) + "px")
                    .select("#value")
                    .text("lables:"+rowLabel[d.row-1]+","+colLabel[d.col-1]+"\ndata:"+d.value+"\nrow-col-idx:"+d.col+","+d.row+"\ncell-xy "+this.x.baseVal.value+", "+this.y.baseVal.value);
                //Show the tooltip
                d3.select("#heatmap-tooltip").classed("hidden", false);
            })
            .on("mouseout", function(){
                d3.select(this).classed("cell-hover",false);
                d3.selectAll(".rowLabel").classed("text-highlight",false);
                d3.selectAll(".colLabel").classed("text-highlight",false);
                //d3.selectAll(".colLabel").style("font-size", parseInt(cellSize) + "px");
                //d3.selectAll(".rowLabel").style("font-size", parseInt(cellSize) + "px");
                d3.select("#heatmap-tooltip").classed("hidden", true);
            });
        
        var legend = svg.selectAll(".legend")
            .data([-10,-9,-8,-7,-6,-5,-4,-3,-2,-1,0,1,2,3,4,5,6,7,8,9,10])
            .enter().append("g")
            .attr("class", "legend");

        legend.append("rect")
            .attr("x", function(d, i) { return legendElementWidth * i; })
            .attr("y", height+(cellSize*2))
            .attr("width", legendElementWidth)
            .attr("height", cellSize)
            .style("fill", function(d, i) { return colors[i]; });

        legend.append("text")
            .attr("class", "mono")
            .text(function(d) { return d; })
            .attr("width", legendElementWidth)
            .attr("x", function(d, i) { return legendElementWidth * i; })
            .attr("y", height + (cellSize*4))
            .style("font-size", cellSize + "px");

        // change ordering of cells
        function sortbylabel(rORc,i,sortOrder) {
            var t = svg.transition().duration(3000);
            var values=[];
            var sorted; // sorted is zero-based index
            d3.selectAll(".c"+rORc+i) 
                .filter(function(ce){
                values.push(ce.value);
            });
            if(rORc=="r"){ // sort valuesatio of a gene
                sorted=d3.range(colNumber).sort(function(a,b){ if(sortOrder){ return values[b]-values[a];}else{ return values[a]-values[b];}});
                t.selectAll(".cell")
                    .attr("x", function(d) { return sorted.indexOf(d.col-1) * cellSize; });
                t.selectAll(".colLabel")
                    .attr("y", function (d, i) { return sorted.indexOf(i) * cellSize; });
            } else { // sort valuesatio of a contrast
                sorted=d3.range(rowNumber).sort(function(a,b){if(sortOrder){ return values[b]-values[a];}else{ return values[a]-values[b];}});
                t.selectAll(".cell")
                    .attr("y", function(d) { return sorted.indexOf(d.row-1) * cellSize; });
                t.selectAll(".rowLabel")
                    .attr("y", function (d, i) { return sorted.indexOf(i) * cellSize; });
            }
        }
        
        d3.select("#order").on("change",function(){
            order(this.value);
        });

        function order(value) {
            if(value=="hclust"){
                var t = svg.transition().duration(3000);
                t.selectAll(".cell")
                    .attr("x", function(d) { return colIndex.indexOf(d.col) * cellSize; })
                    .attr("y", function(d) { return rowIndex.indexOf(d.row) * cellSize; });

                t.selectAll(".rowLabel")
                    .attr("y", function (d, i) { return rowIndex.indexOf(i+1) * cellSize; });

                t.selectAll(".colLabel")
                    .attr("y", function (d, i) { return colIndex.indexOf(i+1) * cellSize; });

            } else if (value=="probecontrast") {
                var t = svg.transition().duration(3000);
                t.selectAll(".cell")
                    .attr("x", function(d) { return (d.col - 1) * cellSize; })
                    .attr("y", function(d) { return (d.row - 1) * cellSize; });

                t.selectAll(".rowLabel")
                    .attr("y", function (d, i) { return i * cellSize; });

                t.selectAll(".colLabel")
                    .attr("y", function (d, i) { return i * cellSize; });
            } else if (value=="probe") {
                var t = svg.transition().duration(3000);
                t.selectAll(".cell")
                    .attr("y", function(d) { return (d.row - 1) * cellSize; });

                t.selectAll(".rowLabel")
                    .attr("y", function (d, i) { return i * cellSize; });
            } else if (value=="contrast"){
                var t = svg.transition().duration(3000);
                t.selectAll(".cell")
                    .attr("x", function(d) { return (d.col - 1) * cellSize; });
                t.selectAll(".colLabel")
                    .attr("y", function (d, i) { return i * cellSize; });
            }
        }
        
        var sa=d3.select(".g3")
            .on("mousedown", function() {
                if( !d3.event.altKey) {
                    d3.selectAll(".cell-selected").classed("cell-selected",false);
                    d3.selectAll(".rowLabel").classed("text-selected",false);
                    d3.selectAll(".colLabel").classed("text-selected",false);
                }
                var p = d3.mouse(this);
                sa.append("rect")
                .attr({
                    rx      : 0,
                    ry      : 0,
                    class   : "selection",
                    x       : p[0],
                    y       : p[1],
                    width   : 1,
                    height  : 1
                })
            })
            .on("mousemove", function() {
                var s = sa.select("rect.selection");
          
                if(!s.empty()) {
                    var p = d3.mouse(this),
                    d = {
                        x       : parseInt(s.attr("x"), 10),
                        y       : parseInt(s.attr("y"), 10),
                        width   : parseInt(s.attr("width"), 10),
                        height  : parseInt(s.attr("height"), 10)
                    },
                    move = {
                        x : p[0] - d.x,
                        y : p[1] - d.y
                    };
          
                    if(move.x < 1 || (move.x*2<d.width)) {
                        d.x = p[0];
                        d.width -= move.x;
                    } else {
                        d.width = move.x;       
                    }

                    if(move.y < 1 || (move.y*2<d.height)) {
                        d.y = p[1];
                        d.height -= move.y;
                    } else {
                        d.height = move.y;       
                    }
                    s.attr(d);
          
                    // deselect all temporary selected state objects
                    d3.selectAll(".cell-selection.cell-selected").classed("cell-selected", false);
                    d3.selectAll(".text-selection.text-selected").classed("text-selected",false);

                    d3.selectAll('.cell').filter(function(cell_d, i) {
                        if(!d3.select(this).classed("cell-selected") &&
                            // inner circle inside selection frame
                            (this.x.baseVal.value)+cellSize >= d.x && (this.x.baseVal.value)<=d.x+d.width &&
                            (this.y.baseVal.value)+cellSize >= d.y && (this.y.baseVal.value)<=d.y+d.height)
                            {
                                d3.select(this)
                                    .classed("cell-selection", true)
                                    .classed("cell-selected", true);

                                d3.select(".r"+(cell_d.row-1))
                                    .classed("text-selection",true)
                                    .classed("text-selected",true);

                                d3.select(".c"+(cell_d.col-1))
                                    .classed("text-selection",true)
                                    .classed("text-selected",true);
                            }
                    });
                }
            })
            .on("mouseup", function() {
                // remove selection frame
                sa.selectAll("rect.selection").remove();

                // remove temporary selection marker class
                d3.selectAll(".cell-selection").classed("cell-selection", false);
                d3.selectAll(".text-selection").classed("text-selection",false);
            })
            .on("mouseout", function() {
                if(d3.event.relatedTarget.tagName=='html') {
                    // remove selection frame
                    sa.selectAll("rect.selection").remove();
                
                    // remove temporary selection marker class
                    d3.selectAll(".cell-selection").classed("cell-selection", false);
                    d3.selectAll(".rowLabel").classed("text-selected",false);
                    d3.selectAll(".colLabel").classed("text-selected",false);
                }
            });
        },
        
        // template
        _templateSelect: function() {
            return  '<select id="order">' +
                        '<option value="hclust">by cluster</option>' +
                        '<option value="probecontrast">by probe name and contrast name</option>' +
                        '<option value="probe">by probe name</option>' +
                        '<option value="contrast">by contrast name</option>' +
                        '<option value="custom">by log2 ratio</option>' +
                    '</select>';
        },
        
        // template
        _templateTooltip: function() {
            return  '<div id="heatmap-tooltip" class="hidden">' +
                        '<p><span id="value"></p>'
                    '</div>';
        }
    });
});