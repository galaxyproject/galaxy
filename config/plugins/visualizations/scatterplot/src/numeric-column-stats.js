var numericColumnStats = function(data, keys) {
    var console = console || { debug: function() {} },
        stats = {};

    // precondition: keys is an array of keys accessible on each data in data
    if (!keys || !keys.length) {
        throw new Error("keys is a required parameter and must be an array:" + keys);
    }
    if (!data || !data.length) {
        return stats;
    }

    function parseVal(val) {
        if (val === null) {
            throw new Error("Null value");
        }
        val = Number(val);
        if (isNaN(val) || !isFinite(val)) {
            throw new Error("NaN or non-finite number");
        }
        return val;
    }

    // does this effect the data in the other thread?
    ["min", "max", "sum", "mean", "median", "count"].forEach(function(name, i) {
        stats[name] = new Array(keys.length);
    });

    var keyIndex = 0,
        separatedCols = new Array(keys.length);
    keys.forEach(function(key, keyIndex) {
        stats.min[keyIndex] = 0;
        stats.max[keyIndex] = 0;
        stats.sum[keyIndex] = 0;
        separatedCols[keyIndex] = [];
    });

    // work backwards to prevent co-modification problems while splitting up data into columns
    for (var dataIndex = data.length - 1; dataIndex >= 0; dataIndex -= 1) {
        var datum = data.pop(dataIndex);

        for (keyIndex = 0; keyIndex < keys.length; keyIndex += 1) {
            var key = keys[keyIndex],
                datumColVal = datum[key];

            try {
                //NOTE: parsing value as number
                datumColVal = parseVal(datumColVal);
            } catch (e) {
                continue;
            }

            // separate the columns
            separatedCols[keyIndex].unshift(datumColVal);
            // get the other stats
            stats.min[keyIndex] = Math.min(stats.min[keyIndex], datumColVal);
            stats.max[keyIndex] = Math.max(stats.max[keyIndex], datumColVal);
            stats.sum[keyIndex] += datumColVal;
        }
    }

    // get counts, mean, median
    function comparator(a, b) {
        if (a < b) {
            return -1;
        }
        if (a < b) {
            return 1;
        }
        return 0;
    }

    for (keyIndex = 0; keyIndex < keys.length; keyIndex += 1) {
        var count = separatedCols[keyIndex].length,
            sum = stats.sum[keyIndex];
        stats.count[keyIndex] = count;
        stats.mean[keyIndex] = sum / count;

        // sort columns for median
        separatedCols[keyIndex].sort(comparator);

        // odd count -> straight forward median
        var middleDataIndex = Math.floor(count / 2);
        if (count % 2 === 1) {
            stats.median[keyIndex] = separatedCols[keyIndex][middleDataIndex];
        } else {
            var middleValA = separatedCols[keyIndex][middleDataIndex],
                middleValB = separatedCols[keyIndex][middleDataIndex + 1];
            stats.median[keyIndex] = (middleValA + middleValB) / 2;
        }
    }
    return stats;
};
