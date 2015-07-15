<%inherit file="/base.mako"/>
<%namespace file="/message.mako" import="render_msg" />

%if message:
    ${render_msg( message, 'done' )}
%endif

<!--run_stats.mako-->
<style>
.chart rect {
    fill: steelblue;
}

.chart text {
    fill: white;
    font: 7px sans-serif;
    text-anchor: end;
}

.tick text {
    fill: black;
    font-family: Arial, sans-serif;
    font-size: 7px;
}

.axis path, .axis line {
    fill: none;
    stroke: #000;
    shape-rendering: crispEdges;
}

.chart .title {
    fill: black;
    font-size: 15px;
    font-family: "Lucida Grande",verdana,arial,helvetica,sans-serif;
    font-weight: 800;
    line-height: 1.1;
}

.chart .ax_title {
    fill: black;
}

.hr_container {
    position: relative;
    display: inline-block;
    vertical-align: top;
}

.dy_container {
    position: relative;
    display: inline-block;
    vertical-align: top;
}

.charts {
    margin-top: 10px;
    margin-left: 0;
    margin-right: 0;
    text-align: center;
    position: relative;
    display: block;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap
}

.trim {
    position:relative;
    height:15px;
    top: 55px;
    background: #ebd9b2;
    color: #000;
    border-top: solid #d6b161 1px;
    border-bottom: solid #d6b161 1px;
}
</style>

<script type="text/javascript">
function type(d) {
    d = +d; // coerce to number
    return d;
}

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

function create_chart( inp_data, name, time, title ) {
    require( ["d3"], function (e) {
        var data = inp_data;
        var margin = {top: 60, right: 30, bottom: 50, left: 60};
        function click(d) {
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
                    .attr("height", chart_height*1.5)
                    .attr("width", chart_width*1.5);
        }

        var height = 150;
        if(d3.max(data) != 0) {
            var zoom = height / d3.max(data);
        } else {
            var zoom = 1.0;
        }
        var chart_height = height + margin.top + margin.bottom;
        $(".charts").css("height", chart_height*1.55);

        var width = 300;
        var barWidth = width / data.length;
        var chart_width = width + margin.left + margin.right;

        var y = d3.scale.linear()
            .range([height, 0]);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .tickFormat( function(d) { return d3.round( d*d3.max(data), 1 ) });


        if (time == "hours") {
            var x = d3.time.scale()
                .domain([new Date(), date_by_subtracting_days(new Date(), 1)])
                .rangeRound([0, width]);

            var xAxis = d3.svg.axis()
                .scale(x)
                .tickFormat(d3.time.format('%b %d %H'))
                .ticks(d3.time.hours, 1)
                .orient("bottom")
                .tickSize(0)
                .tickPadding(8);
        } else if (time == "days") {
            var x = d3.time.scale()
                .domain([new Date(), date_by_subtracting_days(new Date(), 30)])
                .rangeRound([0, width]);

            var xAxis = d3.svg.axis()
                .scale(x)
                .tickFormat(d3.time.format('%b %d'))
                .ticks(d3.time.days, 1)
                .orient("bottom")
                .tickSize(0)
                .tickPadding(8);
        }

        var chart = d3.select("#" + name)
            .attr("width", function(d) {
                if(name == "jc_hr_chart" || name == "jc_dy_chart") {
                    wdth = chart_width * 1.5;
                } else {
                    wdth = chart_width;
                }

                return wdth;
            })
            .attr("height", function(d) {
                if(name == "jc_hr_chart" || name == "jc_dy_chart") {
                    hght = chart_height * 1.5;
                } else {
                    hght = chart_height;
                }

                return hght;
            })
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
                    d3.select(d3.event.path[1]).select(".tool_tip")
                        .select("text")
                            .attr("transform", "translate( 45, " + ((height - (d * zoom))  + +margin.top + 10) + " )" )
                            .attr("visibility", "visible")
                            .text(d);

                    d3.select(d3.event.path[1]).select(".tool_tip")
                        .attr("width", "40px")
                        .attr("height", "15px")
                        .select("rect")
                            .attr("transform", "translate( 20, " + ((height - (d * zoom)) + +margin.top) + " )" )
                            .attr("width", "40px")
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
            .attr("text-anchor", "middle")
            .attr("transform", function(e) {
                return "translate( " + width + ",15 )";
            })
            .text(title);

        chart.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(" + margin.left + "," + (+height + +margin.top )+ ")")
            .call(xAxis)
                .selectAll("text")
                .attr("transform", function() {
                    if(time == "hours") {
                        return "translate( " + (-(barWidth/2) - 2) + ", 17)rotate(-90)";
                    } else if(time == "days") {
                        return "translate( " + (-(barWidth/2) - 7) + ", 13)rotate(-90)";
                    }
                });

        chart.append("g")
            .append("text")
                .attr("class", "ax_title")
                .attr("transform", function(e) {
                    var trans = "";
                    if(time == "hours") {
                        trans = "translate(" + (+margin.left/2) + "," + margin.top + ")rotate(-90)";
                    } else if(time == "days") {
                        trans = "translate(" + (+margin.left/4) + "," + margin.top + ")rotate(-90)";
                    }
                    return trans;
                })
                .text("Number of Jobs");

        chart.append("g")
            .append("text")
                .attr("class", "ax_title")
                .attr("transform", function(e) {
                    var trans = "";
                    if(time == "hours") {
                        trans = trans = "translate(" + (+margin.left*2 + 20) + "," + (+chart_height - 7) + ")";
                    } else if(time == "days") {
                        trans = "translate(" + (+margin.left*2 ) + "," + (+chart_height - 7) + ")";
                    }
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

        chart.append("g")
            .attr("class", "y axis")
            .attr("transform", "translate( " + margin.left + "," + margin.top + ")")
            .call(yAxis);
        bar.append("rect")
            .attr("y", function(d) { return height - (d * zoom); })
            .attr("height", function(d) { return (d * zoom); })
            .attr("width", barWidth - 1);

        chart.append("g")
            .attr("class", "tool_tip")
            .append("rect");
        chart.select(".tool_tip")
            .append("text");
    });
}

function create_histogram( inp_data, name, time, title ) {
    require( ["d3"], function (e) {
        //inp_data is an array of numbers that are the amount of minutes per run
        var data = inp_data;
        console.log(d3.max(inp_data))
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
                .attr("height", chart_height*1.5)
                .attr("width", chart_width*1.5);

        }

        var formatMinutes = function(d) {
                hours = Math.floor( d / 60 )
                minutes = d - (hours * 60)

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
        $(".charts").css("height", chart_height*1.55);

        var width = 300;
        var chart_width = width + margin.left + margin.right;

        var x = d3.scale.linear()
            .domain([0, d3.max(data)])
            .range([0, width]);

        // Generate a histogram using twenty uniformly-spaced bins.
        var data = d3.layout.histogram()
            .bins(x.ticks(20))
            (data);

        var y = d3.scale.linear()
            .domain([0, d3.max(data, function(d) { return d.y; })])
            .range([height, 0]);

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom")
            .tickFormat(formatMinutes);

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

                while( size > 1) {
                    size = size / 10;
                    i++;
                }
                var wdth = (i * 4) + 10;
                d3.select(d3.event.path[1]).select(".tool_tip")
                    .select("text")
                        .attr("transform", "translate( " + (margin.left - 5) + ", " + (height + +margin.top - 5) + " )" )
                        .attr("visibility", "visible")
                        .text(d.length);

                d3.select(d3.event.path[1]).select(".tool_tip")
                    .attr("width", wdth + "px")
                    .attr("height", "15px")
                    .select("rect")
                        .attr("transform", "translate( " + ((+margin.left) - wdth) + ", " + (height + +margin.top - 15) + " )")
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

        chart.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate( " + margin.left + "," + (+height + +margin.top) + ")")
            .call(xAxis);

        chart.append("g")
            .attr("class", "tool_tip")
            .append("rect");
        chart.select(".tool_tip")
            .append("text");
    });
}
    create_chart( ${jf_hr_data}, "jf_hr_chart", "hours", "Jobs Finished per Hour" );
    create_chart( ${jf_dy_data}, "jf_dy_chart", "days", "Jobs Finished per Day" );
    create_chart( ${jc_hr_data}, "jc_hr_chart", "hours", "Jobs Created per Hour" );
    create_chart( ${jc_dy_data}, "jc_dy_chart", "days", "Jobs Created per Day" );
    create_histogram( ${et_hr_data}, "et_hr_chart", "delta-hours", "Job Run Times (past day)" );
    create_histogram( ${et_dy_data}, "et_dy_chart", "days", "Job Run Time (past 3 days)" );
    </script>

<div class="toolForm">
    <div class="trim" id="tr_hr"></div>
    <div class="charts">
        <div class="hr_container">
            <svg class="chart hr" id="jf_hr_chart"></svg>
        </div>
        <div class="hr_container">
            <svg class="chart hr" id="jc_hr_chart"></svg>
        </div>
        <div class="hr_container">
            <svg class="chart hr" id="et_hr_chart"></svg>
        </div>
    </div>
    <div class="trim" id="tr_dy"></div>
    <div class="charts">
        <div class="dy_container">
            <svg class="chart dy" id="jf_dy_chart"></svg>
        </div>
        <div class="dy_container">
            <svg class="chart dy" id="jc_dy_chart"></svg>
        </div>
        <div class="dy_container">
            <svg class="chart dy" id="et_dy_chart"></svg>
        </div>
    </div>
</div>
<!--run_stats.mako-->