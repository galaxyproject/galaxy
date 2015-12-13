#!/usr/bin/env nodejs

"use strict";

process.stdin.setEncoding('utf8');

var incoming = "";

process.stdin.on('readable', function() {
  var chunk = process.stdin.read();
    if (chunk !== null) {
        incoming += chunk;
    }
});

process.stdin.on('end', function() {
    var j = JSON.parse(incoming);
    var exp = ""

    if (j.script[0] == "{") {
        exp = "{return function()" + j.script + "();}";
    }
    else {
        exp = "{return " + j.script + ";}";
    }

    var fn = '"use strict";\n';

    if (j.engineConfig) {
        for (var index = 0; index < j.engineConfig.length; ++index) {
            fn += j.engineConfig[index] + "\n";
        }
    }

    fn += "var $job = " + JSON.stringify(j.job) + ";\n";
    fn += "var $self = " + JSON.stringify(j.context) + ";\n"

    fn += "var $runtime = " + JSON.stringify(j.runtime) + ";\n"
    fn += "var $tmpdir = " + JSON.stringify(j.tmpdir) + ";\n"
    fn += "var $outdir = " + JSON.stringify(j.outdir) + ";\n"


    fn += "(function()" + exp + ")()";

    process.stdout.write(JSON.stringify(require("vm").runInNewContext(fn, {})));
});
