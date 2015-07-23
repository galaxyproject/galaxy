function date_by_subtracting_days(date, days) {
    return new Date(
        date.getFullYear(), 
        date.getMonth(), 
        date.getDate() - days,
        date.getHours(),
        date.getMinutes(),
        date.getSeconds(),
        date.getMilliseconds()
    );
}

function date_by_adding_hours(date, hours) {
    return new Date(
        date.getFullYear(), 
        date.getMonth(), 
        date.getDate(),
        date.getHours() + hours,
        date.getMinutes(),
        date.getSeconds(),
        date.getMilliseconds()
    );
}

function get_utc_time() {
    var date = new Date()
    return new Date(
    date.getUTCFullYear(),
    date.getUTCMonth(),
    date.getUTCDate(),
    date.getUTCHours(),
    date.getUTCMinutes(), 
    date.getUTCSeconds()
  )
}

function refresh() {
    window.location.reload(true);
}
setTimeout(refresh, 900000); //15 minutes = 900000 ms

function create_chart( inp_data, name, time, title ) {
    require( ["d3"], function (e) {
        var data = inp_data;
        var margin = {top: 60, right: 30, bottom: 50, left: 60};
        var chart_zoom = 1.8;

        function click() {
            var classes = d3.select(this).attr("class");
            classes = classes.split(" ");
            d3.selectAll("." + classes[0]).filter("." + classes[1])
                .transition()
                    .duration(750)
                    .attr("height", chart_height)
                    .attr("width", chart_width);

            d3.select(this)
                .transition()
                    .duration(750)
                    .attr("height", chart_height*chart_zoom)
                    .attr("width", chart_width*chart_zoom);
        }

        var height = 150;
        if(d3.max(data) != 0) {
            var zoom = height / d3.max(data);
        } else {
            var zoom = 1.0;
        }
        var chart_height = height + margin.top + margin.bottom;
        $(".charts").css("height", chart_height * (chart_zoom));

        var width = 300;
        var barWidth = 0;
        if(time == "hours") {
            barWidth = width / 24;
        } else if(time == "days") {
            barWidth = width / 30;
        }
        var chart_width = width + margin.left + margin.right;

        var chart = d3.select("#" + name)
            .attr("width", chart_width)
            .attr("height", chart_width)
            .attr("preserveAspectRatio", "xMidYMin")
            .attr("viewBox", "0 0 " + chart_width + " " + chart_height)
            .on("click", click);

        var bar = chart.selectAll("g")
            .data(data)
            .enter().append("g")
                .attr("transform", function(d, i) {
                    curr_margin = +margin.left;
                    curr_margin += +(i * barWidth);
                    return "translate(" + curr_margin + "," + margin.top + ")";
                })
                .on("mouseenter", function(d) {
                    var i = 0;
                    var size = d;

                    while( size >= 1) {
                        size = size / 10;
                        i++;
                    }

                    var wdth = (i * 4) + 10;
                    d3.select(d3.event.path[1]).select(".tool_tip")
                        .select("text")
                            .attr("transform", "translate( " + (margin.left - 5) + ", " + ((height - (d * zoom)) + +margin.top + 10) + " )" )
                            .attr("visibility", "visible")
                            .text(d);

                    d3.select(d3.event.path[1]).select(".tool_tip")
                        .attr("width", wdth + "px")
                        .attr("height", "15px")
                        .select("rect")
                            .attr("transform", "translate( " + ((+margin.left) - wdth) + ", " + ((height - (d * zoom)) + +margin.top) + " )" )
                            .attr("width", wdth + "px")
                            .attr("height", "15px")
                            .attr("fill","#ebd9b2");
                })
                .on("mouseleave", function(d) {
                    d3.select(d3.event.path[1]).select(".tool_tip")
                        .select("text")
                            .attr("visibility", "hidden");

                    d3.select(d3.event.path[1]).select(".tool_tip")
                        .select("rect")
                            .attr("width", "0")
                            .attr("height", "0")
                            .attr("fill","")
                            .text(d);
                });
        chart.append("g")
            .append("text")
            .attr("class", "title")
            .attr("text-anchor", "end")
            .attr("transform", function(e) {
                return "translate( " + width + ",15 )";
            })
            .text(title);

        if (time == "hours") {
            var x = d3.time.scale.utc()
                .domain([get_utc_time(), date_by_subtracting_days(get_utc_time(), 1)])
                .rangeRound([0, width]);

            var xAxis = d3.svg.axis()
                .scale(x)
                .tickPadding(0)
                .tickFormat(d3.time.format('%b %d %H'))
                .ticks(d3.time.hours, 1)
                .orient("bottom")
                .tickSize(0)
                .outerTickSize(0);
        } else if (time == "days") {
            var x = d3.time.scale.utc()
                .domain([get_utc_time(), date_by_subtracting_days(get_utc_time(), 28)])
                .rangeRound([0, width])
                .nice();

            var xAxis = d3.svg.axis()
                .scale(x)
                .tickPadding(0)
                .tickFormat(d3.time.format('%b %d'))
                .ticks(d3.time.days, 1)
                .orient("bottom")
                .tickSize(0)
                .outerTickSize(0);
        }

        chart.append("g")
            .attr("class", "x axis")
            .attr("id", ("x_" + name))
            .attr("transform", "translate( " + (+margin.left) + "," + (+height + +margin.top )+ ")")
            .call(xAxis)
                .selectAll("text")
                .style("text-anchor", "end")
                .attr("transform", function() {
                    return "rotate(-60, 0, " + d3.select(this).node().getBBox().height + ")";
                });

        chart.append("g")
            .append("text")
                .attr("class", "ax_title")
                .attr("transform", function(e) {
                    var axis = d3.select("#x_" + name).node()
                    var left_pad = +margin.left + (axis.getBoundingClientRect().width/2) + 30;
                    var top_pad = +margin.top + height + axis.getBoundingClientRect().height + 10
                    var trans = "translate(" + left_pad + "," + top_pad + ")";

                    return trans;
                })
                .text(function(d) {
                    var info = "";
                    if(time == "hours") {
                        info = "Date(month day hour)";
                    } else if(time == "days") {
                        info = "Date(month day)";
                    }
                    return info;
                });

        var y = d3.scale.linear()
            .range([height, 0]);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .tickFormat( function(d) { return d3.round( d*d3.max(data), 0 ) });

        chart.append("g")
            .attr("class", "y axis")
            .attr("id", ("y_" + name))
            .attr("text-anchor", "end")
            .attr("transform", "translate( " + margin.left + "," + margin.top + ")")
            .call(yAxis)
                .select(".domain");

        chart.append("g")
            .append("text")
                .attr("class", "ax_title")
                .attr("transform", function(e) {
                    var axis = d3.select("#y_" + name).node()
                    var left_pad = +margin.left - axis.getBoundingClientRect().width - 5;
                    var top_pad = +margin.top + (axis.getBoundingClientRect().height/2) - 30
                    var trans = "translate(" + left_pad + "," + top_pad + ")rotate(-90)";

                    return trans;
                })
                .text("Number of Jobs");

        bar.append("rect")
            .attr("y", function(d) { return height - (d * zoom); })
            .attr("height", function(d) { return (d * zoom); })
            .attr("width", barWidth - 1);

        chart.append("g")
            .attr("class", "tool_tip")
            .append("rect");
        chart.select(".tool_tip")
            .append("text");

        if(name == "jc_dy_chart" || name == "jc_hr_chart") {
            d3.select("#" + name)
                .attr("height", chart_height * chart_zoom)
                .attr("width", chart_width * chart_zoom)
        }
    });
}

//============================================================================================================

function create_histogram( inp_data, name, time, title ) {
    require( ["d3"], function (e) {
        //inp_data is an array of numbers that are the amount of minutes per run
        var data = inp_data;
        var chart_zoom = 1.8;
            // Formatters for counts and times (converting numbers to Dates).
        function click(d) {
            var classes = d3.select(this).attr("class")
            classes = classes.split(" ");
            d3.selectAll("." + classes[0]).filter("." + classes[1])
                .transition()
                    .duration(750)
                    .attr("height", chart_height)
                    .attr("width", chart_width);

            d3.select(this)
            .transition()
                .duration(750)
                .attr("height", chart_height*chart_zoom)
                .attr("width", chart_width*chart_zoom);

        }

        var formatMinutes = function(d) {
                hours = Math.floor( d / 60 )
                minutes = Math.floor(d - (hours * 60))

                if(hours < 10) {
                    hours = "0" + hours
                }
                if(minutes < 10) {
                    minutes = "0" + minutes
                }

                return hours + ":" + minutes;
            };

        var margin = {top: 60, right: 30, bottom: 50, left: 60};
        var height = 150;
        var chart_height = height + margin.top + margin.bottom;

        var width = 300;
        var chart_width = width + margin.left + margin.right;

        var lengths = []

        var x = d3.scale.linear()
            .domain([0, d3.max(data)])
            .range([0, width]);

        // Generate a histogram using twenty uniformly-spaced bins.
        var data = d3.layout.histogram()
            .bins(x.ticks(20))(data);

        for(var i = 0; i < data.length; i ++) {
            lengths.push(data[i].length)
        }

        if(d3.max(data) != 0) {
            var zoom = height / d3.max(lengths);
        } else {
            var zoom = 1.0;
        }

        var y = d3.scale.linear()
            .domain([0, d3.max(data, function(d) { return d.y; })])
            .range([height, 0]);

        var chart = d3.select("#" + name)
            .attr("viewBox", "0 0 " + chart_width + " " + chart_height)
            .attr("width", chart_width)
            .attr("height", chart_height)
            .attr("preserveAspectRatio", "xMidYMin")
            .on("click", click);

        chart.append("g")
            .append("text")
            .attr("class", "title")
            .attr("transform", function(e) {
                return "translate( " + width + ",15 )";
            })
            .text(title);

        var bar = chart.selectAll(".bar")
            .data(data)
          .enter().append("g")
            .attr("class", "bar")
            .attr("transform", function(d) { return "translate(" + (+x(d.x) + +margin.left) + "," + (+y(d.y) + +margin.top) + ")"; })
            .on("mouseenter", function(d) {
                i = 0;
                size = d.length;

                while( size >= 1) {
                    size = size / 10;
                    i++;
                }
                var wdth = (i * 4) + 10;
                d3.select(d3.event.path[1]).select(".tool_tip")
                    .select("text")
                        .attr("transform", "translate( " + (margin.left - 5) + ", " + (height - (d.length * zoom) + +margin.top + 10) + " )" )
                        .attr("visibility", "visible")
                        .text(d.length);

                d3.select(d3.event.path[1]).select(".tool_tip")
                    .attr("width", wdth + "px")
                    .attr("height", "15px")
                    .select("rect")
                        .attr("transform", "translate( " + ((+margin.left) - wdth) + ", " + (height - (d.length * zoom) + +margin.top) + " )")
                        .attr("width", wdth + "px")
                        .attr("height", "15px")
                        .attr("fill","#ebd9b2");
            })
            .on("mouseleave", function(d) {
                d3.select(d3.event.path[1]).select(".tool_tip")
                    .select("text")
                        .attr("visibility", "hidden");

                d3.select(d3.event.path[1]).select(".tool_tip")
                    .select("rect")
                        .attr("width", "0")
                        .attr("height", "0")
                        .attr("fill","")
            });

        var bar_x;
        if(data[0] == undefined) {
            bar_x = 1;
        } else {
            bar_x = x(data[0].dx);
        }

        bar.append("rect")
            .attr("x", 1)
            .attr("width", bar_x - 1)
            .attr("height", function(d) { return height - y(d.y); });

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
            .tickFormat(formatMinutes);

        chart.append("g")
            .attr("class", "x axis")
            .attr("id", "x_" + name)
            .attr("transform", "translate( " + margin.left + "," + (+height + +margin.top) + ")")
            .call(xAxis);

        chart.append("g")
            .append("text")
                .attr("class", "ax_title")
                .attr("transform", function(e) {
                    var axis = d3.select("#x_" + name).node()
                    var left_pad = +margin.left + (axis.getBoundingClientRect().width/2) + 30;
                    var top_pad = +margin.top + height + axis.getBoundingClientRect().height + 10
                    var trans = "translate(" + left_pad + "," + top_pad + ")";

                    return trans;
                })
                .text("ETA - hrs:mins");

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left");

        chart.append("g")
            .attr("class", "y axis")
            .attr("id", ("y_" + name))
            .attr("transform", "translate( " + margin.left + "," + margin.top + ")")
            .call(yAxis);

        chart.append("g")
            .append("text")
                .attr("class", "ax_title")
                .attr("transform", function(e) {
                    var axis = d3.select("#y_" + name).node()
                    var left_pad = +margin.left - axis.getBoundingClientRect().width - 5;
                    var top_pad = +margin.top + (axis.getBoundingClientRect().height/2) - 30
                    var trans = "translate(" + left_pad + "," + top_pad + ")rotate(-90)";

                    return trans;
                })
                .text("Number of Jobs");

        chart.append("g")
            .attr("class", "tool_tip")
            .append("rect");
        chart.select(".tool_tip")
            .append("text");
    });
}
