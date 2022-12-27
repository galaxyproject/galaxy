import $ from "jquery";
import * as d3 from "d3";

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

function date_by_subtracting_hours(date, hours) {
    return new Date(
        date.getFullYear(),
        date.getMonth(),
        date.getDate(),
        date.getHours() - hours,
        date.getMinutes(),
        date.getSeconds(),
        date.getMilliseconds()
    );
}

// Gets the utc time without minutes and seconds
function get_utc_time_hours() {
    var date = new Date();
    return new Date(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate(), date.getUTCHours(), 0, 0);
}

// This is commented out until we make Reports more responsive.
// setTimeout(refresh, 60000); //1 minute = 60000 ms

export function create_chart(inp_data, name, time, title) {
    // Initialize starting variables
    var data = inp_data;

    var hours_array = [];
    var now = get_utc_time_hours();
    var i;
    for (i = 0; i < 24; i++) {
        hours_array.push(date_by_subtracting_hours(now, i));
    }

    var days_array = [];
    for (i = 0; i < 30; i++) {
        days_array.push(date_by_subtracting_days(now, i));
    }

    var margin = { top: 60, right: 30, bottom: 50, left: 60 };
    var width = 300;
    var barWidth = 0;
    if (time == "hours") {
        barWidth = width / 24;
    } else if (time == "days") {
        barWidth = width / 30;
    }
    var chart_width = width + margin.left + margin.right;

    var chart_zoom = 1.75;
    var height = 150;
    var zoom;
    if (d3.max(data) !== 0) {
        zoom = height / d3.max(data);
    } else {
        zoom = 1.0;
    }
    var chart_height = height + margin.top + margin.bottom;

    // Function for zooming in and out of charts
    function click() {
        var classes = d3.select(this).attr("class");
        classes = classes.split(" ");
        d3.selectAll(`.${classes[0]}`)
            .filter(`.${classes[1]}`)
            .style("cursor", "zoom-in")
            .transition()
            .duration(750)
            .attr("height", chart_height)
            .attr("width", chart_width);

        d3.select(this)
            .style("cursor", "default")
            .transition()
            .duration(750)
            .attr("height", chart_height * chart_zoom)
            .attr("width", chart_width * chart_zoom);
    }

    // Initialize all chart containers to have the correct height
    $(".charts").css("height", chart_height * chart_zoom);

    // Create the chart object
    var chart = d3
        .select(`#${name}`)
        .attr("width", chart_width)
        .attr("height", chart_height)
        .attr("preserveAspectRatio", "xMidYMin")
        .attr("viewBox", `0 0 ${chart_width} ${chart_height}`)
        .on("click", click);

    // Create bars on the chart and assosciate data with it
    var bar = chart
        .selectAll("g")
        .data(data)
        .enter()
        .append("g")
        .attr("transform", (d, i) => {
            // Place the bar in the correct place
            var curr_margin = margin.left;
            curr_margin += +(i * barWidth);
            return `translate(${curr_margin},${margin.top})`;
        })
        .on("mouseenter", (d) => {
            // Show tool tip
            var i = 1;
            var size = d;

            while (size >= 10) {
                size = size / 10;
                i++;
            }

            var wdth = i * 4 + 10;
            d3.select(d.target.parentElement)
                .select(".tool_tip")
                .select("text")
                .attr("transform", `translate( ${margin.left - 5}, ${height - d * zoom + margin.top + 10} )`)
                .attr("visibility", "visible")
                .text(d);

            d3.select(d.target.parentElement)
                .select(".tool_tip")
                .attr("width", `${wdth}px`)
                .attr("height", "15px")
                .select("rect")
                .attr("transform", `translate( ${margin.left - wdth}, ${height - d * zoom + margin.top} )`)
                .attr("width", `${wdth}px`)
                .attr("height", "15px")
                .attr("fill", "#ebd9b2");
        })
        .on("mouseleave", (d) => {
            // Remove tool tip
            d3.select(d.target.parentElement).select(".tool_tip").select("text").attr("visibility", "hidden");

            d3.select(d.target.parentElement)
                .select(".tool_tip")
                .select("rect")
                .attr("width", "0")
                .attr("height", "0")
                .attr("fill", "")
                .text(d);
        });

    // Add a title to the chart
    chart
        .append("g")
        .append("text")
        .attr("class", "title")
        .attr("text-anchor", "end")
        .attr("transform", () => `translate( ${width},15 )`)
        .text(title);

    // Add an x axis line to the chart
    chart
        .append("g")
        .attr("class", "axis")
        .append("path")
        .attr("class", "x")
        .attr("d", () => {
            var m_x = margin.left;
            var m_y = margin.top + height;
            var l_x = m_x + width;
            return `M${m_x} ${m_y} L ${l_x} ${m_y}`;
        });

    // Declare how high the y axis goes
    var y = d3.curveLinear().range([height, 0]);

    // Create a yAxis object
    var yAxis = d3.svg
        .axis()
        .scale(y)
        .orient("left")
        .tickFormat((d) => Math.round(d * d3.max(data), 0));

    // Put the y axis on the chart
    chart
        .append("g")
        .attr("class", "y axis")
        .attr("id", `y_${name}`)
        .attr("text-anchor", "end")
        .attr("transform", `translate( ${margin.left},${margin.top})`)
        .call(yAxis)
        .select(".domain");

    // Put a title for y axis on chart
    chart
        .append("g")
        .append("text")
        .attr("class", "ax_title")
        .attr("transform", () => {
            var axis = d3.select(`#y_${name}`).node();
            var left_pad = margin.left - axis.getBoundingClientRect().width - 5;
            var top_pad = margin.top + axis.getBoundingClientRect().height / 2 - 30;
            return `translate(${left_pad},${top_pad})rotate(-90)`;
        })
        .text("Number of Jobs");

    // Add color to the chart's bars
    bar.append("rect")
        .attr("y", (d) => height - d * zoom)
        .attr("height", (d) => d * zoom)
        .attr("width", barWidth - 1);

    var first = false;

    // Append x axis
    if (time == "hours") {
        // Append hour lines
        bar.append("line")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", 0)
            .attr("y2", 3)
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .attr("pointer-events", "none")
            .attr("transform", () => `translate( ${barWidth / 2}, ${height})`);

        // Append hour numbers
        bar.append("text")
            .attr("fill", "rgb(0,0,0)")
            .attr("transform", `translate( 10, ${height + 10} )`)
            .text((d, i) => {
                var time = "0000";

                if (hours_array[i].getHours() < 10) {
                    time = `0${String(hours_array[i].getHours())}`;
                } else {
                    time = hours_array[i].getHours();
                }

                return time;
            });

        // Append day lines
        var curr_day = "";
        first = false;
        bar.append("line")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", 0)
            .attr("y2", (d, i) => {
                var _y2 = 0;

                if (hours_array[i].getDate() != curr_day) {
                    if (!first) {
                        _y2 = 27;
                        first = true;
                    } else {
                        _y2 = 20;
                    }

                    curr_day = hours_array[i].getDate();
                }

                return _y2;
            })
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .attr("pointer-events", "none")
            .attr("transform", () => `translate( 0, ${height})`);

        // Append day numbers
        curr_day = "";
        var curr_day_text = "";
        first = false;
        bar.append("text")
            .attr("fill", "rgb(0,0,0)")
            .attr("pointer-events", "none")
            .text((d, i) => {
                var time = "";
                var locale = "en-us";

                if (hours_array[i].getDate() != curr_day_text) {
                    time = String(hours_array[i].toLocaleString(locale, { month: "long" }));
                    time += ` ${String(hours_array[i].getDate())}`;

                    curr_day_text = hours_array[i].getDate();
                }

                return time;
            })
            .attr("transform", function (d, i) {
                var text_height = height;
                var this_width = d3.select(this).node().getBBox().width;

                if (hours_array[i].getDate() != curr_day) {
                    if (!first) {
                        text_height += 26;
                        first = true;
                    } else {
                        text_height += 18;
                    }

                    curr_day = hours_array[i].getDate();
                }

                return `translate( ${this_width + 2}, ${text_height} )`;
            });
    } else if (time == "days") {
        // Append day lines
        bar.append("line")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", 0)
            .attr("y2", 3)
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .attr("pointer-events", "none")
            .attr("transform", () => `translate( ${barWidth / 2}, ${height})`);

        // Append day numbers
        bar.append("text")
            .attr("fill", "rgb(0,0,0)")
            .attr("transform", `translate( 9, ${height + 10} )`)
            .text((d, i) => {
                var time = "0000";

                if (days_array[i].getDate() < 10) {
                    time = `0${String(days_array[i].getDate())}`;
                } else {
                    time = days_array[i].getDate();
                }

                return time;
            });

        // Append month lines
        var curr_month = "";
        first = false;
        bar.append("line")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", 0)
            .attr("y2", (d, i) => {
                var _y2 = 0;

                if (days_array[i].getMonth() != curr_month) {
                    if (!first) {
                        _y2 = 27;
                        first = true;
                    } else {
                        _y2 = 20;
                    }

                    curr_month = days_array[i].getMonth();
                }

                return _y2;
            })
            .attr("stroke", "black")
            .attr("stroke-width", 1)
            .attr("pointer-events", "none")
            .attr("transform", () => `translate( 0, ${height})`);

        // Append month numbers
        curr_month = "";
        var curr_month_text = "";
        first = false;
        bar.append("text")
            .attr("fill", "rgb(0,100,0)")
            .attr("pointer-events", "none")
            .text((d, i) => {
                var time = "";
                var locale = "en-us";

                if (days_array[i].getMonth() != curr_month_text) {
                    time = String(days_array[i].toLocaleString(locale, { month: "long" }));
                    time += ` ${String(days_array[i].getFullYear())}`;

                    curr_month_text = days_array[i].getMonth();
                }

                return time;
            })
            .attr("transform", function (d, i) {
                var text_height = height;
                var this_width = d3.select(this).node().getBBox().width;

                if (days_array[i].getMonth() != curr_month) {
                    if (!first) {
                        text_height += 26;
                        first = true;
                    } else {
                        text_height += 18;
                    }

                    curr_month = days_array[i].getMonth();
                }

                return `translate( ${this_width + 2}, ${text_height} )`;
            });
    }

    // Put an invisible tool tip on the chart
    chart.append("g").attr("class", "tool_tip").append("rect");
    chart.select(".tool_tip").append("text");

    // Initialize initial zoomed charts
    if (name == "jc_dy_chart" || name == "jc_hr_chart") {
        d3.select(`#${name}`)
            .attr("height", chart_height * chart_zoom)
            .attr("width", chart_width * chart_zoom)
            .style("cursor", "default");
    }
}

//============================================================================================================

export function create_histogram(inp_data, name, title) {
    // Initialize initial variables
    // inp_data is an array of numbers that are the amount of minutes per run
    var data = inp_data;

    var chart_zoom = 1.75;
    var margin = { top: 60, right: 30, bottom: 50, left: 60 };

    var height = 150;
    var chart_height = height + margin.top + margin.bottom;

    var width = 300;
    var chart_width = width + margin.left + margin.right;

    // Cereate x axis metadata
    // Used for x axis, histogram creation, and bar initialization
    var x = d3
        .curveLinear()
        .domain([0, d3.max(data)])
        .range([0, width]);

    // Generate a histogram using twenty uniformly-spaced bins.
    data = d3.histogram().bins(x.ticks(20))(data);

    // Create an array of the sizes of the bars
    var lengths = [];
    for (var i = 0; i < data.length; i++) {
        lengths.push(data[i].length);
    }

    var zoom;
    // Find the amount needed to magnify the bars
    if (d3.max(data) !== 0) {
        zoom = height / d3.max(lengths);
    } else {
        zoom = 1.0;
    }

    // Create y axis metadata
    // Used for y axis and bar initialization
    var y = d3
        .curveLinear()
        .domain([0, d3.max(data, (d) => d.y)])
        .range([height, 0]);

    // Function for zooming in and out of charts
    function click() {
        var classes = d3.select(this).attr("class");
        classes = classes.split(" ");
        d3.selectAll(`.${classes[0]}`)
            .filter(`.${classes[1]}`)
            .style("cursor", "zoom-in")
            .transition()
            .duration(750)
            .attr("height", chart_height)
            .attr("width", chart_width);

        d3.select(this)
            .style("cursor", "default")
            .transition()
            .duration(750)
            .attr("height", chart_height * chart_zoom)
            .attr("width", chart_width * chart_zoom);
    }

    // Formatter for x axis times (converting minutes to HH:MM).
    var formatMinutes = (d) => {
        var hours = Math.floor(d / 60);
        var minutes = Math.floor(d - hours * 60);

        if (hours < 10) {
            hours = `0${hours}`;
        }
        if (minutes < 10) {
            minutes = `0${minutes}`;
        }

        return `${hours}:${minutes}`;
    };

    // Create a chart object
    var chart = d3
        .select(`#${name}`)
        .attr("viewBox", `0 0 ${chart_width} ${chart_height}`)
        .attr("width", chart_width)
        .attr("height", chart_height)
        .attr("preserveAspectRatio", "xMidYMin")
        .on("click", click);

    // Put title on chart
    chart
        .append("g")
        .append("text")
        .attr("class", "title")
        .attr("transform", () => `translate( ${width},15 )`)
        .text(title);

    // Put bars on chart
    var bar = chart
        .selectAll(".bar")
        .data(data)
        .enter()
        .append("g")
        .attr("class", "bar")
        .attr("transform", (d) => `translate(${+x(d.x) + margin.left},${+y(d.y) + margin.top})`)
        .on("mouseenter", (d) => {
            // Show tool tip
            var i = 0;

            var size = d.length;

            while (size >= 1) {
                size = size / 10;
                i++;
            }
            var wdth = i * 4 + 10;
            d3.select(d.target.parentElement)
                .select(".tool_tip")
                .select("text")
                .attr("transform", `translate( ${margin.left - 5}, ${height - d.length * zoom + margin.top + 10} )`)
                .attr("visibility", "visible")
                .text(d.length);

            d3.select(d.target.parentElement)
                .select(".tool_tip")
                .attr("width", `${wdth}px`)
                .attr("height", "15px")
                .select("rect")
                .attr("transform", `translate( ${margin.left - wdth}, ${height - d.length * zoom + margin.top} )`)
                .attr("width", `${wdth}px`)
                .attr("height", "15px")
                .attr("fill", "#ebd9b2");
        })
        .on("mouseleave", (d) => {
            // Remove tool tip
            d3.select(d.target.parentElement).select(".tool_tip").select("text").attr("visibility", "hidden");

            d3.select(d.target.parentElement)
                .select(".tool_tip")
                .select("rect")
                .attr("width", "0")
                .attr("height", "0")
                .attr("fill", "");
        });

    // Create bar width
    var bar_x;
    if (data[0] === undefined) {
        bar_x = 1;
    } else {
        bar_x = x(data[0].dx);
    }

    // Add color to bar
    bar.append("rect")
        .attr("x", 1)
        .attr("width", bar_x - 1)
        .attr("height", (d) => height - y(d.y));

    // Create x axis
    var xAxis = d3.svg.axis().scale(x).orient("bottom").tickFormat(formatMinutes);

    // Add x axis to chart
    chart
        .append("g")
        .attr("class", "x axis")
        .attr("id", `x_${name}`)
        .attr("transform", `translate( ${margin.left},${+height + margin.top})`)
        .call(xAxis);

    // Add a title to the x axis
    chart
        .append("g")
        .append("text")
        .attr("class", "ax_title")
        .attr("transform", () => {
            var axis = d3.select(`#x_${name}`).node();
            var left_pad = margin.left + axis.getBoundingClientRect().width / 2 + 30;
            var top_pad = margin.top + height + axis.getBoundingClientRect().height + 10;
            return `translate(${left_pad},${top_pad})`;
        })
        .text("ETA - hrs:mins");

    // Create y axis
    var yAxis = d3.svg.axis().scale(y).orient("left");

    // Add y axis to chart
    chart
        .append("g")
        .attr("class", "y axis")
        .attr("id", `y_${name}`)
        .attr("transform", `translate( ${margin.left},${margin.top})`)
        .call(yAxis);

    // Add a title to the y axis
    chart
        .append("g")
        .append("text")
        .attr("class", "ax_title")
        .attr("transform", () => {
            var axis = d3.select(`#y_${name}`).node();
            var left_pad = margin.left - axis.getBoundingClientRect().width - 5;
            var top_pad = margin.top + axis.getBoundingClientRect().height / 2 - 30;
            return `translate(${left_pad},${top_pad})rotate(-90)`;
        })
        .text("Number of Jobs");

    // Put an invisible tool tip on the chart
    chart.append("g").attr("class", "tool_tip").append("rect");
    chart.select(".tool_tip").append("text");
}
