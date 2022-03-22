import "./js/publicPath";
import "./css/jquery-ui.min.css";
import "./css/lorikeet.css";
import "./css/datatables.min.css";
import "./css/msi.css";
import "./css/app.css";
import "./css/igv.css";
import "bootstrap/dist/css/bootstrap.css";

import "script-loader!./js/jquery.min.js";
import "script-loader!./js/jquery-ui.min.js";

import "bootstrap";
import "script-loader!./js/popper.min.js";
import "script-loader!./js/plotly-latest.min.js";
import "script-loader!./js/datatables.min.js";
import "script-loader!./js/d3.min.js";
import "script-loader!../node_modules/igv/dist/igv.min.js";
import "script-loader!./js/msms_graphs.js";

/**
 * Handles modification provisioning.
 * Uses chained Promises to efficiently generate all modifications in memory.
 */
var PeptideModifications = (function (pm) {
    //[iTRAQ4plex]RTLNISHNLH{S:Phospho}LLPEVSPM{K:iTRAQ4plex}NR
    //Returns an html formatted sequence including modifications for a list of peptide ids found in pepIDs
    pm.htmlFormatSequences = function (objs) {
        //pepIDs
        objs.data.forEach(function (cv) {
            let s = undefined;
            if (cv['"Sequence"']) {
                s = cv['"Sequence"'];
            } else {
                s = cv['"PEPTIDE_ID"'];
            }
            s = s.replace(
                /{([A-Z]):(.+?)}/g,
                '<span class="aa_mod" data-toggle="tooltip" data-placement="top" title="$2">$1</span>'
            );
            s = s.replace(
                /\[(\S+?)\]/g,
                '<span class="aa_mod" data-toggle="tooltip" data-placement="top" title="Terminal Mod $1">&bull;</span>'
            );

            //For older versions
            s = s.replace(
                /^([A-Z]){(.+?)}/g,
                '<span class="aa_mod" data-toggle="tooltip" data-placement="top" title="Terminal Mod $2">&bull;</span>$1'
            );
            s = s.replace(
                /([A-Z]){(.+?)}/g,
                '<span class="aa_mod" data-toggle="tooltip" data-placement="top" title="$2">$1</span>'
            );

            //For the olders version
            cv['"Sequence"'] = s;
        });
        return objs;
    };
    return pm;
})(PeptideModifications || {}); // eslint-disable-line no-use-before-define

/**
 * Handles score summary information. Scores are dynamic and can be quite numerous.
 *
 */
var ScoreSummary = (function (sSum) {
    sSum.scoreSummary = {};
    sSum.rankedScores = null;

    //Generates list of scores ranked by pct of scores present.
    sSum.getRankedScores = function () {
        var scoreArray = [];
        Object.keys(sSum.scoreSummary).forEach(function (cv) {
            scoreArray.push([cv, sSum.scoreSummary[cv].pct_scores_present]);
        });
        scoreArray.sort(function (a, b) {
            return b[1] - a[1];
        });
        sSum.rankedScores = scoreArray;
        sSum.publish("RankedScoresAvailable", sSum.rankedScores);
    };

    sSum.generateScores = function () {
        var q = "SELECT score_summary.* from score_summary";
        var url =
            sSum.href +
            "/api/datasets/" +
            sSum.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        var self = this;
        $.get(url + encodeURIComponent(q), function (data) {
            var scoreNames;
            data.data.forEach(function (cv, idx) {
                var obj = {};
                if (idx === 0) {
                    scoreNames = cv;
                } else {
                    for (var i = 0; i < scoreNames.length; i++) {
                        obj[scoreNames[i]] = cv[i];
                    }
                    self.scoreSummary[cv[scoreNames.indexOf("score_name")]] = obj;
                }
            });
            sSum.publish("ScoreSummaryComplete", sSum.scoreSummary);
        });
    };

    sSum.init = function (confObj) {
        sSum.href = confObj.href;
        sSum.datasetID = confObj.datasetID;
        sSum.generateScores();
        sSum.subscribe("RequestRankedScores", function () {
            if (sSum.rankedScores) {
                sSum.publish("RankedScoresAvailable", sSum.rankedScores);
            } else {
                sSum.getRankedScores();
            }
        });
    };

    return sSum;
})(ScoreSummary || {}); // eslint-disable-line no-use-before-define

/**
 * Object for building AJAX server-side data providers to a datatable
 *
 * confObj.baseQuery is an object:
 *  An example:
 * {
 *  SELECT: 'pe.Peptide_pkid, p.sequence, COUNT(DISTINCT(pe.DBSequence_pkid)) AS ProteinCount, COUNT(DISTINCT(pe.SpectrumIdentification_pkid)) AS SpectralCount',
 *  FROM: 'PeptideEvidence pe, Peptide p',
 *  WHERE: 'pe.Peptide_pkid = p.pkid',
 *  GROUPBY: 'pe.Peptide_pkid'
 * }
 *
 * confObj.rowIDField indicates that the SQL field named should be the key to the
 * data row. In gerneral this will be a id field. If present, the field will be marked
 * as non-visible OPTIONAL
 */
function AjaxDataProvider(confObj) {
    // eslint-disable-line no-unused-vars
    var self = this;

    this.baseQuery = confObj.baseQuery;
    this.href = confObj.href;
    this.historyID = confObj.historyID;
    this.datasetID = confObj.datasetID;
    this.rowIDField = confObj.rowIDField;
    this.columnNames = confObj.columnNames;
    this.searchColumn = confObj.searchColumn;
    this.searchTable = confObj.searchTable;
    this.tableDivID = confObj.tableDivID;
    this.filtered = false;
    this.customSQL = confObj.customSQL;
    this.initCompleteCB = confObj.callBackFN || function () {};

    this.scoreSummary = confObj.scoreSummary || false;

    this.sequenceFormatter = confObj.sequenceFormatter || null;

    this.url =
        this.href + "/api/datasets/" + this.datasetID + "?data_type=raw_data&provider=sqlite-table&headers=True&query=";

    this.recordsTotal = null;
    this.recordsFiltered = null;
    this.scoresByType = {};

    //Need to get score datatypes from the SQLite table
    (function () {
        var q = "SELECT score_summary.score_name, score_summary.score_type FROM score_summary";
        var s = self;
        $.get(self.url + encodeURIComponent(q), function (data) {
            data.data.forEach(function (cv) {
                if (!(cv[1] in s.scoresByType)) {
                    s.scoresByType[cv[1]] = [];
                }
                s.scoresByType[cv[1]].push(cv[0]);
            });
        });
    })();

    this.buildInClause = function (searchStr) {
        var rStr = " AND " + this.searchColumn + " IN (";

        rStr += searchStr + ")";

        return rStr;
    };

    this.buildLikeClause = function (searchStr) {
        let rx = RegExp(/(LIKE \"%[A-Z]*%\")/g);
        let matches = searchStr.match(rx);
        let rStr = " AND ";
        let colName = this.searchColumn;

        matches.forEach(function (m) {
            rStr += colName + " " + m + " OR ";
        });
        rStr = rStr.slice(0, rStr.lastIndexOf(" OR "));
        return rStr;
    };

    //---------------------------------------------------------------- Functions
    this.buildBaseQuery = function (searchReq) {
        var rStr = null;

        if (this.customSQL) {
            rStr = this.customSQL;
        } else {
            rStr = "SELECT " + this.baseQuery.SELECT + " FROM " + this.baseQuery.FROM;
            rStr += this.baseQuery.WHERE ? " WHERE " + this.baseQuery.WHERE : "";
        }

        // Search value can be multiple values within a string.
        if (searchReq.value) {
            if (searchReq.value.indexOf("%") > -1) {
                rStr += this.buildLikeClause(searchReq.value);
            } else {
                rStr += this.buildInClause(searchReq.value);
            }
        }

        if (!this.customSQL) {
            rStr += this.baseQuery.GROUPBY ? " GROUP BY " + this.baseQuery.GROUPBY : "";
        }

        return rStr;
    };

    this.getTotalRecordCount = function (callParms, callbackFN, enclState) {
        var sStr = this.buildBaseQuery(callParms.search);
        var finalFn = this.queryData;
        var parms = callParms;
        var dFn = callbackFN;
        var callingState = enclState;
        $.get(this.url + encodeURIComponent("SELECT COUNT(*) FROM (" + sStr + ")"), function (data) {
            callingState.recordsTotal = data.data[1][0];
            callingState.recordsFiltered = callingState.recordsTotal;
            finalFn(parms, dFn, callingState);
        });
    }.bind(this);

    this.getFilteredRecordCount = function (callParms, callbackFN, enclState) {
        var sStr = this.buildBaseQuery(callParms.search);
        sStr = "SELECT COUNT(*) FROM (" + sStr + ")";
        var nextFN = this.queryData;
        var parms = callParms;
        var destFN = callbackFN;
        var callingState = enclState;
        $.get(this.url + encodeURIComponent(sStr), function (data) {
            callingState.recordsFiltered = data.data[1][0];
            nextFN(parms, destFN, callingState);
        });
    };

    //Returns column definitions for the datatable.
    this.getColumnNames = function () {
        var rValue = this.columnNames;

        if (this.rowIDField) {
            rValue.forEach(
                function (cv) {
                    if (cv.title === this.rowIDField) {
                        cv.visible = false;
                    }
                }.bind(this)
            );
        }
        return rValue;
    };

    // Helper function for odering based on table request.
    // {column: 2, dir: "DESC"}
    this.orderFunction = function (orderArray) {
        var orderStr = "";

        orderArray.forEach(
            function (cv) {
                var isCast = false;
                var orderColName = this.columnNames[cv.column].title;
                this.scoresByType.REAL.forEach(function (t) {
                    if (orderColName === t) {
                        isCast = true;
                    }
                });
                if (isCast) {
                    orderStr += " ORDER BY CAST(" + this.columnNames[cv.column].data + " AS REAL) " + cv.dir + " ";
                } else {
                    orderStr += " ORDER BY " + this.columnNames[cv.column].data + " " + cv.dir + " ";
                }
            }.bind(this)
        );

        return orderStr;
    };

    this.queryData = function (callParms, callbackFN, enclState) {
        var self = enclState;
        var sqlStatement = self.buildBaseQuery(callParms.search);
        var requestParms = callParms;
        var rowField = self.rowIDField;
        var formatFunc = self.sequenceFormatter;

        var isNumber = function (n) {
            return !isNaN(parseFloat(n)) && isFinite(n);
        };

        // Ordering per callParms
        sqlStatement += self.orderFunction(requestParms.order);

        //Add limit and offset
        sqlStatement += " LIMIT " + requestParms.length + " OFFSET " + requestParms.start;

        $.get(
            self.url + encodeURIComponent(sqlStatement),
            function (data) {
                var retParms = requestParms;
                var retObj = {};
                var cNames = data.data[0];

                retObj.draw = retParms.draw;
                retObj.recordsTotal = this.recordsTotal;
                retObj.recordsFiltered = this.recordsFiltered;
                retObj.data = [];

                data.data.slice(1).forEach(function (cv) {
                    var obj = {};
                    cv.forEach(function (d, idx) {
                        var escapedField = '"' + cNames[idx] + '"';
                        if (isNumber(d) && cNames[idx] != 'PEPTIDE_ID') {
                            obj[escapedField] = Number.parseFloat(d);
                        } else {
                            obj[escapedField] = d;
                        }
                    });
                    if (rowField) {
                        obj.DT_RowId = obj['"' + rowField + '"'];
                        obj.DT_RowData = {
                            key: obj['"' + rowField + '"'],
                            fObj: obj,
                        };
                    }
                    retObj.orderable = true;
                    retObj.data.push(obj);
                });
                if (formatFunc) {
                    retObj = formatFunc(retObj);
                }
                callbackFN(retObj);
            }.bind(self)
        );
    };

    /**
     * Called from the DataTable table.
     * Need to state check:
     *  - Is this the first call or pagination call. If first,
     *      need to get the total DB count for the base query before
     *      running the base query.
     *  - Is this a call based on filter and its first filter call:
     *      Need to get DB count on base plus filter query, then
     *          run the filter query.
     *  - Is this a clear filter call, that is we are in a filtered state, but
     *      now the user has cleared the filter.
     *  - Ths filter call can never be the absolute first call. Table is rendered
     *      from the first call.
     *
     */
    this.provideData = function (callParms, callbackFN) {
        if (!this.recordsTotal) {
            this.getTotalRecordCount(callParms, callbackFN, this);
        } else if (callParms.search.value.length > 0 && !this.filtered) {
            // Table is asking for a filtered query. It is the first filtered request
            this.filtered = true;
            this.getFilteredRecordCount(callParms, callbackFN, this);
        } else if (callParms.search.value.length === 0 && this.filtered) {
            // Table is resetting from filtering.
            this.filtered = false;
            this.recordsFiltered = this.recordsTotal;
            this.queryData(callParms, callbackFN, this);
        } else {
            this.queryData(callParms, callbackFN, this);
        }
    };

    this.fillDOM = function () {
        var cbFn = this.initCompleteCB;
        var options = {
            scrollX: true,
            dom: "rtipl",
            processing: true,
            serverSide: true,
            ajax: function (data, callbackFN) {
                this.provideData(data, callbackFN);
            }.bind(this),
            columns: this.getColumnNames(),
        };

        $("#" + this.tableDivID)
            .DataTable(options)
            .on("init.dt", function () {
                $("#progress-div").empty();
                cbFn();
            });
    };

    this.generateTable = function () {
        // Do we need to get column names?
        if (!this.columnNames) {
            // Need to dynamically generate column names.
            $.get(
                this.url + encodeURIComponent(this.buildBaseQuery({ value: "" })) + " LIMIT 0",
                function (data) {
                    this.columnNames = [];
                    data.data[0].forEach(
                        function (cn) {
                            var obj = {};
                            obj.data = '"' + cn + '"'; // Some of the feeding applications use illegal characters in their column names.
                            obj.title = cn;
                            this.columnNames.push(obj);
                        }.bind(this)
                    );
                    this.fillDOM();
                }.bind(this)
            );
        } else {
            this.fillDOM();
        }
    };

    // this.clearContents = function() {
    //     let dElem = $('#' + this.tableDivID);
    //     let dt = $(dElem.selector).DataTable();
    //     dt.destroy();
    //     dElem.empty();
    //     this.columnNames = null;
    //     this.recordsTotal = null;
    //     this.recordsFiltered = null;
    //     this.filtered = false;
    //     this.customSQL = null;
    // };
}

/**
 * Module for handling GUI presentation and data filtering based on the protein FDR threshold used by the
 * search application.
 */
var FDRPresentation = (function (fdr) {
    fdr.ignoreScores = ["theoretical mass", "tic", "score_name"];
    fdr.scoreName = null;
    fdr.scoreValue = null;
    fdr.softwareName = null;
    fdr.softwareVersion = null;
    fdr.fdrProtocolName = null;
    fdr.fdrProtocolValue = null;

    //Use plotly.js for scatter plots
    fdr.buildPlotlyPlots = function () {
        Object.keys(FDRPresentation.graphPackage).forEach(function (k, kIdx) {
            //key is score name, eg: PeptideShaker PSM Score

            var passed = {
                y: FDRPresentation.graphPackage[k].passed,
                x: Array.from({ length: FDRPresentation.graphPackage[k].passed.length }, (x, i) => i),
                mode: "markers",
                type: "scattergl",
                name: "Passed FDR Threshold",
                hoverinfo: "y",
            };

            var failed = {
                y: FDRPresentation.graphPackage[k].failed,
                x: Array.from({ length: FDRPresentation.graphPackage[k].failed.length }, (x, i) => i),
                mode: "markers",
                type: "scattergl",
                name: "Failed FDR Threshold",
                hoverinfo: "y",
            };
            var data = [passed, failed];
            var layout = {
                title: k,
                xaxis: {
                    title: "PSM Index",
                    showticklabels: false,
                },
                height: 500,
            };

            var forClick = document.getElementById("panel_" + kIdx);

            Plotly.newPlot("panel_" + kIdx, data, layout);

            // forClick.on('plotly_click', function(data){
            //     var filter_yval = 0;
            //     data.points.forEach(function(dp) {
            //         if (dp.y > filter_yval) {
            //             filter_yval = dp.y
            //         }
            //     });
            //     document.getElementById('filter_' + kIdx).innerText = 'Filter data by ' + k + ' score value >= ' + filter_yval;
            //     var node = document.createElement("button");
            //     node.innerText = 'Filter';
            //     node.style = "margin: 5px;";
            //     node.setAttribute('score_name', k);
            //     node.setAttribute('score_value', filter_yval);
            //     node.addEventListener('click', function(){
            //         console.log('Filtering now.');
            //         console.log('using score ' + this.getAttribute('score_name'));
            //         console.log('value of ' + this.getAttribute('score_value'));
            //     })
            //     document.getElementById('filter_' + kIdx).appendChild(node);
            // })
        });
    };

    //Get the actual scores for the discovered fields.
    fdr.getScoreData = function (fieldNames) {
        let qStr = "SELECT PSM.passThreshold, ";
        let baseURL =
            fdr.href +
            "/api/datasets/" +
            fdr.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        let url = baseURL;

        fieldNames.forEach(function (cv) {
            qStr += 'PSM."' + cv + '",';
        });
        qStr = qStr.slice(0, qStr.lastIndexOf(","));
        qStr += " FROM psm_entries PSM;";
        url += encodeURIComponent(qStr);

        $.get(url, function (data) {
            var graphPackage = {};
            var fNames = data.data[0].slice(1);
            data.data[0].slice(1).forEach(function (sn) {
                graphPackage[sn] = {};
                graphPackage[sn].passed = [];
                graphPackage[sn].failed = [];
            });
            data.data.slice(1).forEach(function (cv) {
                cv.slice(1).forEach(function (x, xidx) {
                    if (cv[0] === "true") {
                        graphPackage[fNames[xidx]].passed.push(x);
                    } else {
                        graphPackage[fNames[xidx]].failed.push(x);
                    }
                });
            });
            fNames.forEach(function (y) {
                graphPackage[y].passed.sort(function (a, b) {
                    return a - b;
                });
                graphPackage[y].failed.sort(function (a, b) {
                    return b - a;
                });
            });
            FDRPresentation.graphPackage = graphPackage;

            url =
                baseURL +
                encodeURIComponent(
                    "SELECT protein_detection_protocol.name,protein_detection_protocol.value, " +
                        "  analysis_software.name, analysis_software.version " +
                        "   FROM protein_detection_protocol, analysis_software"
                );

            $.get(url, function (data) {
                FDRPresentation.fdrProtocolName = data.data[1][0];
                FDRPresentation.fdrProtocolValue = data.data[1][1];
                FDRPresentation.softwareName = data.data[1][2];
                FDRPresentation.softwareVersion = data.data[1][3];
                FDRPresentation.preparePlotlyPanel();
                FDRPresentation.buildPlotlyPlots();
                $("#" + FDRPresentation.divID).hide(); //Start hidden.
                FDRPresentation.publish("FDRDataPrepared");
            });
        });
    };

    //Get REAL scores that have full coverage. These scores will be used in plots
    fdr.getScores = function () {
        let qStr =
            "SELECT score_summary.score_name FROM score_summary WHERE score_summary.pct_scores_present = 1 AND \n" +
            'score_summary.score_type = "REAL"';
        let url =
            fdr.href +
            "/api/datasets/" +
            fdr.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        url += encodeURIComponent(qStr);

        $.get(url, function (data) {
            var graphScores = [];
            data.data.slice(1).forEach(function (cv) {
                if (FDRPresentation.ignoreScores.indexOf(cv[0]) === -1) {
                    graphScores.push(cv[0]);
                }
            });
            FDRPresentation.getScoreData(graphScores);
        });
    };

    //Builds GUI panel for Plotly plots
    fdr.preparePlotlyPanel = function () {
        let domStr =
            '<div class="panel panel-primary">' +
            '<div class="panel-heading">' +
            '<h3 class="panel-title">' +
            '<a role="button" data-toggle="collapse" data-parent="#accordion" href="#collapseOne" aria-expanded="true" aria-controls="collapseOne">' +
            "ID Scores</a></h3></div>" +
            '<div id="collapseOne" class="panel-collapse collapse in" role="tabpanel" aria-labelledby="headingOne">' +
            '<div class="panel-body"><div class="row"><div class="col-md-12"><h5>##SOFTWARE_NAME## (##SOFTWARE_VERSION##) ##FDR_PROTOCOL_NAME## at ##FDR_PROTOCOL_VALUE##</h5></div></div>' +
            "##SCORE_DOM##" +
            "</div>";

        var sDom = "";
        Object.keys(FDRPresentation.graphPackage).forEach(function (k, kIdx) {
            sDom += '<div class="row"><div class="col-md-12" id="filter_' + kIdx + '"></div></div>';
            sDom += '<div id="panel_' + kIdx + '"></div>';
        });

        domStr = domStr.replace("##SCORE_DOM##", sDom);
        domStr = domStr.replace("##SOFTWARE_NAME##", fdr.softwareName);
        domStr = domStr.replace("##SOFTWARE_VERSION##", fdr.softwareVersion);
        domStr = domStr.replace("##FDR_PROTOCOL_NAME##", fdr.fdrProtocolName);
        domStr = domStr.replace("##FDR_PROTOCOL_VALUE##", fdr.fdrProtocolValue);

        $("#" + fdr.divID).append($.parseHTML(domStr));
    };

    fdr.init = function (confObj) {
        fdr.href = confObj.href;
        fdr.datasetID = confObj.datasetID;
        fdr.divID = confObj.divID;
        fdr.callBackFN = confObj.callBackFN;
        fdr.getScores();
    };

    return fdr;
})(FDRPresentation || {}); //eslint-disable-line no-use-before-define

/**
 * User can add tracks to IGV. These tracks are data entries in the current Galaxy history.
 * This code manages interactions betweem user and Galaxy history.
 */
var IGVTrackManager = (function (itm) {
    itm.validTrackTypes = ["bed", "gff", "gff3", "gtf", "wig", "bigWig", "bedGraph", "bam", "vcf", "seg"];
    itm.trackGroups = {
        bed: "annotation",
        gff: "annotation",
        gff3: "annotation",
        gtf: "annotation",
        wig: "wig",
        bigWig: "wig",
        bedGraph: "wig",
        bam: "alignment",
        vcf: "variant",
        seg: "seg",
    };
    itm.galaxyTrackFiles = null;

    itm.queryGalaxyHistory = function () {
        let url = itm.galaxyConfiguration.href + "/api/histories/" + itm.galaxyConfiguration.historyID + "/contents/";

        $.get(url, function (data) {
            let files = [];
            data.forEach(function (d) {
                let obj = {};
                if (Object.keys(d).indexOf("extension") > -1 && d.visible) {
                    if (IGVTrackManager.validTrackTypes.indexOf(d.extension.toLowerCase()) > -1) {
                        obj.id = d.id;
                        obj.name = d.name;
                        obj.sourceType = d.extension;
                        obj.trackGroup = itm.trackGroups[d.extension.toLowerCase()];

                        if (d.extension.toLowerCase() === "bam") {
                            obj.indexURL =
                                itm.galaxyConfiguration.href + d.url + "/metadata_file?metadata_file=bam_index";
                        }

                        files.push(obj);
                    }
                }
            });
            itm.galaxyTrackFiles = files;
            itm.publish("ValidTrackFilesAvailable", itm.galaxyTrackFiles);
        });
    };

    itm.init = function (confObj) {
        itm.galaxyConfiguration = confObj.galaxyConfiguration;

        itm.subscribe("NeedValidTrackFiles", function () {
            if (itm.galaxyTrackFiles) {
                itm.publish("ValidTrackFilesAvailable", itm.galaxyTrackFiles);
            } else {
                itm.queryGalaxyHistory();
            }
        });
    };

    return itm;
})(IGVTrackManager || {}); //eslint-disable-line no-use-before-define

const GenomeWarningText = {
    text:
        '<p class="lead">IGV - Galaxy - Genomes</p>' +
        "<p>The IGV viewer requires access to full genome sequences.</p><p>Galaxy can provide access to a genome sequences via the internal API. This allows for the use of custom reference sequences.</p>" +
        "<p>In addition, IGV has a set of reference genomes that are available to all users of the IGV.js tool</p>" +
        "<p>However, the genome associated with the mz.SQLite history entry is not working with the Galaxy API nor is it a standard IGV genome.</p>" +
        "<p>Until this issue is resolved, you will not be able to see a reference sequence in the MVP viewer.</p>",
};

/**
 * Module code for creating and managing the IGV.js browser.
 *
 * Galaxy history entry for the MZ.Sqlite _must_ have a valid DBKey assigned.
 * @param confObj
 * @constructor
 */
function IGVModule(confObj) {
    this.addTrackCB = confObj.addTrackCB;
    this.igvDiv = confObj.igvDiv;
    this.data = confObj.data;
    if (confObj.genome) {
        this.genome = confObj.genome;
    } else {
        this.genome = confObj.dbkey || "hg19"; //A default value // TODO: Really??
    }

    this.hidden = false;
    if (confObj.fasta_file) {
        this.fasta_file = confObj.fasta_file;
    }
    if (confObj.fasta_index) {
        this.fasta_index = confObj.fasta_index;
    }
}

//Build all the custom UI surrounding the IGV browser.
IGVModule.prototype.fillChrome = function () {
    const IGVOverviewHelp = {
        text:
            '<p class="lead">Purpose</p>' +
            '<p>The IGV panel is the Broad Institutes <a href="http://software.broadinstitute.org/software/igv/" target="_blank">IGV</a> viewer for web applications</p>' +
            "<p>At the start, the IGV viewer is centered around the chromosome location you clicked on in the Peptide-Protein Viewer</p>" +
            "<p>You can move about the entire genome from the IGV viewer. In addition you can load tracks based on data files" +
            " in your current Galaxy history (for instance: BAM, BED or GTF files).</p>" +
            "<p>Note that you cannot change the underlying genome. The genome is set by your Galaxy history.</p>",
    };

    let pStr =
        '<div class="panel panel-default"><div class="panel-heading">' +
        '<div class="row"><div class="col-md-1"><span class="genome-id-value">Genome: ' +
        this.genome +
        "</span></div>" +
        '<div class="col-md-8"><div class="btn-group" role="group" aria-label="...">' +
        '<button id="add-track" type="button" class="btn btn-default">Add Track</button>' +
        '</div></div><div class="col-md-1"><button class="kill-igv-browser">Hide</button>' +
        '<span id="igv_overview_help" style="padding: 5px">Help</span></div>' +
        "</div></div>" +
        '</div><div class="panel-body">' +
        '<div id="browser-location"></div></div></div>';
    let self = this;

    $("#" + this.igvDiv).append($.parseHTML(pStr));

    $("#add-track").on("click", function () {
        self.addTrackCB();
    });

    $("#igv_overview_help").on("click", function () {
        BuildHelpPanel.showHelp({
            helpText: IGVOverviewHelp.text,
            title: "IGV Overview Help",
        });
    });

    $(".kill-igv-browser").on("click", function () {
        self.hidden = true;
        $("#igvDiv").hide();
    });
};

IGVModule.prototype.loadTrack = function (o) {
    igv.browser.loadTrack(o);
};

IGVModule.prototype.goToLocation = function (loc) {
    if (this.hidden) {
        $("#igvDiv").show();
    }
    igv.browser.search(loc);
};

IGVModule.prototype.showBrowser = function () {
    let ref = {};
    // Are we working from a Galaxy genome or IGV reference?
    if (this.fasta_file) {
        ref["fastaURL"] = this.fasta_file;
        ref["indexURL"] = this.fasta_index;
    } else {
        ref["genome"] = this.genome;
    }

    let options = {
        reference: ref,
        locus: this.data.chrom + ":" + this.data.start + "-" + this.data.end,
    };
    this.fillChrome();
    igv.createBrowser(document.getElementById("browser-location"), options);
};

var IGVManager = (function (igm) {
    let validTrackFiles = null;

    igm.goToLocation = function (strL) {
        igm.browser.goToLocation(strL);
    };

    igm.showTrackModal = function () {
        let s =
            '<div class="modal fade" id="galaxy-tracks" tabindex="-1" data-backdrop="false" role="dialog"><div class="modal-dialog" role="document">' +
            '<div class="modal-content">' +
            ' <div class="modal-header"><button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
            '  <h4 class="modal-title">Load IGCV Tracks <h4></div>' +
            ' <div class="modal-body">' +
            "  <p>Available IGV Tracks:</p>" +
            '  <ul class="list-group">##TRACK_LIST##</ul></div>' +
            ' <div class="modal-footer">' +
            '  <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>' +
            '  <button id="btn-load-track" type="button" class="btn btn-primary">Load Track</button>' +
            " </div></div></div></div>";
        let trackList = "";

        if (validTrackFiles.length == 0) {
            $("#igvDiv").prepend(
                '<div class="alert alert-danger" role="alert">Sorry, your Galaxy history does not contain a valid IGV track. There is nothing available to load.</div>'
            );
            $("#add-track").attr("disabled", "disabled");
        } else {
            validTrackFiles.forEach(function (t) {
                trackList += "<li ";
                if (t.indexURL) {
                    trackList += ' indexURL="' + t.indexURL + '"';
                }
                trackList +=
                    ' trackGroup="' +
                    t.trackGroup +
                    '" sourcetype="' +
                    t.sourceType +
                    '" gid="' +
                    t.id +
                    '" class="list-group-item track-id-item">' +
                    t.name +
                    "</>";
            });
            s = s.replace("##TRACK_LIST##", trackList);
            $("#master_modal").empty().append(s);

            $(".track-id-item").on("click", function () {
                $(this).toggleClass("selected");
            });

            $("#btn-load-track").on("click", function () {
                $(".track-id-item.selected").each(function () {
                    let apiCall =
                        igm.galaxyConfiguration.href +
                        "/api/histories/" +
                        igm.galaxyConfiguration.historyID +
                        "/contents/" +
                        $(this).attr("gid") +
                        "/display";
                    let opts = {};
                    opts.type = $(this).attr("trackGroup");
                    opts.sourceType = $(this).attr("sourcetype");
                    opts.url = apiCall;
                    opts.name = $(this).text();
                    if ($(this).attr("indexURL")) {
                        opts.indexURL = $(this).attr("indexURL");
                    }
                    igm.browser.loadTrack(opts);
                });
                $("#galaxy-tracks").modal("hide");
            });

            $("#galaxy-tracks").modal({ backdrop: false });
        }
    };

    igm.addIGVTrack = function () {
        if (validTrackFiles) {
            igm.showTrackModal(validTrackFiles);
        } else {
            igm.subscribe("ValidTrackFilesAvailable", function (d) {
                validTrackFiles = d;
                igm.showTrackModal(validTrackFiles);
            });
            igm.publish("NeedValidTrackFiles");
        }
    };

    igm.createNewBrowser = function (confObj) {
        confObj.addTrackCB = igm.addIGVTrack;
        igm.browser = new IGVModule(confObj);
        igm.browser.showBrowser();
    };

    //IGV default genome use.
    // We are here because of a Galaxy API call failure. Fall back to one of the
    // supported IGV genomes. Otherwise, inform the user we are having an issue.
    igm.defaultGenomeConfig = function (defaultObject) {
        let hosted_genomes = [
            "hg38",
            "hg19",
            "hg18",
            "mm10",
            "gorGor4",
            "panTro4",
            "panPan2",
            "susScr11",
            "bosTau8",
            "canFam3",
            "rn6",
            "danRer11",
            "danRer10",
            "dm6",
            "ce11",
            "sacCer3",
        ];

        //Do we have an exact match "galaxy dbKey": "mm10" <-> "hosted_genomes": "mm10"?
        let idx = hosted_genomes.indexOf(defaultObject.genome.toLowerCase());
        let igv_genome = "";
        if (idx > -1) {
            igv_genome = hosted_genomes[idx];
            defaultObject.igvConfObj.fasta_file = null;
            defaultObject.igvConfObj.fasta_index = null;
            defaultObject.igvConfObj.genome = igv_genome;
            igm.createNewBrowser(defaultObject.igvConfObj);
        } else {
            // Got a partial match?? mm9 will match mm10
            let rx = /\D+/;
            let galaxy_genome = rx.exec(defaultObject.genome.toLowerCase());
            for (let i = 0; i < hosted_genomes.length; i++) {
                let result = rx.exec(hosted_genomes[i]);
                if (result[0] === galaxy_genome[0]) {
                    // First match and we are out.
                    defaultObject.igvConfObj.fasta_file = null;
                    defaultObject.igvConfObj.fasta_index = null;
                    defaultObject.igvConfObj.genome = result["input"];
                    igm.createNewBrowser(defaultObject.igvConfObj);
                }
            }
            // No matches at all
            BuildHelpPanel.showHelp({
                helpText: GenomeWarningText.text,
                title: "Missing Genome: " + defaultObject.genome,
            });
        }
    };

    igm.buildModule = function (confOb) {
        //Get URI for index file and fasta file, URI call will be based on dbkey.
        //http://localhost:8080/api/genomes/mmXX/genome_uri
        let uri = this.galaxyConfiguration.href + "/api/genomes/" + this.galaxyConfiguration.dbkey + "/genome_uri";
        let cobj = confOb;
        fetch(uri)
            .then((resp) => resp.json())
            .then(function (data) {
                cobj.fasta_file = data["fasta_file"];
                cobj.fasta_index = data["fasta_index"];
                igm.createNewBrowser(cobj);
            })
            .catch(function (error) {
                // There is an error coming back from the API call. Fallback to IGV functionality.
                // Use IGV supported genomes only.
                igm.defaultGenomeConfig({
                    genome: cobj.dbkey,
                    igvConfObj: cobj,
                });
            });
    };

    igm.init = function (confObj) {
        igm.galaxyConfiguration = confObj.galaxyConfiguration;
    };

    return igm;
})(IGVManager || {}); //eslint-disable-line no-use-before-define

/**
 * Name:            PSMProteinViewer.js
 * Author:          mcgo0092@umn.edu
 * Created:         Mar 1 2016
 *
 * Description:
 *              This is a D3.js based svg generator. It is meant to show a user
 *              the relationship between user chosen PSM sequences, associated
 *              peptide sequences and the originating protein.
 *
 */

let PSMProteinViewer = (function () {
    /**
     *
     * @param confObj The object containing protein information.<br/>With the following elements <br/>
     *
     *      baseDiv: '#id' The DOM element to insert all SVGs.
     *      genome: [
     *          {
                    cds_end:143
                    cds_start:0
                    chrom:"15"
                    end:41096310
                    name:"H0YMN5"
                    start:41096167
                    strand:"-"
     *          }
     *      ],
     *      protein: {
     *          sequence: [] Array of peptide sequences
     *          offset: x If the offset should start at something else than 0
     *          name: 'protein name' The protein name.
     *      }
     *      peptideList: [
     *          {
     *              sequence: [], sequence array
     *              offset: int, where does the peptide start on the protein
     *              score: '', string of a score to show in tooltip
     *          } ...
     *      ]
     * @constructor
     */
    function PSMProteinViewer(confObj) {
        var self = this;
        var viewObject = confObj;

        this.dbkey = confObj.dbkey;

        //Callback function for requesting an MSMS render of a PSM
        this.msmsRender = confObj.msmsRender;

        //Basic configuration values

        //Holds all the protein information
        this.proteinObj = confObj.protein;
        //Holds all the PSMs
        this.peptideList = confObj.peptideList;

        if (confObj.genome) {
            this.genomeList = confObj.genome;
        } else {
            this.genomeList = [];
        }
        this.aaAbrev = {
            A: "ala",
            R: "arg",
            N: "asn",
            D: "asp",
            C: "cys",
            Q: "gln",
            E: "glu",
            G: "gly",
            H: "his",
            I: "ile",
            L: "leu",
            K: "lys",
            M: "met",
            F: "phe",
            P: "pro",
            S: "ser",
            T: "thr",
            W: "trp",
            Y: "tyr",
            V: "val",
            B: "asx",
            Z: "glx",
            X: "xaa",
        };

        //Modifications, dynamically set from input
        this.modifications = [];
        var boundList = this.modifications;
        this.peptideList.forEach(function (p) {
            if (p.hasOwnProperty("mods")) {
                p.mods.forEach(function (m) {
                    if (boundList.indexOf(m[1]) === -1) {
                        boundList.push(m[1]);
                    }
                });
            }
        });

        //Protein rect size in focus area
        this.prtSz = 20;
        //rounded rect
        this.rXrY = 5;
        //Opacity
        this.rectOpacity = 0.75;
        //Text Y buffer
        this.txtYBuffer = 4;
        //Track where the protein is showing 0 === beginning of protein
        //This is never > 0, it is the translate x offset
        this.prtSeqXPos = 0;
        //Show protein sequence offset every xth aa. Default is every 10th residue
        this.offsetModal = 10;
        //maximum Y offset when all peptides are rendered.
        this.maxFocusY = 0;
        //protein rect size in context area
        this.ctxPrtSz = 5;
        //Holds y coordinates of drawn peptides. Used for packing
        this.psmExclusions = [];

        this.margin = { left: 50, right: 50, top: 50, bottom: 50 };

        //base div for svg, will be overridden by user
        this.baseDiv = confObj.baseDiv || "body";

        //div for igv.js viewer
        this.igvDiv = confObj.igvDiv;

        //Prep for SVG creation
        //add context and focus divs.
        $(self.baseDiv).append($.parseHTML('<div id="prt_name" class="col-md-12"></div>'));
        $(self.baseDiv).append($.parseHTML('<div id="genome" class="col-md-12"></div>'));
        $(self.baseDiv).append($.parseHTML('<div id="focus" class="col-md-12"></div>'));
        $(self.baseDiv).append($.parseHTML('<div id="context" class="col-md-12"></div>'));

        //SVG holding protein name and desciption
        this.prtNameSVG = d3
            .select("#prt_name")
            .append("svg")
            .attr("width", function () {
                return $("div#prt_name").width() - self.margin.left - self.margin.right;
            })
            .attr("height", 50);

        this.genomeSVG = d3
            .select("#genome")
            .append("svg")
            .attr("width", function () {
                return $("div#prt_name").width() - self.margin.left - self.margin.right;
            })
            .attr("height", 50);

        //SVG holding the focus graphics
        this.focusSVG = d3
            .select("#focus")
            .append("svg")
            .attr("width", function () {
                return $("div#focus").width() - self.margin.left - self.margin.right;
            })
            .attr("height", "100%");
        //Focus 'g'
        this.focusGroup = null;

        //SVG holding the context graphics
        this.contextSVG = d3
            .select("#context")
            .append("svg")
            .attr("width", function () {
                return $("div#context").width() - self.margin.left - self.margin.right;
            })
            .attr("height", "100%");

        //Context 'g'
        this.contextGroup = null;
        //Genome group
        this.genomeGroup = null;

        //Context svg uses a d3 scale.
        this.ctxXScale = d3
            .scaleLinear()
            .domain([0, self.proteinObj.sequence.length])
            .range([0, parseInt(self.contextSVG.style("width"))]);

        //Rendering functions and helpers -------------------------------------

        //Moves the focus locator line to the corrected position in the context SVG.
        this.lineRelocator = function () {
            var newX1 = -1 * (self.prtSeqXPos / self.prtSz);
            var newX2 = newX1 + Math.floor(parseInt(self.focusSVG.style("width")) / self.prtSz);

            d3.select("line.locator").attr("x1", self.ctxXScale(newX1)).attr("x2", self.ctxXScale(newX2));
        };

        //Allows for proper packing of sequences.
        //No overlapping of peptide sequences in the y direction.
        this.calcExclusionZone = function (len, offset, sizeOffset) {
            var factor = 2;

            self.psmExclusions.map(function (cv) {
                if (
                    (offset <= cv[1] && offset >= cv[0]) ||
                    (offset + (len - 1) <= cv[1] && offset + (len - 1) >= cv[0])
                ) {
                    factor += 1;
                }
            });

            self.psmExclusions.push([offset, offset + (len - 1)]);
            return factor * sizeOffset;
        };

        this.styleMods = function (data, idx) {
            var elemIDX = idx;
            if (data.hasOwnProperty("mods")) {
                data.mods.forEach(function (aMod) {
                    var offset = aMod[0] === 0 ? 0 : aMod[0] - 1; //TODO: talk to JJ about this crazy offset issue in the DB
                    $("rect.peptide_" + elemIDX + ":eq(" + offset + ")").addClass("ptm");
                    $("text.peptide_" + elemIDX + ":eq(" + offset + ")").addClass(aMod[1].toLowerCase());
                });
            }
        };

        //Rendering functions and helpers -------------------------------------

        //Div for tooltip display used as user hovers
        this.ttDiv = d3
            .select("body")
            .append("div")
            .attr("class", "tooltip")
            .attr("id", "d3-tooltip")
            .style("opacity", 0);

        //Actual SVG rendering
        this.renderSVG = function () {
            //Protein name and description
            self.prtNameSVG
                .append("g")
                .append("text")
                .text(function () {
                    return self.proteinObj.name;
                })
                .attr("x", 0)
                .attr("y", 20)
                .attr("font-family", "sans-serif")
                .attr("font-size", "20px");

            //Add drag behavior.
            self.focusGroup = self.focusSVG
                .append("g")
                .attr("transform", "translate(0,5)")
                .call(
                    d3.drag().on("drag", function () {
                        self.prtSeqXPos += d3.event.dx;
                        //Confine the sequence line from running off the left
                        if (self.prtSeqXPos > 0) {
                            self.prtSeqXPos = 0;
                        }
                        //Confine the sequence line from running off the right
                        if (Math.abs(self.prtSeqXPos) > (self.proteinObj.sequence.length - 20) * self.prtSz) {
                            self.prtSeqXPos = -1 * ((self.proteinObj.sequence.length - 20) * self.prtSz);
                        }
                        d3.select(this).attr("transform", "translate(" + self.prtSeqXPos + ",0)");
                        //move the genome group
                        if (self.genomeGroup) {
                            self.genomeGroup.attr("transform", "translate(" + self.prtSeqXPos + ",0)");
                        }
                        self.lineRelocator();
                    })
                );

            self.genomeGroup = self.genomeSVG.append("g").attr("transform", "translate(0,0)");
            //Draw the genome schematic, if needed
            if (self.genomeList.length > 0) {
                //SVG patterns for showing genomic information
                $("div #genome")
                    .find("g")
                    .append(
                        "<svg>" +
                            '<defs><pattern id="genomePlus" x="0", y="0" width="8" height="8" patternUnits="userSpaceOnUse">' +
                            '<polygon points="0,0 0,8 4,4" style="fill:#e6550d;stroke:gray;stroke-width:1;opacity:1.0"></polygon>' +
                            '</pattern><pattern id="genomeNeg" x="0", y="0" width="8" height="8" patternUnits="userSpaceOnUse">' +
                            '<polygon points="8,0 8,8 4,4" style="fill:#e6550d;stroke:gray;stroke-width:1;opacity:1.0"></polygon>' +
                            "</pattern>" +
                            '<pattern id="ref_align" patternUnits="userSpaceOnUse" x="0" y="0" width="10" height="10"> <line x1="0" y1="10" x2="5" y2="0" style="stroke:#9c3e0d;stroke-width:1" /> ' +
                            '<line x1="5" y1="10" x2="10" y2="0" style="stroke:#9c3e0d;stroke-width:1" /></pattern>' +
                            "</defs></svg>"
                    );

                self.genomeGroup
                    .selectAll("rect")
                    .data(self.genomeList)
                    .enter()
                    .append("rect")
                    .attr("x", function (d) {
                        return (d["cds_start"] / 3) * self.prtSz;
                    })
                    .attr("y", 0)
                    .attr("width", function (d) {
                        var x = d["cds_end"] / 3 - d["cds_start"] / 3;
                        return x * self.prtSz;
                    })
                    .attr("height", 8)
                    .attr("class", "genome_line")
                    .attr("fill", function (d) {
                        if (d["strand"] === "+") {
                            return "url(#genomePlus)";
                        } else {
                            return "url(#genomeNeg)";
                        }
                    })
                    .attr("rx", self.rXrY)
                    .attr("ry", self.rXrY)
                    .on("click", function () {
                        let d = d3.select(this).data()[0];
                        let options = {};

                        if (PSMProteinViewer.igvModule) {
                            //already created just search
                            IGVManager.goToLocation(d.chrom + ":" + d.start + "-" + d.end);
                        } else {
                            options.igvDiv = self.igvDiv;
                            options.data = d;
                            options.dbkey = self.dbkey;
                            //Does self have a dbkey assigned? If not, inform the
                            //user they must associated the history entry with a
                            //reference genome.
                            if (self.dbkey === "?") {
                                //TODO: modal, message banner or something else besides alert??
                                alert("The mz.sqlite database must be associated with a reference genome");
                            } else {
                                IGVManager.buildModule(options);
                            }
                            PSMProteinViewer.igvModule = true;
                        }
                    })
                    .append("svg:title")
                    .text(function (d) {
                        var s =
                            "Go to " +
                            d["chrom"] +
                            ":" +
                            d["start"].toLocaleString() +
                            "-" +
                            d["end"].toLocaleString() +
                            " on an open IGV browser.";
                        return s;
                    });

                self.genomeGroup
                    .selectAll("text")
                    .data(self.genomeList)
                    .enter()
                    .append("text")
                    .text(function (d) {
                        return "Chr: " + d["chrom"];
                    })
                    .attr("x", function (d) {
                        return (d["cds_start"] / 3) * self.prtSz + 3;
                    })
                    .attr("y", 18)
                    .attr("font-size", "16")
                    .attr("transform", "translate(0,10)");
            } else {
                //Add a 'dummy' genome line to indicate the lack of genomic coordinates.
                self.genomeSVG
                    .selectAll("line")
                    .data([1])
                    .enter()
                    .append("line")
                    .attr("x1", 0)
                    .attr("x2", function () {
                        return $("div#genome").width();
                    })
                    .attr("class", "genome_dummy")
                    .attr("y1", 0)
                    .attr("y2", 0);

                self.genomeSVG
                    .append("text")
                    .text("No Genomic Coordinates Available")
                    .attr("x", 10)
                    .attr("y", 15)
                    .attr("font-size", "18");
            }

            //Draw variant<->reference comparison ======================================================================
            self.variantGroup = self.genomeGroup.append("g").attr("transform", "translate(0,30)");
            // Alignments
            // aligns: [[40, 50], [50, 55]]
            viewObject.variantInformation.aligns.forEach(function (a) {
                self.variantGroup
                    .append("g")
                    .attr("transform", "translate(0,10)")
                    .append("rect")
                    .attr("x", a[0] * self.prtSz)
                    .attr("y", 0)
                    .attr("width", (a[1] - a[0]) * self.prtSz)
                    .attr("height", 3)
                    .attr("fill", "#9c3e0d")
                    .attr("class", "align_match")
                    .append("svg:title")
                    .text("Aligned with reference sequence.");
            });

            // Deletions
            // Object loc:20 missing:"ELV"
            viewObject.variantInformation.deletions.forEach(function (v) {
                self.variantGroup
                    .append("polygon")
                    .attr("points", function () {
                        var idx = v.loc;
                        var a = [idx * self.prtSz, self.prtSz];
                        var b = [a[0] + self.prtSz / 2, 0];
                        var c = [a[0] - self.prtSz / 2, 0];
                        return a.toString() + " " + b.toString() + " " + c.toString();
                    })
                    .attr("fill", "#9c3e0d")
                    .append("svg:title")
                    .text("Deletion of " + v.missing + " from reference seqeunce.");
            });

            // Additions
            // additions: [{loc: 30, added: 'ELV'}]
            viewObject.variantInformation.additions.forEach(function (v) {
                var offset = v.loc;
                var addLen = v.added.length;
                self.variantGroup
                    .append("polygon")
                    .attr("points", function () {
                        var a = [offset * self.prtSz, self.prtSz];
                        var b = [(offset + addLen) * self.prtSz, self.prtSz];
                        var c = [(a[0] + b[0]) / 2, 0];
                        return a.toString() + " " + b.toString() + " " + c.toString();
                    })
                    .attr("fill", "#9c3e0d")
                    .append("svg:title")
                    .text("Addition to reference sequence.");
            });
            //==========================================================================================================

            //Draw the protein sequence rects
            self.focusGroup
                .selectAll("rect")
                .data(self.proteinObj.sequence)
                .enter()
                .append("rect")
                .attr("class", function (d, i) {
                    var rClass = "amino_acid";
                    var vObj = viewObject;
                    //substituitions: [{loc: 5, ref:'X'},{loc: 10, ref:'X'}],
                    vObj.variantInformation.substitutions.forEach(function (sub) {
                        if (sub.loc === i) {
                            rClass = "reference_mismatch";
                        }
                    });
                    return rClass;
                })
                .attr("x", function (d, i) {
                    return i * self.prtSz;
                })
                .attr("y", 0)
                .attr("rx", self.rXrY)
                .attr("ry", self.rXrY)
                .attr("width", self.prtSz)
                .attr("height", self.prtSz)
                .attr("opacity", self.rectOpacity);

            //Draw protein residue text
            self.focusGroup
                .selectAll("text.aa_residue")
                .data(self.proteinObj.sequence)
                .enter()
                .append("text")
                .attr("class", "aa_residue")
                .text(function (d) {
                    return d;
                })
                .attr("x", function (d, i) {
                    return i * self.prtSz + self.prtSz / 2.0;
                })
                .attr("y", self.prtSz - self.txtYBuffer)
                .attr("text-anchor", "middle");

            //Draw sequence offsets. I think it looks better than an axis.
            self.focusGroup
                .selectAll("text.offset")
                .data(self.proteinObj.sequence)
                .enter()
                .append("text")
                .attr("class", "offset")
                .text(function (d, i) {
                    if (i % self.offsetModal === 0) {
                        return i;
                    }
                })
                .attr("x", function (d, i) {
                    return i * self.prtSz + self.prtSz / 2.0;
                })
                .attr("y", 2 * (self.prtSz - self.txtYBuffer))
                .attr("text-anchor", "middle");

            //Begin context rendering
            self.contextGroup = self.contextSVG.append("g").attr("transform", "translate(0,0)");

            //Draw the focus locator, want it as the bottom layer so has to draw first.
            self.contextGroup
                .append("line")
                .call(
                    d3
                        .drag()
                        .on("drag", function () {
                            var evtX = 0;
                            var numAA = 0;
                            var focusSVGW = parseInt(self.focusSVG.style("width"));
                            var focusW = self.ctxXScale(
                                Math.floor(parseInt(self.focusSVG.style("width")) / self.prtSz)
                            );

                            //never let locator go beyond left margin
                            evtX = d3.event.x < 0 ? 0.0 : d3.event.x;
                            //never let evtX push locator beyond right margin
                            if (focusSVGW - evtX < focusW) {
                                evtX = focusSVGW - Math.ceil(focusW);
                            }

                            numAA = Math.ceil(evtX / self.ctxXScale(1));

                            d3.select(this)
                                .attr("x1", function () {
                                    return self.ctxXScale(numAA);
                                })
                                .attr("x2", function () {
                                    return (
                                        self.ctxXScale(numAA) +
                                        self.ctxXScale(Math.floor(parseInt(self.focusSVG.style("width")) / self.prtSz))
                                    );
                                });

                            self.prtSeqXPos = -1 * Math.floor(numAA * self.prtSz);
                            self.focusGroup.attr("transform", "translate(" + self.prtSeqXPos + ",5)");
                            if (self.genomeGroup) {
                                self.genomeGroup.attr("transform", "translate(" + self.prtSeqXPos + ",0)");
                            }
                        })
                        .on("end", function () {
                            self.focusGroup.attr("transform", "translate(" + self.prtSeqXPos + ",5)");
                        })
                )
                .attr("class", "locator")
                .attr("x1", 0)
                .attr("y1", 10)
                .attr("x2", function () {
                    var vizAA = Math.floor(parseInt(self.focusSVG.style("width")) / self.prtSz);
                    return self.ctxXScale(vizAA);
                })
                .attr("y2", 10);

            //Draw the scaled protein sequence
            self.contextGroup
                .selectAll("rect.ctx")
                .data(self.proteinObj.sequence)
                .enter()
                .append("rect")
                .attr("class", function () {
                    return "ctx";
                })
                .attr("x", function (d, i) {
                    return self.ctxXScale(i);
                })
                .attr("y", 0)
                .attr("width", function () {
                    return self.ctxXScale(1);
                })
                .attr("height", self.ctxPrtSz)
                .on("mouseover", function (d, i) {
                    var ctxWidth = $("div#context").width();
                    var xPxPos = d3.event.pageX;

                    self.ttDiv.html(d + "<br/> Offset: " + i);

                    if (xPxPos > ctxWidth / 2.0) {
                        xPxPos -= parseInt(self.ttDiv.style("width"));
                    }

                    self.ttDiv.style("left", xPxPos + "px").style("top", d3.event.pageY - 50 + "px");

                    self.ttDiv.transition().duration(200).style("opacity", 0.9);
                })
                .on("mouseout", function () {
                    self.ttDiv.transition().duration(500).style("opacity", 0);
                });

            //Draw PSMs/Peptides onto focus and context svgs
            self.peptideList.map(function (obj, idx) {
                var baseY = self.calcExclusionZone(obj.sequence.length, obj.offset, self.prtSz);
                var tScore;
                var msmsCallback = self.msmsRender;

                if (obj.score) {
                    tScore = obj.score;
                } else {
                    tScore = "No Score";
                }

                if (baseY > self.maxFocusY) {
                    self.maxFocusY = baseY;
                }

                self.focusGroup
                    .selectAll("rect.peptide_" + idx)
                    .data(obj.sequence)
                    .enter()
                    .append("rect")
                    .attr("class", function (d, i) {
                        var c = obj.class + " peptide_" + idx;
                        if (obj.mismatch.indexOf(i) > -1) {
                            c += " mismatch";
                        }
                        return c;
                    })
                    .attr("x", function (d, i) {
                        i += obj.offset;
                        return i * self.prtSz;
                    })
                    .attr("y", baseY)
                    .attr("width", self.prtSz)
                    .attr("height", self.prtSz)
                    .attr("opacity", 0.7);

                self.focusGroup
                    .selectAll("text.peptide_" + idx)
                    .data(obj.sequence)
                    .enter()
                    .append("text")
                    .attr("class", "txt_pep peptide_" + idx)
                    .attr("feature_type", obj.class)
                    .attr("score_val", tScore)
                    .text(function (d) {
                        return d;
                    })
                    .attr("x", function (d, i) {
                        i += obj.offset;
                        return i * self.prtSz + self.prtSz / 2;
                    })
                    .attr("y", baseY + (self.prtSz - self.txtYBuffer))
                    .attr("text-anchor", "middle")
                    .attr("spectrum_identID", obj.spectrum_identID)
                    .on("click", function () {
                        msmsCallback(d3.select(this).attr("spectrum_identID"));
                    })
                    .on("mouseover", function () {
                        var classes = d3.select(this).attr("class");
                        var xPxPos = d3.event.pageX;

                        var scoreTop = $("#focus").position().top;
                        var focusWidth = $("#focus").width();

                        var ttText =
                            d3.select(this).attr("feature_type").toLowerCase() === "psm" ? "Target PSM" : "PSM";
                        var stHTML = "<em>" + ttText + "</em><br>" + d3.select(this).attr("score_val");

                        //Add modifications to tooltip
                        self.modifications.forEach(function (aMod) {
                            if (classes.indexOf(aMod.toLowerCase()) >= 0) {
                                stHTML += "<br><p><strong>Modification:</strong>" + aMod + "</p>";
                            }
                        });

                        self.ttDiv.html(stHTML);

                        self.ttDiv
                            .style("left", function () {
                                if (xPxPos <= focusWidth / 2) {
                                    return focusWidth / 2 + "px";
                                } else {
                                    return focusWidth / 4 + "px";
                                }
                            })
                            .style("top", scoreTop + "px");

                        self.ttDiv.transition().duration(200).style("opacity", 0.9);
                    })
                    .on("mouseout", function () {
                        self.ttDiv.transition().duration(500).style("opacity", 0);
                    });

                //Rects into the context svg
                baseY = baseY / 4.0;
                self.contextGroup
                    .selectAll("rect.ctx_psm_" + idx)
                    .data(obj.sequence)
                    .enter()
                    .append("rect")
                    .attr("class", function (d, i) {
                        var c = "ctx_" + obj.class + " ctx_psm_" + idx;

                        if (obj.mismatch.indexOf(i) > -1) {
                            c += " mismatch";
                        }

                        return c;
                    })
                    .attr("x", function (d, i) {
                        i += obj.offset;
                        return self.ctxXScale(i);
                    })
                    .attr("y", baseY)
                    .attr("width", self.ctxXScale(1))
                    .attr("height", self.ctxPrtSz);

                self.styleMods(obj, idx);
            });

            //Focus height needs to be set now that everything is drawn
            self.focusSVG.attr("height", self.maxFocusY + 50);
            self.contextSVG.attr("height", self.maxFocusY / 4 + 50); //TODO: ratio of the two rect sizes.
        };
    }

    return PSMProteinViewer;
})();
/* eslint-disable-line no-use-before-define, no-unused-vars */

const PeptideOverviewHelp = {
    text:
        '<p class="lead">Purpose</p>' +
        "<p>The Peptide Overview panel gives quick access to information about: unique peptide sequences (Sequences), displayed with any covalent modifications to specific amino acids highlighted and annotated via mouse-over, number of PSMs matched to each sequence (Spectra Count) and the number of inferred proteins containing each peptide sequence (Protein Count).  Data can be sorted be each of these columns in ascending or descending order.</p>" +
        "<hr>" +
        '<p class="lead">Actions</p><p><dl>' +
        "<dt>PSMs for Selected Peptides</dt><dd>Show PSMs for all selected unique peptide sequences in the Peptide Overview table. All PSMs matching to this peptide are shown, without filtering by scoring metrics.</dd>" +
        "<dt>PSMs filtered by Score</dt><dd>You can filter PSMs by their associated scores. You can filter just the PSMs linked with the selected peptide sequences in the table or filter for PSMs from the entire dataset. To select filtering criteria, a filtering panel will become visible.</dd>" +
        "<dt>Load from Galaxy</dt><dd>You can load a pre-filtered single-column tabular file from Galaxy containing peptide sequences of interest. The column must contain a peptide sequence on each line, one per line.</dd>" +
        "<dt>Peptide-Protein Viewer</dt><dd>Displays a peptide sequence aligned within the overall protein sequence(s) from which it is derived.  Other peptides from the dataset also derived from this protein are displayed as well.   This viewer also displays genomic coordinates coding for the protein sequence, from which the IGV viewer can be launched.</dd>" +
        "<dt>Render</dt><dd>Generate a Lorikeet view of a single, annotated MS/MS scan for each peptide shown in the overview table. Based on the score selected from the dropdown menu, the highest quality MS/MS spectra matching each peptide will be shown.</dd>" +
        "<dt>Filter</dt><dd>Filter and select peptides based on sequence information query entered in the text box.</dd>" +
        "</dl></p>",
};

const PSMDetailHelp = {
    text:
        '<p class="lead">Purpose</p>' +
        '<p>This panel contains all the details for a set of selected peptide sequences, including any scoring metrics available for the highest quality PSM for the peptide. Each column is sortable.  Click on any row, and the best scoring, annotated MS/MS spectra will be generated for viewing using the <a href="https://github.com/UWPR/Lorikeet" target="_blank">Lorikeet</a> tool.</p>' +
        '<hr><p class="lead">Actions</p>' +
        "<dl><dt>Row Click</dt><dd>Click on any peptide sequence in a row to generate the view of the annotated MS/MS spectra matched to this sequence.  Clicking on multiple rows will generate separate MS/MS visualizations.</dd></dl>",
};

/**
 * Module of code for managing and presenting a peptide-centric view of the mz-sqlite db.
 */
var PeptideView = (function (pv) {
    pv.baseQuery = {
        SELECT:
            'spectrum_counts.ENCODED_SEQUENCE AS Sequence, spectrum_counts.SPECTRA_COUNT AS "Spectra Count", protein_counts.PROTEIN_COUNT AS "Protein Count", spectrum_counts.peptide_id',
        FROM: "spectrum_counts, protein_counts",
        WHERE: "protein_counts.SII_ID = spectrum_counts.SII_ID",
    };
    pv.columnValues = "";
    pv.tableElm = '<table id="data-table" class="table table-bordered" cellspacing="0" width="100%"></table>';
    pv.visibleScores = [];
    pv.forPSMRendering = [];
    pv.filteringFiles = [];
    pv.candidateFiles = {};
    pv.candidateFilesPanel = false;

    pv.prepareFilterSequences = function (lst) {
        if (lst.length > 0) {
            if (lst.indexOf("%") > -1) {
                pv.filterByLike(lst.split(/\s|,|;|:/).toLocaleString());
            } else {
                pv.filterBySequences(lst.split(/\W/).toLocaleString());
            }
        } else {
            console.log("User wants to filter on an empty list");
        }
    };

    pv.domEdit = function () {
        var e = $("#" + pv.baseDiv);
        e.empty();
        var tt =
            "Generate a single MSMS scan for each peptide in the overview table. The best MSMS will be determined by the chosen score.";
        e.append(
            $.parseHTML(
                '<div class="panel panel-default"> ' +
                    '<div class="panel-heading"><h3 class="panel-title" style="display: inline">Peptide Overview</h3><span id="peptide_overview_help" class="fa fa-question" style="padding: 5px"></span><span class="sr-only">Help?</span></div>' +
                    '<div class="row">' +
                    '<div class="col-md-6">' +
                    '<div id="pep-functions" class="btn-group" role="group">' +
                    '<button id="btn-load-from-galaxy" type="button" class="btn btn-primary" disabled="disabled" data-toggle="tooltip" data-placement="bottom" title="Enlists datasets from Galaxy history for loading">Load from Galaxy</button>' +
                    '<button id="btn-view-in-protein" type="button" class="btn btn-primary" disabled="disabled" data-toggle="tooltip" data-placement="bottom" title="Displays peptide hits aligned within protein sequences and genomic location of translated genes">Peptide-Protein Viewer</button>' +
                    '<button type="button" class="btn btn-primary dropdown-toggle render-btn" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" ><span data-toggle="tooltip" data-placement="bottom" title="' +
                    tt +
                    '">Render </span><span class="caret"></span><span class="sr-only">Toggle Dropdown</span></button>' +
                    '<ul id="score-type-ul" class="dropdown-menu"></ul>' +
                    "</div></div>" +
                    '<div class="col-md-1"></div><div class="col-md-5"><input class="pep-filter" size="40" type="text" placeholder="Peptide Sequences for Filtering"/>' +
                    '<button type="button" class="pep-filter btn btn-primary" data-toggle="tooltip" data-placement="bottom" title="Filter peptides based on sequence information query">Filter</button><button type="button" class="pep-filter btn btn-primary" data-toggle="tooltip" data-placement="bottom" title="Clear query for filtering peptides">Clear</button></div>' +
                    "</div>" +
                    '<div class="panel-body">' +
                    pv.tableElm +
                    "</div>" +
                    '<div class="panel-footer">' +
                    '<div class="btn-group" role="group">' +
                    '<button type="button" id="psm-all" class="btn btn-primary" data-toggle="tooltip" data-placement="bottom" title="Show PSMs for all selected peptide sequences in the Peptide Overview table">PSMs for Selected Peptides</button>' +
                    '<div class="btn-group" role="group">' +
                    '<button type="button" id="psm-filtered" class="btn btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" ><span data-toggle="tooltip" data-placement="bottom" title="Show PSMs for peptide sequences filtered by score">PSMs Filtered by Score</span> <span class="caret"></span><span class="sr-only">Toggle Dropdown</span></button> ' +
                    '<ul class="dropdown-menu" id="psm-filter-ul">' +
                    '<li value="global"><a href="#">Filter Global Peptides</a></li>' +
                    '<li value="current"><a href="#">Filter Peptides in Peptide Overview Table</a></li></ul>' +
                    "</div></div></div>" +
                    "</div>"
            )
        );
        $(".render-btn").attr("disabled", "disabled");

        //Wire
        $("#psm-filter-ul li").on("click", function () {
            let type = $(this).attr("value");

            if (type === "current") {
                if (pv.forPSMRendering.length === 0) {
                    let table = $("#data-table").DataTable();
                    table.$("tr").toggleClass("selected-peptide");
                    table.$(".selected-peptide").each(function () {
                        pv.forPSMRendering.push(table.$(this).data());
                    });
                    pv.publish("ScoreFilteringRequest", pv.forPSMRendering);
                }
            } else {
                pv.publish("GlobalScoreFilterRequest");
            }

            $("html, body").animate(
                {
                    scrollTop: $("#score_filter_div").offset().top,
                },
                1000
            );
            $("#psm-filtered").tooltip("hide");
        });

        $("#psm-all").on("click", function () {
            if (pv.forPSMRendering.length > 0) {
                pv.appendDetailDOM("Selected Peptides");
                pv.createDetailTable(pv.forPSMRendering);
            }
        });

        //filter code
        $("button.pep-filter").on("click", function () {
            if ($(this).text() === "Filter") {
                pv.prepareFilterSequences($("input.pep-filter").val());
            } else {
                //Clear any existing filtering
                $("input.pep-filter").val("");
                $("#data-table").DataTable().search("");
                $("#data-table").DataTable().draw();
            }
        });

        //Help panel for peptide overview
        $("#peptide_overview_help").on("click", function () {
            BuildHelpPanel.showHelp({
                helpText: PeptideOverviewHelp.text,
                title: "Peptide Overview Help",
            });
        });
    };

    pv.destroyDetailTable = function () {
        var el = $("#detail_div");
        el.empty();
    };

    pv.appendDetailDOM = function (sequence) {
        var el = $("#detail_div");
        el.empty();
        el.append(
            $.parseHTML(
                '<div class="panel panel-default"> ' +
                    '<div class="panel-heading" style="background-color: lightblue;">' +
                    '<div class="row">' +
                    '<div class="col-md-10"><h3 class="panel-title" style="display: inline;">PSM Detail for ' +
                    sequence +
                    '</h3><span id="psm_detail_help" class="fa fa-question" style="padding: 5px"></span><span class="sr-only">Help?</span></div>' +
                    '<div class="col-md-2"><span><button class="kill-detail-table fa fa-times"></button></span></div></div>' +
                    "</div>" +
                    '<div><button id="pep-prot-psm_view" class="btn btn-primary">Peptide-Protein Viewer</button></div>' +
                    '<div class="panel-body"><table id="data-detail-table" class="table table-bordered" cellspacing="0" width="100%"></table></div></div>'
            )
        );

        $(".kill-detail-table").on("click", pv.destroyDetailTable);

        $("#psm_detail_help").on("click", function () {
            BuildHelpPanel.showHelp({
                helpText: PSMDetailHelp.text,
                title: "PSM Details for Selected Unique Peptides",
            });
        });

        $("#pep-prot-psm_view").on("click", function () {
            var ids = [];
            var data = $("#data-detail-table").DataTable().data();
            for (var idx = 0; idx < data.length; idx++) {
                ids.push(data[idx]['"id"']);
            }
            pv.publish("userRequestsViewInProteins", ids.toString());
        });
    };

    pv.buildScoreQuery = function () {
        var q = " psm_entries.id, psm_entries.sequence, psm_entries.spectrumID, psm_entries.spectrumTitle, ";
        pv.visibleScores.forEach(function (cv) {
            q += 'psm_entries."' + cv + '",';
        });
        q = q.slice(0, q.lastIndexOf(","));
        return q;
    };

    //an array of id objects
    pv.createDetailTable = function (idArray, fStr) {
        let idStr = "";
        let filterStr = fStr || null;

        idArray.forEach(function (o) {
            idStr += '"' + o.key + '",';
        });

        idStr = idStr.slice(0, idStr.lastIndexOf(","));

        let setDetailRowClick = function () {
            $("#data-detail-table")
                .find("tbody")
                .on("click", "tr", function () {
                    $(this).toggleClass("selected-peptide");
                    pv.publish("renderPSMForPeptide", {
                        pkid: $(this).data().key,
                        spectrumID: $(this).data().fObj['"spectrumID"'],
                        spectrumTitle: $(this).data().fObj['"spectrumTitle"'],
                    });
                });
        };

        let option = {
            tableDivID: "data-detail-table",
            rowIDField: "id",
            baseQuery: {
                SELECT: "psm_entries.*",
                FROM: " psm_entries",
                WHERE: "psm_entries.id in (" + idStr + ") ",
            },
            href: pv.galaxyConfiguration.href,
            datasetID: pv.galaxyConfiguration.datasetID,
            callBackFN: setDetailRowClick,
        };

        if (idStr.length === 0) {
            //Do not restrict psm_entries.id, this is a global request
            option.baseQuery.WHERE = "";
        }

        if (fStr) {
            if (option.baseQuery.WHERE.length === 0) {
                option.baseQuery.WHERE += " " + fStr + " ";
            } else {
                option.baseQuery.WHERE += " AND " + fStr + " ";
            }
        }

        if (pv.visibleScores.length > 0) {
            option.baseQuery["SELECT"] = pv.buildScoreQuery();
        }

        option.scoreSummary = true;

        let psmDetailDP = new AjaxDataProvider(option);
        psmDetailDP.generateTable();
        //Move to table
        $("html, body").animate(
            {
                scrollTop: $("#detail_div").offset().top,
            },
            1000
        );
        $("#psm-all").tooltip("hide");
    };

    pv.wireTable = function () {
        //Table is initialized
        pv.publish("dataTableInitialized", {});
        let table = $("#data-table").DataTable();

        table.on("draw", function () {
            pv.forPSMRendering = [];
        });

        $("#data-table tbody").on("click", "tr", function () {
            let t = $("#data-table").DataTable();
            //New approach
            if ($(this).hasClass("selected-peptide")) {
                $(this).toggleClass("selected-peptide");
                let d = t.$(this).data();
                if (pv.forPSMRendering.indexOf(d) > -1) {
                    pv.forPSMRendering.splice(pv.forPSMRendering.indexOf(d), 1);
                }
            } else {
                //$('#data-table tbody tr').each(function(){$(this).removeClass('selected-peptide')});
                $(this).addClass("selected-peptide");
                pv.forPSMRendering.push(t.$(this).data());

                //pv.createDetailTable(t.$('tr.selected-peptide').data());
            }
        });
    };

    pv.makeTableAndQuery = function (sqlStr) {
        pv.domEdit();

        pv.dataProvider = new AjaxDataProvider({
            baseQuery: sqlStr,
            rowIDField: "PEPTIDE_ID",
            href: pv.galaxyConfiguration.href,
            datasetID: pv.galaxyConfiguration.datasetID,
            tableDivID: "data-table",
            searchColumn: "spectrum_counts.SEQUENCE",
            callBackFN: pv.wireTable,
            sequenceFormatter: PeptideModifications.htmlFormatSequences,
            modificationCount: pv.galaxyConfiguration.tableRowCount.peptide_modifications,
        });

        pv.dataProvider.generateTable();
    };

    pv.clearSeachFiltering = function () {
        $("#data-table").DataTable().search("").draw();
    };

    pv.setSearchFiltering = function (s) {
        $("#data-table").DataTable().search(s).draw();
    };

    /**
     * User wishes to filter by a large list of peptide sequences.
     * List comes from current Galaxy history.
     * @param listSeq
     */
    pv.filterBySequences = function (listSeq) {
        let escapedStr = "";

        //Clear any existing filtering
        PeptideView.clearSeachFiltering();

        listSeq.split(",").forEach(function (cv, idx) {
            if (idx > 0) {
                escapedStr += ',"' + cv + '"';
            } else {
                escapedStr += '"' + cv + '"';
            }
        });

        PeptideView.setSearchFiltering(escapedStr);
    };

    pv.filterByLike = function (listSeq) {
        let rStr = "";

        PeptideView.clearSeachFiltering();

        rStr += " LIKE " + '"' + listSeq.split(",")[0] + '"';

        PeptideView.setSearchFiltering(rStr);
    };

    pv.prepareRenderScores = function (data) {
        var liS = "";

        $("#score-type-ul").empty();

        data.forEach(function (cv) {
            var s = '<li s_name="' + cv + '" s_dir="ASC"><a href="#"><strong>' + cv + "</strong> ASC</a></li>";
            s += '<li s_name="' + cv + '" s_dir="DSC"><a href="#"><strong>' + cv + "</strong> DSC</a></li>";

            if (cv.indexOf("PeptideShaker") > -1) {
                //prepend in str
                liS = s.concat(liS);
            } else {
                //append in str
                liS = liS.concat(s);
            }
        });

        $("#score-type-ul").append($.parseHTML(liS));
        $("#score-type-ul li").on("click", function () {
            var scoreName = $(this).attr("s_name");
            var sortDir = $(this).attr("s_dir");
            var rowData = $("#data-table").DataTable().rows().data();
            var numRows = rowData.length;
            var idx;
            var peptides = [];

            for (idx = 0; idx < numRows; idx += 1) {
                peptides.push(rowData[idx]['"PEPTIDE_ID"']);
            }

            pv.publish("renderBestPSM", {
                peptideIDs: peptides.toString(),
                scoreField: scoreName,
                sortDir: sortDir,
            });
        });
        //Render btn now is operational
        $(".render-btn").removeAttr("disabled");
    };

    pv.resetTable = function () {
        let tbl = $("#data-table").DataTable();
        tbl.destroy();
        $("#data-table").empty();
        pv.dataProvider = null;
        pv.makeTableAndQuery(pv.baseQuery);
    };

    pv.reBuildTable = function (name, value) {
        let tbl = $("#data-table").DataTable();
        let q = {
            SELECT:
                'DISTINCT spectrum_counts.ENCODED_SEQUENCE AS Sequence, spectrum_counts.SPECTRA_COUNT AS "Spectra Count", protein_counts.PROTEIN_COUNT AS "Protein Count", spectrum_counts.peptide_id',
            FROM: "spectrum_counts, protein_counts, psm_entries",
            WHERE:
                'protein_counts.SII_ID = spectrum_counts.SII_ID AND  psm_entries.id = spectrum_counts.PEPTIDE_ID AND psm_entries."' +
                name +
                '" >= ' +
                value,
        };
        tbl.destroy();
        $("#data-table").empty();
        pv.dataProvider = null;
        pv.makeTableAndQuery(q);
    };

    pv.getPeptideFilterSequences = function (files) {};

    pv.buildFileSelectPanel = function () {
        let str =
            '<div id="user-filter-list" class="panel panel-default">' +
            '  <div class="panel-heading">Choose Tabular File(s) for Peptide Filtering</div>\n' +
            '  <div class="panel-body">##FILES_HERE##</div>' +
            '  <div class="panel-footer">' +
            '  <div class="btn-group" role="group">' +
            '  <button type="button" class="btn btn-primary" id="filter-with">Use for Filtering</button>' +
            '  <button type="button" class="btn btn-primary" id="cancel-this">Cancel</button></div>' +
            "  </div></div>";

        let fDiv = '<div class="row">';
        Object.keys(pv.candidateFiles).forEach(function (key) {
            fDiv +=
                '<div class="col-md-11 shadow candidate-file" dID="' +
                key +
                '">' +
                pv.candidateFiles[key]["name"] +
                "</div>";
        });
        fDiv += "</div>";
        str = str.replace("##FILES_HERE##", fDiv);

        $("#overview_row").prepend($.parseHTML(str));
        $(".candidate-file").on("click", function () {
            if ($(this).hasClass("shadow")) {
                $(this).removeClass("shadow");
                $(this).addClass("used-for-filtering");
            } else {
                $(this).addClass("shadow");
                $(this).removeClass("used-for-filtering");
            }
        });

        $("#cancel-this").on("click", function () {
            $(".candidate-file.used-for-filtering").each(function () {
                $(this).removeClass("used-for-filtering");
                $(this).addClass("shadow");
            });
            $("#user-filter-list").toggle();
        });

        $("#filter-with").on("click", function () {
            pv.filteringFiles = [];
            $(".candidate-file.used-for-filtering").each(function () {
                pv.filteringFiles.push(pv.candidateFiles[$(this).attr("dID")]);
            });
            if (pv.filteringFiles.length > 0) {
                pv.publish("ParseCandidateFiles", pv.filteringFiles);
            }
            $("#user-filter-list").toggle();
        });

        pv.candidateFilesPanel = true;
    };

    pv.init = function (confObj) {
        pv.baseDiv = confObj.baseDiv;
        pv.galaxyConfiguration = confObj.galaxyConfiguration;

        pv.makeTableAndQuery(pv.baseQuery);

        pv.subscribe("UserRemovedFDRFilter", function () {
            pv.resetTable();
        });
        pv.subscribe("VisibleScores", function (arg) {
            //These are the scores the user wants to see
            pv.visibleScores = arg;
            pv.prepareRenderScores(arg);
        });

        pv.publish("RequestVisibleScores");

        pv.publish("RequestRankedScores", {});

        pv.subscribe("CandidateFilesParsed", function (arg) {
            //TODO: this needs to be an accessible function
            let od = $("#overview_div");
            pv.filteringFiles = arg.data;
            od.removeClass("col-md-12");
            od.addClass("col-md-8");
            $("#data-table").DataTable().draw();
            SequenceByFile.init({
                pageSize: 50,
                seqData: pv.filteringFiles,
                elID: "overview_row",
                callBack: pv.filterBySequences,
            });
        });

        pv.subscribe("CandidateFilesAvailable", function (arg) {
            var b = $("#btn-load-from-galaxy");
            var bProt = $("#btn-view-in-protein");
            //Can allow the user to load a peptide file from history.
            b.removeAttr("disabled");

            arg.forEach(function (cv) {
                pv.candidateFiles[cv.obj["id"]] = cv;
            });

            b.on("click", function () {
                if (pv.candidateFilesPanel) {
                    $("#user-filter-list").toggle();
                } else {
                    pv.buildFileSelectPanel();
                }
            });
            bProt.removeAttr("disabled");
            bProt.on("click", function () {
                var ids = [];
                var data = $("#data-table").DataTable().data();
                for (var idx = 0; idx < data.length; idx++) {
                    ids.push(data[idx]['"PEPTIDE_ID"']);
                }
                pv.publish("userRequestsViewInProteins", ids.toString());
            });
        });

        pv.subscribe("UserProvidesScoreFiltering", function (data) {
            pv.appendDetailDOM("Score Filtered PSMs");
            pv.createDetailTable(data["data"], data["fStr"]);
            //Hide Peptide Overview. User is focusing on filtered PSMs.
            document.getElementById("overview_div").setAttribute("style", "display:none");
        });

        pv.subscribe("UserClearedScoreFilter", function () {
            //User is finished with filtered PSMs, present Peptide Overview.
            document.getElementById("overview_div").setAttribute("style", "display:visible");

            let table = $("#data-table").DataTable();
            table.$("tr").removeClass("selected-peptide");
            pv.forPSMRendering = [];
        });

        $('[data-toggle="tooltip"]').tooltip();
    };

    return pv;
})(PeptideView || {}); // eslint-disable-line no-use-before-define
const LorikeetHelp = {
    text:
        '<p class="lead">Purpose</p>' +
        '<p>The <a href="http://uwpr.github.io/Lorikeet/" target="_blank">Lorikeet</a> viewer allows users to view and explore the MS/MS spectra which results in matches to specific peptide sequences.  Annotated MS/MS are shown for peptide sequences clicked on in the PSM Detail for Selected Peptides window, or those generated using the Render button. Lorikeet allows users to select various attributes of peptide MS/MS spectra to annotate (left side) and view a tabular summary peaks matching to selected fragment ions within the spectrum.  More information on Lorikeet is available at <a href="https://github.com/UWPR/Lorikeet" target="_blank">GitHub</a></p>' +
        "<p>Along the top, you can delete, “thumbs up” or “thumbs down” the scan. Scans receiving a thumbs up assignment are tagged, and can be exported back to Galaxy for further analysis if desired.</p>",
};

/**
 * The lorikeet options instance
 * @constructor
 */
function LorikeetInstance() {
    this.options = {
        sequence: null,
        staticMods: [],
        variableMods: [],
        ntermMod: 0, // additional mass to be added to the n-term
        ctermMod: 0, // additional mass to be added to the c-term
        peaks: [],
        massError: 0.1,
        scanNum: null,
        fileName: null,
        charge: null,
        precursorMz: null,
        ms1peaks: null,
        ms1scanLabel: null,
        precursorPeaks: null,
        precursorPeakClickFn: null,
        zoomMs1: false,
        width: 750, // width of the ms/ms plot
        height: 450, // height of the ms/ms plot
        extraPeakSeries: [],
        residueSpecificNeutralLosses: false,
        showIonTable: true,
        showViewingOptions: true,
        showOptionsTable: true, //false
        showInternalIonOption: true,
        showInternalIonTable: true,
        showMHIonOption: false,
        showAllTable: false,
        showSequenceInfo: true,
    };
}

/**
 *
 *  Module for rendering the PSM to Lorikeet
 *
 *  1 - Find PSMs associated with a list of peptide ids.
 *  2 - User has chosen a score to use for ranking.
 *  3 - Get PSM based on the 'best' scoring for desired score.
 *  4 - Generate Lorikeet MSMS based on 3
 *
 */
var RenderPSM = (function (rpm) {
    rpm.currentSpectra = {};
    rpm.renderedSpectra = {};
    rpm.idMapping = {};

    rpm.determineModType = function (arr, type) {
        rVal = [];

        arr.forEach(function (m) {
            if (m.modType === type) {
                rVal.push(m);
            }
        });

        return rVal;
    };

    //Determine nature of mod: fixed, variable, cterm or nterm
    rpm.setModTypes = function (currentSpectra, obj) {
        let sequenceLength = currentSpectra.sequence.length;
        let mods = [];
        if (currentSpectra.modifications != undefined) {
            mods = currentSpectra.modifications;
        }

        obj.staticMods = [];
        obj.variableMods = [];
        obj.ntermMod = 0; // additional mass to be added to the n-term
        obj.ctermMod = 0; // additional mass to be added to the c-term

        mods.forEach(function (m) {
            let residueMod = true;
            let am = {};
            if (m.index === 0) {
                obj.ntermMod += m.modMass;
                residueMod = false;
            }
            if (m.index === sequenceLength + 1) {
                obj.ctermMod += m.modMass;
                residueMod = false;
            }
            if (residueMod) {
                if (m.modType === "fixed") {
                    // Example: [{"modMass":57.0,"aminoAcid":"C"}];
                    am.modMass = m.modMass;
                    am.aminoAcid = m.aminoAcid;
                    obj.staticMods.push(am);
                } else {
                    //Example: [ {index: 14, modMass: 16.0, aminoAcid: 'M'} ]
                    am.index = m.index;
                    am.modMass = m.modMass;
                    am.aminoAcid = m.aminoAcid;
                    obj.variableMods.push(am);
                }
            }
        });
    };

    rpm.renderSpectrum = function (spectrumID) {
        var slug =
            '<div id="#ID#" class="panel panel-info col-md-12" style="background-color: #d9edf7"><div class="panel-heading">' +
            '<div class="row"><div class="col-md-10"><span class="aa aa_header">#PH#</span><span class="lorikeet_help fa fa-question" style="padding: 5px"></span><span class="sr-only">Help?</span></div>' +
            '<div class="col-md-2"<div class="btn-group btn-group-xs" role="group" style="padding-bottom: 5px;">' +
            '<button value="#ID#" spec_id="#SID#" type="button" class="btn btn-default delete-scan"><span class="fa fa-times" aria-hidden="true"></span></button>' +
            '<button value="#ID#" spec_id="#SID#" type="button" class="btn btn-default verify-scan"><span class="fa fa-thumbs-up" aria-hidden="true"></span></button>' +
            '<button value="#ID#" spec_id="#SID#" type="button" class="btn btn-default unverify-scan"><span class="fa fa-thumbs-down" aria-hidden="true"></span></button>' +
            "</div>" +
            '</div><div class="panel-body">#PB#</div></div>';
        var lObj = new LorikeetInstance();

        //Hold a map for  the complicated scan id and title so it is html compliant
        var scanIndex = Object.keys(rpm.renderedSpectra).length + 1;
        rpm.idMapping[scanIndex] = spectrumID;

        slug = slug.replace(/#ID#/g, scanIndex);
        slug = slug.replace(/#SID#/g, spectrumID);
        slug = slug.replace("#PH#", rpm.currentSpectra[spectrumID].sequence);
        slug = slug.replace("#PB#", '<div id="lm_' + scanIndex + '"></div>');
        lObj.scanNum = spectrumID;
        lObj.sequence = rpm.currentSpectra[spectrumID].sequence;
        lObj.peaks = rpm.currentSpectra[spectrumID].peaks;
        lObj.width = 750;
        lObj.height = 450;
        lObj.showInternalIonTable = true;
        lObj.showInternalIonOption = true;
        lObj.showAllTable = true;
        lObj.showOptionsTable = true;
        lObj.labelReporters = true;
        lObj.showMHIonOption = true;
        rpm.setModTypes(rpm.currentSpectra[spectrumID], lObj);

        $("#lorikeet_zone").prepend($.parseHTML(slug));
        $("#lm_" + scanIndex).specview(lObj);

        $(".lorikeet_help").on("click", function () {
            BuildHelpPanel.showHelp({
                helpText: LorikeetHelp.text,
                title: "Lorikeet MS/MS Viewer",
            });
        });

        //Wire the review buttons
        $(".unverify-scan").on("click", function () {
            $("#" + $(this).val())
                .removeClass()
                .addClass("panel panel-danger");
            rpm.publish("userUnverifiedSpectrum", {
                scanID: $(this).attr("spec_id"),
            });
        });
        $(".delete-scan").on("click", function () {
            $("#" + $(this).val()).remove();
        });
        $(".verify-scan").on("click", function () {
            $("#" + $(this).val())
                .removeClass()
                .addClass("panel panel-success");
            rpm.publish("userVerifiedSpectrum", {
                spectrum_title: RenderPSM.renderedSpectra[rpm.idMapping[$(this).val()]].Spectrum_title,
                spectrum_pkid: RenderPSM.renderedSpectra[rpm.idMapping[$(this).val()]].Spectrum_pkid,
                peptide_pkid: RenderPSM.renderedSpectra[rpm.idMapping[$(this).val()]].Peptide_pkid,
                sequence: RenderPSM.renderedSpectra[rpm.idMapping[$(this).val()]].sequence,
            });
        });
    };

    rpm.getSequences = function () {
        var sql = "SELECT peptides.id, peptides.sequence FROM peptides " + "WHERE peptides.id in (##PEPS##)";
        var pepList = "";
        var url =
            rpm.galaxyConfiguration.href +
            "/api/datasets/" +
            rpm.galaxyConfiguration.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";

        Object.keys(rpm.currentSpectra).forEach(function (k, idx) {
            if (idx > 0) {
                pepList += ',"' + rpm.currentSpectra[k].Peptide_pkid + '"';
            } else {
                pepList += '"' + rpm.currentSpectra[k].Peptide_pkid + '"';
            }
        });
        sql = sql.replace("##PEPS##", pepList);
        url += sql;

        $.get(url, function (data) {
            var seqByPep = {};
            data.data.slice(1).forEach(function (cv) {
                seqByPep[cv[0]] = cv[1];
            });
            Object.keys(rpm.currentSpectra).forEach(function (k) {
                rpm.currentSpectra[k].sequence = seqByPep[rpm.currentSpectra[k].Peptide_pkid];
            });

            //Can now actually render the MSMS
            Object.keys(rpm.currentSpectra).forEach(function (k) {
                rpm.renderSpectrum(k);
                rpm.renderedSpectra[k] = rpm.currentSpectra[k];
            });
        });
    };

    rpm.getModifications = function () {
        var sql =
            "SELECT PM.peptide_ref, PM.location, PM.residue, PM.monoisotopicMassDelta, PM.modType " +
            "FROM peptide_modifications PM WHERE PM.peptide_ref in (##PEPS##)";
        var pepList = "";
        var url =
            rpm.galaxyConfiguration.href +
            "/api/datasets/" +
            rpm.galaxyConfiguration.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";

        Object.keys(rpm.currentSpectra).forEach(function (k, idx) {
            if (idx > 0) {
                pepList += ',"' + rpm.currentSpectra[k].Peptide_pkid + '"';
            } else {
                pepList += '"' + rpm.currentSpectra[k].Peptide_pkid + '"';
            }
        });
        sql = sql.replace("##PEPS##", pepList);
        url += sql;

        $.get(url, function (data) {
            var modsByPepID = {};
            data.data.slice(1).forEach(function (cv) {
                var obj = {};
                obj.index = cv[1]; // === 0 ? 1 : cv[1]; 0 means n-term 1 means the first amino acid.
                obj.modMass = cv[3];
                obj.aminoAcid = cv[2];
                obj.modType = cv[4];

                if (!(cv[0] in modsByPepID)) {
                    modsByPepID[cv[0]] = [];
                }
                modsByPepID[cv[0]].push(obj);
            });
            Object.keys(rpm.currentSpectra).forEach(function (k) {
                rpm.currentSpectra[k].modifications = modsByPepID[rpm.currentSpectra[k].Peptide_pkid];
            });
            rpm.getSequences();
        });
    };

    rpm.buildPeaks = function () {
        var sqlSlug =
            "SELECT scans.mzValues, scans.intensities, scans.spectrumID, scans.spectrumTitle FROM scans \n" +
            'WHERE scans.spectrumTitle = "##SPECTRUM_TITLE##" AND scans.spectrumID = "##SPECTRUM_ID##"';
        //var pepList = '';
        var url =
            rpm.galaxyConfiguration.href +
            "/api/datasets/" +
            rpm.galaxyConfiguration.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        var sql = "";

        Object.keys(rpm.currentSpectra).forEach(function (k, idx) {
            if (idx > 0) {
                sql = sql + " UNION " + sqlSlug;
            } else {
                sql = sqlSlug;
            }
            sql = sql.replace("##SPECTRUM_TITLE##", rpm.currentSpectra[k].Spectrum_title);
            sql = sql.replace("##SPECTRUM_ID##", rpm.currentSpectra[k].Spectrum_pkid);
        });
        url += sql;

        $.get(url, function (data) {
            data.data.slice(1).forEach(function (cv) {
                var moz = JSON.parse(cv[0]);
                var intensity = JSON.parse(cv[1]);
                var cPeaks = (rpm.currentSpectra[cv[2] + "," + cv[3]].peaks = []);

                moz.forEach(function (cv, idx) {
                    cPeaks.push([cv, intensity[idx]]);
                });
            });
            rpm.getModifications();
        });
    };

    rpm.beginBulkRender = function (obj) {
        var sql =
            "SELECT psm_entries.id, psm_entries.spectrumID, psm_entries.spectrumTitle, " +
            '##MM##(psm_entries."##SCORE##") AS "##SCORE##" ' +
            "FROM psm_entries " +
            " WHERE " +
            " psm_entries.id IN (##ID_LIST##)" +
            "GROUP BY psm_entries.id";

        var rx_score = /##SCORE##/g;
        var m_m = obj.sortDir === "ASC" ? "MIN" : "MAX";
        var url =
            rpm.galaxyConfiguration.href +
            "/api/datasets/" +
            rpm.galaxyConfiguration.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";

        var escapedIDs = obj.peptideIDs
            .split(",")
            .map(function (x) {
                return '"' + x + '"';
            })
            .toString();

        sql = sql.replace("##ID_LIST##", escapedIDs);
        sql = sql.replace(rx_score, obj.scoreField);
        sql = sql.replace("##MM##", m_m);

        url = url + sql;
        $.get(url, function (data) {
            data.data.slice(1).forEach(function (cv) {
                var obj = {};
                obj.Peptide_pkid = cv[0];
                obj.Spectrum_pkid = cv[1];
                obj.Spectrum_title = cv[2];
                rpm.currentSpectra[obj.Spectrum_pkid + "," + obj.Spectrum_title] = obj;
            });
            rpm.buildPeaks();
        });
    };

    rpm.beginSinglePSM = function (obj) {
        var sql =
            "SELECT psm_entries.id, psm_entries.spectrumID, psm_entries.spectrumTitle " +
            "FROM psm_entries WHERE psm_entries.spectrumID = ##ID## AND psm_entries.spectrumTitle = ##TITLE## ";
        var url =
            rpm.galaxyConfiguration.href +
            "/api/datasets/" +
            rpm.galaxyConfiguration.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        sql = sql.replace("##ID##", '"' + obj.spectrumID + '"');
        sql = sql.replace("##TITLE##", '"' + obj.spectrumTitle + '"');
        url += sql;

        $.get(url, function (data) {
            data.data.slice(1).forEach(function (cv) {
                var obj = {};
                obj.Peptide_pkid = cv[0];
                obj.Spectrum_pkid = cv[1];
                obj.Spectrum_title = cv[2];
                rpm.currentSpectra[obj.Spectrum_pkid + "," + obj.Spectrum_title] = obj;
            });
            rpm.buildPeaks();
        });
    };

    rpm.manageClearing = function () {
        $("#clear_scans")
            .removeAttr("disabled")
            .on("click", function () {
                $("#lorikeet_zone")
                    .children()
                    .each(function () {
                        $(this).remove();
                    });
                $(this).attr("disabled", "disabled");
                $("#clear_scans").tooltip("hide");
            });
    };

    rpm.init = function (confObj) {
        rpm.galaxyConfiguration = confObj.galaxyConfiguration;

        rpm.subscribe("renderPSMForPeptide", function (arg) {
            rpm.currentSpectra = {};
            rpm.beginSinglePSM({
                peptideID: arg.pkid,
                spectrumID: arg.spectrumID,
                spectrumTitle: arg.spectrumTitle,
            });
            rpm.manageClearing();

            $("html, body").animate(
                {
                    scrollTop: $("#lorikeet_zone").offset().top,
                },
                1000
            );
        });

        rpm.subscribe("renderBestPSM", function (arg) {
            rpm.currentSpectra = {};
            rpm.beginBulkRender({
                peptideIDs: arg.peptideIDs,
                scoreField: arg.scoreField,
                sortDir: arg.sortDir,
            });
            $("html, body").animate(
                {
                    scrollTop: $("#lorikeet_zone").offset().top,
                },
                1000
            );
            rpm.manageClearing();
        });
    };

    return rpm;
})(RenderPSM || {}); // eslint-disable-line no-use-before-define
const ScoreFilterHelp = {
    text:
        '<p class="lead">Purpose</p><p>The Scores for Filtering panel allows you to search for PSMs ' +
        "based on individual PSM scores. From the <em>Score</em> dropdown, you can choose one or multiple " +
        "PSM scores for fitering.</p><hr>" +
        '<p class="lead">Actions</p><p><dl>' +
        "<dt>All conditions are true</dt><dd>Each chosen score filter must be true</dd>" +
        "<dt>Any condition is true</dt><dd>Any one score filter is true</dd>" +
        "<dt>Filter Now</dt><dd>Produces a table of PSMs fulfilling your score filtering.</dd></p>",
};

/**
 * Module for allowing user to filter PSMs based on one or more score value.
 */
//$('#score-filter-rows').children().length
var ScoreFilterModule = (function (sfm) {
    sfm.scoreSummary = null;
    sfm.guiDiv = "score_filter_div";

    sfm.buildScoreFilterRow = function (sName) {
        var rId = Math.random()
            .toString(36)
            .replace(/[^a-z]+/g, "");
        let divStr =
            '<div id="' +
            rId +
            '" class="row">' +
            '<div class="col-md-4 sf-name"><span class="lead">' +
            sName +
            "</span></div>" +
            '<div class="col-md-3">MIN: ' +
            sfm.scoreSummary[sName]["min_value"] +
            " MAX: " +
            sfm.scoreSummary[sName]["max_value"] +
            "  </div>";

        divStr +=
            '<div class="col-md-1"><select class="score_filter_op">' +
            '<option value="gt">&gt;</option><option value="gte">&ge;</option><option value="lt">&lt;</option><option value="lte">&le;</option>' +
            "</select></div>";

        divStr +=
            '<div class="col-md-2"><input class="sf-number" type="number"></div><div class="col-md-1"><span delete-row="' +
            rId +
            '" class="filter-remove" aria-hidden="true">X</span></div>';

        return divStr;
    };

    sfm.prepareDOM = function () {
        let dStr =
            '<div class="panel panel-default"><div class="panel-heading"><h3 class="panel-title" style="display: inline;">Scores for Filtering</h3>' +
            '<span id="score_filter_help" class="fa fa-question" style="padding: 5px"></span><span class="sr-only">Help?</span>' +
            '</div><div class="panel-body">' +
            '<div class="dropdown"><button class="btn btn-default dropdown-toggle" type="button" id="dropdown-score" data-toggle="dropdown">Score<span class="caret"></span></button>' +
            '<ul class="dropdown-menu" aria-labelledby="dropdown-score">##LIST##</ul></div>' +
            '<div id="score-filter-rows">' +
            "</div>" +
            '<input type="radio" value="AND" name="q-type" class="score_query_type"><label for="all-clause">All conditions are true (AND)</label>' +
            "<span>&nbsp;</span>" +
            '<input type="radio" value="OR" name="q-type" class="score_query_type" checked><label for="any-clause">Any condition is true (OR)</label>' +
            '</div><div class="panel-footer">' +
            '<button type="button" id="score-filter-now" class="btn btn-primary btn-sm">Filter Now</button>' +
            '<button type="button" id="score-filter-clear" class="btn btn-primary btn-sm">Clear Filter</button>' +
            "</div></div>";
        let scores = "";

        Object.keys(sfm.scoreSummary)
            .sort()
            .forEach(function (cv) {
                if (sfm.scoreSummary[cv]["score_type"] === "REAL") {
                    scores += '<li class="shadow score_filter_name">' + cv + "</li>";
                }
            });

        dStr = dStr.replace("##LIST##", scores);
        $("#" + sfm.guiDiv).append($.parseHTML(dStr));

        //wire
        $(".score_filter_name").on("click", function () {
            let divStr = sfm.buildScoreFilterRow($(this).text());
            $("#score-filter-rows").append(divStr);

            $(".filter-remove").on("click", function () {
                document.getElementById($(this).attr("delete-row")).remove();
            });
        });

        $("#score-filter-clear").on("click", function () {
            $("#" + sfm.guiDiv).empty();
            sfm.publish("UserClearedScoreFilter");
        });

        $("#score-filter-now").on("click", function () {
            let filterStr = " ";
            let ops = { gt: ">", gte: ">=", lt: "<", lte: "<=" };
            //$('input[name=q-type]:checked').val() =>"any-clause" | "all-clause"

            $("#score-filter-rows")
                .children()
                .each(function () {
                    filterStr +=
                        'psm_entries."' +
                        $(this).find(".sf-name").text() +
                        '" ' +
                        ops[$(this).find(".score_filter_op").val()] +
                        " " +
                        $(this).find(".sf-number").val() +
                        " " +
                        $("input[name=q-type]:checked").val() +
                        " ";
                });
            filterStr = filterStr.slice(0, filterStr.lastIndexOf(" " + $("input[name=q-type]:checked").val() + " "));

            sfm.publish("UserProvidesScoreFiltering", {
                fStr: filterStr,
                data: sfm.peptideObjs,
            });
        });

        $("#score_filter_help").on("click", function () {
            BuildHelpPanel.showHelp({
                helpText: ScoreFilterHelp.text,
                title: "Score Filter Help",
            });
        });
    };

    sfm.prepareScoreFiltering = function (data) {
        sfm.peptideObjs = data;
        sfm.prepareDOM();
    };

    sfm.init = function (confObj) {
        if (confObj["baseDiv"]) {
            sfm.guiDiv = confObj["baseDiv"];
        }

        sfm.subscribe("ScoreSummaryComplete", function (data) {
            sfm.scoreSummary = data;
        });

        sfm.subscribe("ScoreFilteringRequest", function (data) {
            sfm.prepareScoreFiltering(data);
        });

        sfm.subscribe("GlobalScoreFilterRequest", function () {
            sfm.peptideObjs = [];
            sfm.prepareDOM();
        });
    };

    return sfm;
})(ScoreFilterModule || {}); //eslint-disable-line no-use-before-define
/**
 * Manages the presentation of peptide sequences by file and by paging within file.
 */
var SequenceByFile = (function (sbf) {
    sbf.drawTable = function () {
        var domStr =
            '<div class="col-md-4" id="sequence_data_div"><div class="panel panel-default">' +
            '<div class="panel-heading">' +
            '<div class="row">' +
            '<div class="col-md-10">' +
            '<div class="panel-title">Filtering Sequences</div>' +
            "</div>" +
            '<div class="col-md-2"><button class="btn-xs clear-filter">X</button></div></div></div>' +
            '<div class="panel-body fixed-height-panel">';

        sbf.pagedData.forEach(function (cv) {
            if (cv[1].length > 0) {
                domStr +=
                    '<div class="row shadow filter-by" data-entries="' +
                    cv[1] +
                    '">' +
                    '<div class="col-md-12"><strong>' +
                    cv[0] +
                    "</strong></div>" +
                    '<div class="col-md-12"><small>' +
                    cv[1][0] +
                    "</small>" +
                    " to " +
                    "<small>" +
                    cv[1].slice(-1) +
                    "</small></div>" +
                    "</div>";
            }
        });

        domStr += "</div></div></div>";

        $("#" + sbf.elID).append($.parseHTML(domStr));

        $(".filter-by").on("click", function () {
            $(".filter-by").each(function () {
                if (!$(this).hasClass("shadow")) {
                    $(this).removeClass("used-for-filtering");
                    $(this).addClass("shadow");
                }
            });

            $(this).removeClass("shadow");
            $(this).addClass("used-for-filtering");
            sbf.filterFunc($(this).attr("data-entries"));
        });

        $(".clear-filter").on("click", function () {
            var od = $("#overview_div");
            $("#sequence_data_div").remove();

            od.removeClass("col-md-8");
            od.addClass("col-md-12");
            $("#data-table").DataTable().search("");
            $("#data-table").DataTable().draw();
        });
    };

    sbf.pageData = function () {
        sbf.pagedData = [];

        Object.keys(sbf.seqData).forEach(function (k) {
            var numPages = Math.floor(sbf.seqData[k].length / sbf.pageSize);
            var curPage;

            if (numPages === 0) {
                sbf.pagedData.push([k, sbf.seqData[k]]);
            } else {
                //Page the large sequence array.
                for (curPage = 0; curPage <= numPages; curPage += 1) {
                    sbf.pagedData.push([
                        k + " : Page " + (curPage + 1),
                        sbf.seqData[k].slice(curPage * sbf.pageSize, curPage * sbf.pageSize + sbf.pageSize),
                    ]);
                }
            }
        });
        sbf.drawTable();
    };

    sbf.init = function (confObj) {
        sbf.pageSize = confObj.pageSize || 50;
        sbf.seqData = confObj.seqData;
        sbf.elID = confObj.elID;
        sbf.pageData();
        sbf.filterFunc = confObj.callBack;
    };

    return sbf;
})(SequenceByFile || {}); // eslint-disable-line no-use-before-define
var VerifiedScans = (function (vs) {
    vs.psmEntrySQL =
        "SELECT psm_entries.* FROM psm_entries " +
        "WHERE psm_entries.spectrumID = ##ID## AND " +
        "psm_entries.spectrumTitle = ##TITLE##";

    vs.galaxyHeader = [];

    /**
     * key: spectrum ID
     * deleted: [T|F]
     * score:
     * sequence: peptide sequence
     * savedToGalaxy: [T|F]
     *
     * @type {{}}
     */
    vs.verifiedScans = {};

    vs.sendToGalaxy = function () {
        var fData = vs.galaxyHeader.join("\t") + "\n";
        var payload = {
            "files_0|url_paste": null,
            dbkey: "?",
            file_type: "tabular",
            "files_0|type": "upload_dataset",
            "files_0|space_to_tab": null,
            "files_0|to_posix_lines": "Yes",
        };
        var postData = {
            history_id: vs.galaxyConfiguration.historyID,
            tool_id: "upload1",
            inputs: null,
        };

        Object.keys(vs.verifiedScans).forEach(function (k) {
            if (!vs.verifiedScans[k].savedToGalaxy && !vs.verifiedScans[k].deleted) {
                fData += vs.verifiedScans[k].psmEntry.join("\t") + "\n";
                vs.verifiedScans[k].savedToGalaxy = true;
            }
        });

        payload["files_0|url_paste"] = fData;
        postData.inputs = JSON.stringify(payload);

        $.ajax({
            url: vs.galaxyConfiguration.href + "/api/tools",
            type: "POST",
            error: function () {
                console.log("ERROR in POSTING sequence file.");
            },
            success: function (data) {
                console.log("ID for file is " + data.outputs[0].id);
                VerifiedScans.verifiedScans = {};
                $("#scan-count-badge").text(VerifiedScans.eligibleScansCount());
            },
            data: postData,
        });
        vs.eligibleScansCount();
    };

    vs.eligibleScansCount = function () {
        var rVal = 0;

        Object.keys(vs.verifiedScans).forEach(function (cv) {
            if (!vs.verifiedScans[cv].deleted && !vs.verifiedScans[cv].savedToGalaxy) {
                rVal += 1;
            }
        });

        if (rVal === 0) {
            $("#scans-to-galaxy").attr("disabled", "disabled");
        } else {
            $("#scans-to-galaxy").removeAttr("disabled");
        }

        return rVal;
    };

    vs.removeScan = function (id) {
        if (id in vs.verifiedScans) {
            vs.verifiedScans[id].deleted = true;
            $("#scan-count-badge").text(vs.eligibleScansCount());
        }
    };

    vs.addScore = function (id) {
        var sql = vs.psmEntrySQL.replace("##ID##", '"' + id.split(",")[0] + '"');
        sql = sql.replace("##TITLE##", '"' + id.split(",")[1] + '"');
        var specID = id;

        $.get(vs.url + sql, function (data) {
            if (vs.galaxyHeader.length === 0) {
                vs.galaxyHeader = vs.galaxyHeader.concat(data.data[0]);
            }
            vs.verifiedScans[specID].psmEntry = data.data[1];
        });
    };

    vs.init = function (confObj) {
        vs.galaxyConfiguration = confObj.galaxyConfiguration;
        vs.url =
            vs.galaxyConfiguration.href +
            "/api/datasets/" +
            vs.galaxyConfiguration.datasetID +
            "?data_type=raw_data&provider=sqlite-table&headers=True&query=";

        /** arg ->
         *  spectrum_pkid: RenderPSM.currentSpectra[$(this).val()].Spectrum_pkid,
            peptide_pkid: RenderPSM.currentSpectra[$(this).val()].Peptide_pkid,
            spectrum_title:
            sequence: RenderPSM.currentSpectra[$(this).val()].sequence

         */
        vs.subscribe("userVerifiedSpectrum", function (arg) {
            if (!(arg.spectrum_pkid + "," + arg.spectrum_title in vs.verifiedScans)) {
                vs.verifiedScans[arg.spectrum_pkid + "," + arg.spectrum_title] = {
                    deleted: false,
                    savedToGalaxy: false,
                    sequence: arg.sequence,
                    peptide_pkid: arg.peptide_pkid,
                    spectrum_pkid: arg.spectrum_pkid,
                    spectrum_title: arg.spectrum_title,
                };
                vs.addScore(arg.spectrum_pkid + "," + arg.spectrum_title);
            } else {
                vs.verifiedScans[arg.spectrum_pkid + "," + arg.spectrum_title].deleted = false;
            }
            $("#scan-count-badge").text(vs.eligibleScansCount());
        });
        vs.subscribe("userUnverifiedSpectrum", function (arg) {
            vs.removeScan(arg.scanID);
        });

        $("#scans-to-galaxy")
            .on("click", function () {
                vs.sendToGalaxy();
                $("#scans-to-galaxy").tooltip("hide");
            })
            .attr("disabled", "disabled");
    };

    return vs;
})(VerifiedScans || {}); // eslint-disable-line no-use-before-define

const FeatureViewerHelp = {
    title: "Peptide-Protein Viewer Help",
    helpText:
        '<p class="lead">Purpose</p>' +
        "<p>The Peptide-Protein viewer displays the complete amino acid sequence for any selected protein within the sequence database used for matching MS/MS data.</p>" +
        "<ul>" +
        "<li>The bottom line shows an overview map of the entire sequence, along with any PSMs matched to the sequence colored in yellow bars.  The darker orange colored bar represents the peptide of interest selected originally from the Peptide Overview page which maps to this protein.</li>" +
        "<li>The lines above show a zoomed in view of selected regions of the protein sequence, with peptides from any PSMs below the overall protein sequence.  Amino acids identified with post-translational modifications are shaded in gray; amino acid variants as compared to a reference are colored in brown within the overall protein sequence map.</li>" +
        "<li>The thinner top line above the amino acid sequence depicts the coding region on the chromosome for the protein, with arrows indicating the direction of transcription for these genomic coordinates.  Breaks in this line indicate joining points of exons composing the mature gene product.</li>" +
        "</ul>" +
        '<p class="lead">Actions</p>' +
        "<dl>" +
        "<dt>Selected regions for viewing from the overall protein sequence</dt>" +
        "<dd>The gray rectangular box can be slid along the linear map of the protein sequence to view any given region of the protein sequence (and any corresponding PSMs) with higher resolution.</dd>" +
        "<dt>Opening Integrated Genomics Viewer (IGV)</dt>" +
        "<dd>Clicking on the thinner top line (with arrows indicating directionality) will open up the interactive IGV viewer, which can be used to map and characterize peptide sequences of interest against transcripts and genomic coding regions.   The IGV tool opens within the same browser window</dd>" +
        "</dl>",
};

//Code to manage creating and presenting peptide > protein > genome feature viewing
var featureViewer = {
    modalHTML:
        '<div class="modal fade" id="peptide_protein" tabindex="-1" data-backdrop="false" role="dialog"><div class="modal-dialog" role="document">' +
        '<div class="modal-content"><div class="modal-header">' +
        '<button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
        '<h4 class="modal-title">##TITLE##</h4></div>' +
        '<div class="modal-body">##BODY##</div>' +
        '<div class="modal-footer">' +
        '<button type="button" class="btn btn-default" data-dismiss="modal">Cancel</button>' +
        "</div> </div><!-- /.modal-content --> </div><!-- /.modal-dialog --> </div><!-- /.modal -->",

    requestMSMSRender: function (id) {
        featureViewer.publish("renderSingleMSMS", id);
    },

    //Gets CIGAR string from DB and transforms to JSON
    getVarianceData: function (accession, dbsID, pepID, nextFunc) {
        const proteinID = dbsID;
        const peptideID = pepID;
        const lAccession = accession;
        const lNextFunc = nextFunc;
        let url =
            featureViewer.galaxyConfiguration.href +
            "/api/datasets/##genomicDataset##?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        let sql = 'SELECT VA.cigar FROM variant_annotation VA WHERE VA.name = "' + accession + '"';

        url = url.replace("##genomicDataset##", featureViewer.cigarDataset);

        /**
         * '191=1X68=1X120=1X133=1X162=1X175=1X2=1X6=1X51=1X232=1X57=1*'
         *  matches
         [['191', '='],
         [ '1', 'X' ],
         [ '68', '=' ],
         [ '1', 'X' ],
         [ '120', '=' ],
         [ '1', 'X' ],
         [ '133', '=' ],
         [ '1', 'X' ],
         [ '162', '=' ],
         [ '1', 'X' ],
         [ '175', '=' ],
         [ '1', 'X' ],
         [ '2', '=' ],
         [ '1', 'X' ],
         [ '6', '=' ],
         [ '1', 'X' ],
         [ '51', '=' ],
         [ '1', 'X' ],
         [ '232', '=' ],
         [ '1', 'X' ],
         [ '57', '=' ] ]
         >

         substitutions: [{loc: 5, ref:'X'},{loc: 10, ref:'X'}],
         deletions: [{loc: 12, missing: 'MILK'}, {loc: 20, missing: 'ELV'}],
         additions: [{loc: 30, added: 'ELV'}],
         aligns: [[40, 150], [20,30]]

         */

        $.get(url + sql, function (data) {
            let cigar; // = data.data[1][0];
            const re = RegExp("([0-9]+)([=|X|M|I|D])", "g");
            let match;
            let obj = {
                substitutions: [],
                deletions: [],
                additions: [],
                aligns: [],
            };
            let idx = 0; //Starting offset into the protein sequence.
            let offset;

            if (data.data.length < 2) {
                if (lNextFunc) {
                    lNextFunc(lAccession, proteinID, peptideID);
                } else {
                    featureViewer.queryFeatures(proteinID, peptideID);
                }
            } else {
                cigar = data.data[1][0];

                while ((match = re.exec(cigar))) {
                    offset = idx + Number.parseInt(match[1]) - 1;
                    switch (match[2]) {
                        case "=":
                        case "M":
                            obj.aligns.push([idx, offset]);
                            break;
                        case "X":
                            obj.substitutions.push({ loc: offset });
                            break;
                        case "D":
                            break;
                        case "I":
                            break;
                    }
                    idx += Number.parseInt(match[1]);
                }
                featureViewer.variantInformation = obj;
                if (lNextFunc) {
                    lNextFunc(lAccession, proteinID, peptideID);
                } else {
                    featureViewer.queryFeatures(proteinID, peptideID);
                }
            }
        });
    },

    //http://localhost:8080/api/datasets/<genomicDataset>?data_type=raw_data&provider=sqlite-table&headers=True&query=
    getGenomicCoordinate: function (accession, dbsID, pepID, nextFunc) {
        var proteinID = dbsID;
        var peptideID = pepID;
        var fv = featureViewer;
        var url =
            fv.galaxyConfiguration.href +
            "/api/datasets/##genomicDataset##?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        var sql = 'SELECT feature_cds_map.* FROM feature_cds_map WHERE feature_cds_map.name = "' + accession + '"';
        url = url.replace("##genomicDataset##", fv.genomicDataset);

        //TODO: catch error here for no find.
        $.get(url + sql, function (data) {
            var names = data.data[0];

            featureViewer.genomicCoordinates = [];

            data.data.slice(1).forEach(function (d) {
                var obj = {};
                d.forEach(function (cv, idx) {
                    obj[names[idx]] = cv;
                });
                featureViewer.genomicCoordinates.push(obj);
            });
            if (nextFunc) {
                nextFunc(accession, proteinID, peptideID);
            } else {
                featureViewer.queryFeatures(proteinID, peptideID);
            }
        });
    },

    formatRawData: function (data) {
        var objD = {}; //temporary obj

        /**
         * 0: "start"
         1:"end"
         2:"isDecoy"
         3:"location"
         4:"name"
         5:"id"
         6:"sequence"
         7:"spectrumID"
         8:"spectrumTitle"
         9:"theoretical mass"
         */

        data.data.slice(1).forEach(function (d) {
            var key = d[5]; //the psm id
            if (!(key in objD)) {
                objD[key] = {};
                objD[key].peptidePKID = d[5];
                objD[key].seq = d[6].split("");
                objD[key].start = d[0];
                objD[key].end = d[1];
                objD[key].isDecoy = d[2];
                objD[key].mods = [];
                if (d[3] !== null) {
                    objD[key].mods.push([d[3], d[4]]); //[mod offset, mod name]
                }
                objD[key].spectrum_identID = d[7];
                objD[key].scores = [data.data[0].slice(10), d.slice(10)];
            } else {
                //Multiple mods exist on the peptide.
                if (d[3] !== null) {
                    objD[key].mods.push([d[3], d[4]]); //[mod offset, mod name]
                }
            }
        });

        return objD;
    },

    buildFeatures: function (data) {
        var sqlData = data.sqlData;
        var targetPeptide = featureViewer.peptideList[data.peptideID];
        var genomeArray = featureViewer.genomicCoordinates ? featureViewer.genomicCoordinates : null;

        var viewObject = {
            dbkey: featureViewer.dbkey,
            igvDiv: "igvDiv",
            baseDiv: "#" + featureViewer.baseDiv,
            genome: genomeArray,
            msmsRender: featureViewer.requestMSMSRender,
            protein: (function () {
                var obj = {};
                targetPeptide.proteins.forEach(function (d) {
                    if (d.protein_pkid.toString() === data.proteinID) {
                        obj.name = d.accession + " : " + d.description;
                        //Is there a sequence?
                        if (d.sequence) {
                            obj.sequence = d.sequence.split(""); //String to array.
                        } else {
                            obj.sequence = [];
                        }
                    }
                });
                return obj;
            })(),
            peptideList: [],
            variantInformation: featureViewer.variantInformation,
        };

        var feats = featureViewer.formatRawData(sqlData);

        Object.keys(feats).forEach(function (k) {
            var obj = {};
            var d = feats[k];
            obj.sequence = d.seq;
            obj.offset = d.start - 1; //index starts at 1, want an offset.
            obj.mismatch = [];
            obj.spectrum_identID = d.spectrum_identID;
            //Does this sequence differ from the protein sequence??
            (function () {
                var p = viewObject.protein.sequence;
                var f = obj.offset;
                obj.sequence.forEach(function (d, i) {
                    if (!(p[i + f] === d)) {
                        obj.mismatch.push(i);
                    }
                });
            })();

            obj.score = (function () {
                var s = "<dl>";
                d.scores[0].forEach(function (a, i) {
                    s += "<dt>" + a + "</dt><dd>" + d.scores[1][i] + "</dd>";
                });
                return s + "</dl>";
            })();

            if (d.mods.length > 0) {
                obj.mods = d.mods;
            }

            if (d.peptidePKID.toString() === data.peptideID) {
                //This is feature 1
                obj["class"] = "psm";
            } else {
                obj["class"] = "peptide";
            }
            viewObject.peptideList.push(obj);
        });

        $("#" + featureViewer.baseDiv).empty();
        featureViewer.view = new PSMProteinViewer(viewObject);
        featureViewer.view.renderSVG();
        $("#protein_viewer").prepend(
            '<button type="button" id="clear_map" class="btn btn-primary btn-sm">Clear Map</button><span id="fv_help"  class="fa fa-question" style="padding: 5px"></span>'
        );
        $("#clear_map").on("click", function () {
            $("#" + featureViewer.baseDiv).empty();
            document.getElementById("d3-tooltip").remove();
        });
        document.getElementById("fv_help").addEventListener("click", () => {
            BuildHelpPanel.showHelp(FeatureViewerHelp);
        });
    },

    queryFeatures: function (dbs_id, pep_id) {
        //The target peptide sequence
        var vScores = "";
        var peptideID = pep_id;
        var sql =
            "SELECT\n" +
            "  PE.start, PE.end, PE.isDecoy,\n" +
            "  PM.location, PM.name, PSM.id, PSM.sequence, PSM.spectrumID, PSM.spectrumTitle, ##SCORES##\n" +
            " FROM\n" +
            "  peptide_evidence PE,\n" +
            "  peptides P, psm_entries PSM\n" +
            "  LEFT OUTER JOIN peptide_modifications PM ON P.id = PM.peptide_ref\n" +
            " WHERE\n" +
            '  PE.dBSequence_ref = "' +
            dbs_id +
            '" AND\n' +
            "  PE.peptide_ref = P.id AND\n" +
            "  PSM.id = P.id";

        if (featureViewer.visibleScores) {
            featureViewer.visibleScores.forEach(function (cs) {
                vScores += 'PSM."' + cs + '",';
            });
            vScores = vScores.slice(0, vScores.lastIndexOf(","));
            sql = encodeURIComponent(sql.replace("##SCORES##", vScores));
        } else {
            sql = sql.replace("##SCORES##", "PSM.*");
        }

        featureViewer.queryFunc(sql, function (data) {
            featureViewer.buildFeatures({
                sqlData: data,
                peptideID: peptideID,
                proteinID: dbs_id,
            });
        });
    },

    showDOM: function () {
        var domS = featureViewer.modalHTML.replace("##TITLE##", "View Peptides in Protein");
        var s = "";
        var pl = featureViewer.peptideList;

        Object.keys(pl).forEach(function (d, idx) {
            s +=
                '<div class="fv-entry col-md-12"><div class="fv-seq">' +
                '<a role="button" data-toggle="collapse" href="#c_' +
                idx +
                '" aria-expanded="true" aria-controls="collapseOne">' +
                pl[d].sequence +
                "</a>" +
                "</div>";
            s += '<div id="c_' + idx + '" class="panel-collapse collapse" role="tabpanel">';
            //Iterate over the 1 .. n proteins this peptide is associated to.
            pl[d].proteins.forEach(function (pObj) {
                s += '<div class="fv-protein" dbs_id="' + pObj["protein_pkid"] + '" pep_id="' + d + '">';
                s += '<div class="col-md-12 p_accession">' + pObj["accession"] + "</div>";
                //s += '<div class="col-md-8 p_description">' + pObj['description'] + '</div>';
                s += "</div>";
            });
            s += "</div></div>";
        });

        domS = domS.replace("##BODY##", s);
        $("#master_modal").empty().append(domS);

        $(".fv-protein").on("click", function () {
            if ($(this).text().indexOf("REVERSED") > -1) {
                var s =
                    '<div class="alert alert-warning alert-dismissible" role="alert">' +
                    '<button type="button" class="close" data-dismiss="alert" aria-label="Close">' +
                    '<span aria-hidden="true">&times;</span></button>' +
                    "<strong>Sorry,</strong> I do not map reverse sequence, decoy proteins.</div>";
                $("#" + featureViewer.baseDiv).append(s);
                $("#peptide_protein").modal("hide");
                return;
            }

            //Does the user history have genomic coordinates, variant coordinates, none or both?
            if (featureViewer.genomicDataset) {
                if (featureViewer.cigarDataset) {
                    featureViewer.getGenomicCoordinate(
                        $(this).find(".p_accession").text(),
                        $(this).attr("dbs_id"),
                        $(this).attr("pep_id"),
                        featureViewer.getVarianceData
                    );
                } else {
                    featureViewer.getGenomicCoordinate(
                        $(this).find(".p_accession").text(),
                        $(this).attr("dbs_id"),
                        $(this).attr("pep_id"),
                        null
                    );
                }
            } else if (featureViewer.cigarDataset) {
                featureViewer.getVarianceData(
                    $(this).find(".p_accession").text(),
                    $(this).attr("dbs_id"),
                    $(this).attr("pep_id"),
                    null
                );
            } else {
                featureViewer.queryFeatures($(this).attr("dbs_id"), $(this).attr("pep_id"));
            }

            $("#peptide_protein").modal("hide");
        });

        $("#peptide_protein")
            .find(".btn-primary")
            .on("click", function () {
                $("#peptide_protein").modal("hide");
            });

        $("#peptide_protein").modal("show");
    },

    getProteinData: function (lst) {
        var s =
            "SELECT PE.peptide_ref, DB.id, DB.accession, DB.description, DB.sequence, DB.length " +
            " FROM db_sequence DB, peptide_evidence PE " +
            " WHERE PE.peptide_ref IN (##PEP_IDS##) AND PE.dBSequence_ref = DB.id";
        s = s.replace("##PEP_IDS##", lst.toString());

        featureViewer.queryFunc(s, function (data) {
            data.data.slice(1).forEach(function (d) {
                var obj = {};
                if (!("proteins" in featureViewer.peptideList[d[0]])) {
                    featureViewer.peptideList[d[0]]["proteins"] = [];
                }
                obj["protein_pkid"] = d[1];
                obj["accession"] = d[2];
                obj["description"] = d[3];
                obj["length"] = d[5];
                obj["sequence"] = d[4];
                featureViewer.peptideList[d[0]]["proteins"].push(obj);
            });
            featureViewer.showDOM();
        });
    },

    getPeptideSequences: function (lst) {
        var s = "SELECT peptides.id, peptides.sequence FROM peptides WHERE peptides.id IN (##IDs##)";
        var pepIDS = [];
        lst.split(",").forEach(function (cv) {
            pepIDS.push('"' + cv + '"');
        });
        s = s.replace("##IDs##", pepIDS.toString());

        featureViewer.queryFunc(s, function (data) {
            featureViewer.peptideList = {};
            data.data.slice(1).forEach(function (d) {
                featureViewer.peptideList[d[0]] = {};
                featureViewer.peptideList[d[0]]["sequence"] = d[1];
            });
            featureViewer.getProteinData(pepIDS);
        });
    },

    init: function (obj) {
        featureViewer.galaxyConfiguration = obj.galaxyConfiguration;
        featureViewer.baseDiv = obj.baseDiv;
        featureViewer.queryFunc = obj.queryFunc;
        featureViewer.variantInformation = {
            substitutions: [],
            deletions: [],
            additions: [],
            aligns: [],
        };
        featureViewer.dbkey = obj.galaxyConfiguration.dbkey;

        //Do we have Genomic metadata?
        (function () {
            var url =
                featureViewer.galaxyConfiguration.href +
                "/api/histories/" +
                featureViewer.galaxyConfiguration.historyID +
                "/contents/";

            $.get(url, function (data) {
                //Need to check if delete = True
                data.forEach(function (d) {
                    if (d["extension"] === "sqlite" && d["deleted"] === false && d["visible"] === true) {
                        $.get(featureViewer.galaxyConfiguration.href + d["url"], function (data) {
                            if (data["peek"].indexOf("feature_cds_map") > -1) {
                                featureViewer.genomicDataset = data["id"];
                            }
                            if (data["peek"].indexOf("variant_annotation") > -1) {
                                featureViewer.cigarDataset = data["id"];
                            }
                        });
                    }
                });
            });
        })();

        featureViewer.subscribe("VisibleScores", function (arg) {
            //These are the scores the user wants to see
            featureViewer.visibleScores = arg;
        });

        featureViewer.subscribe("userRequestsViewInProteins", function (arg) {
            //Get sequences and start the process
            featureViewer.getPeptideSequences(arg);
        });
    },
};
/**
 * Module for basic SQL queries against galaxy.
 * @type {{}}
 */
var gQuery = {
    href: null,
    dataSetID: null,

    query: function (sql, callBackFN) {
        var url = gQuery.href;
        url += "/api/datasets/" + gQuery.datasetID + "?data_type=raw_data&provider=sqlite-table&headers=True&query=";
        url += sql;

        $.get(url, function (data) {
            callBackFN(data);
        }).fail(function (jqXHR) {
            alert("ERROR: query \n" + jqXHR.responseText + " \nfailed.");
        });
    },

    init: function (confObj) {
        gQuery.href = confObj.href;
        gQuery.datasetID = confObj.datasetID;
    },
};
/**
 * Generate JSON of peptide sequences by file for filtering.
 */
var PeptideSequenceFilter = (function (psf) {
    psf.pepsByFile = {};
    psf.candidateFiles = [];
    psf.timer;

    psf.historyContents = function (url) {
        return new Promise(function (resolve, reject) {
            psf.timer = setTimeout(function () {
                alert(
                    "Sorry, Galaxy is not responding. I have waited as long as I can. Grab a coffee, relax, and refresh the app in a bit."
                );
                reject(new Error("Requesting data from Galaxy timeout"));
            }, 30000);
            $.get(url, resolve);
        });
    };

    psf.pepAJAX = function (fObj, cb) {
        var url =
            psf.galaxyConfiguration.href +
            "/api/histories/" +
            psf.galaxyConfiguration.historyID +
            "/contents/" +
            fObj.obj.id +
            "/display";
        var cb_fn = cb;
        var obj = fObj;
        $.get(url, function (data) {
            var cleanSequence = [];

            data.split("\n").forEach(function (v) {
                var rx = new RegExp("[^a-z]|sequence", "i"); //"sequence" cannot be in the string bc the column is named seqeunce????
                if (!v.match(rx)) {
                    if (v.length > 0) {
                        cleanSequence.push(v);
                    }
                }
            });
            psf.pepsByFile[obj.obj.name] = cleanSequence;

            cb_fn();
        });
    };

    psf.peptideFileContents = function (fObj) {
        var obj = fObj;
        return new Promise(function (resolve) {
            psf.pepAJAX(obj, resolve);
        });
    };

    /**
     * Process REST return of list of user's current history.
     * Want to find any entries that are not deleted and tabular.
     */
    psf.processHistoryList = function (data) {
        var availableFiles = [];
        clearTimeout(psf.timer);
        data.forEach(function (cv) {
            if (cv.extension === "tabular" && !cv.deleted) {
                availableFiles.push({
                    name: cv.name,
                    obj: cv,
                });
            }
        });
        psf.candidateFiles = availableFiles;
        psf.publish("CandidateFilesAvailable", psf.candidateFiles);
        psf.subscribe("ParseCandidateFiles", function (data) {
            psf.parseCandidateFiles(data);
        });

        //TODO: Stop here and present available files to user.
    };

    psf.parseCandidateFiles = function (availableFiles) {
        //promise chain to ensure that all tabular files are processed before letting user access
        availableFiles
            .map(psf.peptideFileContents)
            .reduce(
                function (chain, filePromise) {
                    return chain.then(function () {
                        return filePromise;
                    });
                },
                Promise.resolve() //fulfilled Promise to start the reduce chain.
            )
            .then(function () {
                psf.publish("CandidateFilesParsed", {
                    data: psf.pepsByFile,
                });
            });
    };

    psf.loadData = function () {
        var url = psf.galaxyConfiguration.href + "/api/histories/" + psf.galaxyConfiguration.historyID + "/contents";
        var prHistory = psf.historyContents(url);
        prHistory.then(psf.processHistoryList);
    };

    psf.init = function (confObj) {
        psf.galaxyConfiguration = confObj.galaxyConfiguration;
        psf.subscribe("dataTableInitialized", function () {
            psf.loadData();
        });
    };

    return psf;
})(PeptideSequenceFilter || {}); // eslint-disable-line no-use-before-define

/**
 * General utility for building and presenting modal help
 */
var BuildHelpPanel = (function (bhp) {
    bhp.domStr =
        '<div id="user_help_modal" class="modal fade" tabindex="-1" role="dialog">\n' +
        '  <div class="modal-dialog" role="document">\n' +
        '    <div class="modal-content">\n' +
        '      <div class="modal-header">\n' +
        '        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>\n' +
        '        <h4 class="modal-title">#MODAL_TITLE#</h4>\n' +
        "      </div>\n" +
        '      <div class="modal-body">\n' +
        "        <p>#HELP_TEXT#</p>\n" +
        "      </div>\n" +
        '      <div class="modal-footer">\n' +
        '        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>\n' +
        "      </div>\n" +
        "    </div><!-- /.modal-content -->\n" +
        "  </div><!-- /.modal-dialog -->\n" +
        "</div><!-- /.modal -->";

    bhp.finalDom = "";

    bhp.showHelp = function (confObj) {
        bhp.finalDom = bhp.domStr.replace("#HELP_TEXT#", confObj.helpText);
        bhp.finalDom = bhp.finalDom.replace("#MODAL_TITLE#", confObj.title);
        $("#master_modal").empty().append(bhp.finalDom);
        $("#user_help_modal").modal("show");
    };
    return bhp;
})(BuildHelpPanel || {});

/**
 * Handle general configurations for the app.
 */
var ConfigModal = (function (cm) {
    cm.userDefaults = {
        tool_tip_visible: true,
    };

    cm.domStr =
        '<div id="app_config_modal" class="modal fade" tabindex="-1" role="dialog">\n' +
        '  <div class="modal-dialog" role="document">\n' +
        '    <div class="modal-content">\n' +
        '      <div class="modal-header">\n' +
        '        <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>\n' +
        '        <h4 class="modal-title">Configuration</h4>\n' +
        "      </div>\n" +
        '      <div class="modal-body">' +
        "       <div>" +
        '        <input type="checkbox" id="config_tooltip" class="app_config" value="tool_tip_visible"/>' +
        '        <label for="config_tooltip">Enable tooltips</label>' +
        "       </div></div>" +
        '      <div class="modal-footer">\n' +
        '        <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>' +
        '        <button id="save_config_change" type="button" class="btn btn-default">Save Changes</button>' +
        "      </div>\n" +
        "    </div><!-- /.modal-content -->\n" +
        "  </div><!-- /.modal-dialog -->\n" +
        "</div><!-- /.modal -->";

    cm.showConfig = function () {
        $("#master_modal").empty().append(cm.domStr);

        Object.keys(cm.userDefaults).forEach(function (k) {
            var s = 'input[value="' + k + '"]';
            document.querySelector(s).checked = cm.userDefaults[k];
        });

        $("#save_config_change").on("click", function () {
            var configs = document.querySelectorAll('input[class="app_config"]');
            var msgObj = {};
            configs.forEach(function (cv) {
                msgObj[cv.getAttribute("value")] = cv.checked;
                cm.userDefaults[cv.getAttribute("value")] = cv.checked;
            });
            cm.publish("UserChangedDefaults", msgObj);
            $("#app_config_modal").modal("hide");
        });

        $("#app_config_modal").modal("show");
    };

    return cm;
})(ConfigModal || {});

/**
 * There can be many, many scores available to the user. This code allows for
 * managing which scores are visible.
 *
 * By default, only scores that are present on > 85% of PSM entries are visible.
 */
var ScoreDefaults = (function (sd) {
    sd.defaultThreshold = 0.85;
    sd.scoreProperties = {};

    sd.resetDOM = function () {
        $("#score_default_div").empty();
        $("#score_defaults").removeAttr("   disabled");
    };

    sd.modifyVisibleScores = function () {
        var rVal = [];
        $("div .score_name").each(function () {
            sd.scoreProperties[$(this).text()] = $(this).hasClass("selected");
        });

        Object.keys(sd.scoreProperties).forEach(function (key) {
            if (sd.scoreProperties[key]) {
                rVal.push(key);
            }
        });
        sd.publish("VisibleScores", rVal);

        sd.resetDOM();
    };

    sd.showDOM = function () {
        let domStr =
            '<div class="col-md-12" id="score_choice_div"><div class="panel panel-default">' +
            '<div class="panel-heading">' +
            '<div class="row">' +
            '<div class="col-md-8">' +
            '<div class="panel-title"><strong>Choose Score Visibility</strong></div>' +
            "</div>" +
            '<div class="col-md-2"><button id="set_score_defaults_btn" class="btn">Set Defaults</button></div>' +
            '<div class="col-md-2"><button id="clear_div_btn" class="btn">Cancel</button></div></div></div>' +
            '<div class="panel-body fixed-height-panel col-md-12"><div class="row">';

        //Build out the panel body
        var scoreStr = "";
        Object.keys(sd.scoreProperties).forEach(function (s, idx) {
            if (idx === 0) {
                scoreStr = '<div class="row">';
            }
            if (idx % 2 === 0 && idx > 0) {
                scoreStr += '<div class="row">';
            }

            if (sd.scoreProperties[s]) {
                scoreStr += '<div class="col-md-5 score_name selected"><strong>' + s + "</strong></div>";
            } else {
                scoreStr += '<div class="col-md-5 score_name"><strong>' + s + "</strong></div>";
            }

            if (idx % 2 > 0) {
                scoreStr += "</div>";
            }
        });

        domStr += scoreStr + "</div></div></div></div>";
        $("#score_default_div").append(domStr);
        $("div .score_name").on("click", function () {
            $(this).toggleClass("selected");
        });
        $("#clear_div_btn").on("click", function () {
            sd.resetDOM();
        });
        $("#set_score_defaults_btn").on("click", sd.modifyVisibleScores);
    };

    sd.prepareDOM = function () {
        let b = $("#score_defaults");
        b.removeAttr("disabled");
        b.on("click", function () {
            $("#score_defaults").attr("disabled", "disabled");
            sd.showDOM();
            $("#score_defaults").tooltip("hide");
        });
    };

    sd.init = function () {
        sd.subscribe("RequestVisibleScores", function () {
            var rVal = [];
            Object.keys(sd.scoreProperties).forEach(function (key) {
                if (sd.scoreProperties[key]) {
                    rVal.push(key);
                }
            });
            sd.publish("VisibleScores", rVal);
            sd.prepareDOM();
        });

        sd.subscribe("RankedScoresAvailable", function (arg) {
            //arg is an array of [scorename, pct coverage] ordered by pct coverage desc
            arg.forEach(function (s) {
                if (s[1] > sd.defaultThreshold) {
                    //By default show
                    sd.scoreProperties[s[0]] = true;
                } else {
                    //By default hide
                    sd.scoreProperties[s[0]] = false;
                }
            });
        });
        sd.publish("RequestRankedScores");
    };

    return sd;
})(ScoreDefaults || {}); //eslint-disable-line no-use-before-define

const MVPHelp = {
    text:
        '<p class="lead">Purpose</p><p>The Galaxy-based MVP visualization plugin enables viewing of results produced from workflows integrating genomic sequencing data and mass spectrometry (MS)-based proteomics data, commonly known as proteogenomics.  The multi-functional tool allows for organization and filtering of results, quality assessment of tandem mass spectrometry (MS/MS) data matched to peptide sequences, and visualization of data at both the protein and gene level.  A user can, with relatively few keystrokes, filter and order large datasets down to a manageable subset. Due to the tools use of server-side caching, large data sets are handled as quickly as small datasets.</p>' +
        "<p>MVP incorporates the Lorikeet viewer for visualizing MS/MS data as well as the Integrated Genomics Viewer (IGV) for mapping peptide and protein sequences to genomic coordinates, essential for characterizing protein sequence variants arising from gene and transcript variants.</p>" +
        "<p>The starting page provides peptide-centric overview of peptide spectral matches (PSMs) identified using sequence database searching against a protein sequence database, and summarized in a MZSqlite-formatted input file. From this page, a user can carry-out a number of operations, including:</p>" +
        "<ul><li>PSMs linked to unique peptide sequences of interest</li>" +
        "<li>PSMs passing scoring thresholds to ensure quality</li>" +
        "<li>Visualization of MS/MS annotation and quality for selected PSMs</li>" +
        "<li>Mapping PSMs to overall protein sequences</li>" +
        "<li>Mapping protein sequences to genomic coordinates</li>" +
        "<li>Visualization of protein sequence variants comparison to reference protein and gene sequences</li>" +
        "<li>Archiving of PSMs of interest and automated transfer of selected results back to Galaxy for further analyses</li>" +
        "<li>Archiving of visualizations</li></ul>" +
        '<hr><p class="lead">Actions</p><p><dl>' +
        "<dt>ID Scores</dt><dd>Clicking on this button provides a view of the distribution of PSMs for the entire dataset based on false discovery rate (FDR) estimates of the sequence database searching tools used to produce PSMs, if available.  This shows the percent of PSMs passing FDR thresholds dependent on assigned PSM scores. Clicking on the button a second time removes the graph.</dd>" +
        "<dt>ID Features</dt><dd>Clicking on this button generates the list of scoring metrics produced by the sequence database searching software used to generate PSMs.  The user can select the scoring metrics to be shown when examining in detail any PSMs matching to peptide sequences of interest.</dd>" +
        "<dt>Export Scans</dt><dd>Clicking this button automatically exports selected peptide sequences and associated MS/MS data back to Galaxy, where it is shown as a new item in the active History in tabular format</dd>",
};

/**
 * Mediator pattern as main application.
 */
var MVPApplication = (function (app) {
    app.debug = true; //Listen in on event publish
    app.galaxyConfiguration = {};
    app.events = {};
    app.userDefaults = null;

    //Hold some basic defaults. User can override.
    app.app_defaults = {
        tool_tip_visible: true,
    };

    /**
     * Allows objects to subscribe to an event.
     * @param event name
     * @param fn call back function for event
     * @returns {subscribe}
     */
    app.subscribe = function (event, fn) {
        if (!app.events[event]) {
            app.events[event] = [];
        }
        app.events[event].push({
            context: this,
            callback: fn,
        });
        return this;
    };

    /**
     * Unsubscribes from the event queue
     * @param event
     * @param fn
     */
    app.unsubscribe = function (event) {
        app.event[event].filter(
            function (cv) {
                return this === cv.context;
            }.bind(this)
        );
    };

    /**
     * Allows objects to broadcast the occurrence of an event.
     * All subscribers to the event will have their callback functions
     * called.
     *
     * @param event name
     * @returns {*}
     */
    app.publish = function (event) {
        var args, subscription;

        if (!app.events[event]) {
            return false;
        }
        args = Array.prototype.slice.call(arguments, 1);

        if (app.debug) {
            console.log("APP PUBLISH: " + event + " ARGS: " + args);
        }

        app.events[event].map(function (cv) {
            subscription = cv;
            subscription.callback.apply(subscription.context, args);
        });
        return this;
    };

    /**
     * Adds the subscribe and publish functions to an object
     * @param obj
     */
    app.installTo = function (obj) {
        obj.subscribe = app.subscribe;
        obj.publish = app.publish;
        obj.unsubscribe = app.unsubscribe;
    };

    //Load modules
    app.init = function (confObj) {
        this.galaxyConfiguration = confObj;

        $("#dataset_name").text(this.galaxyConfiguration.dataName);

        this.subscribe("ScoreSummaryComplete", function () {
            console.log("Score summary complete, begin table construction");
            ScoreDefaults.init();
            PeptideView.init({
                galaxyConfiguration: this.galaxyConfiguration,
                baseDiv: "overview_div",
            });
        });

        this.subscribe("FDRDataPrepared", function () {
            $("#fdr_module")
                .removeAttr("disabled")
                .on("click", function () {
                    $("#fdr_div").toggle();
                    $("html, body").animate(
                        {
                            scrollTop: $("#fdr_div").offset().top,
                        },
                        500
                    );
                    $("#fdr_module").tooltip("hide");
                });
        });

        this.subscribe("UserChangedDefaults", function (data) {
            Object.keys(data).forEach(function (k) {
                console.log("UserChangedDefaults " + k + " : " + data[k]);
                app.app_defaults[k] = data[k];
                if (k === "tool_tip_visible") {
                    if (data[k]) {
                        $('[data-toggle="tooltip"]').tooltip();
                    } else {
                        $('[data-toggle="tooltip"]').tooltip("destroy");
                    }
                }
            });
        });

        this.installTo(ScoreSummary);
        this.installTo(PeptideView);
        this.installTo(RenderPSM);
        this.installTo(VerifiedScans);
        this.installTo(PeptideSequenceFilter);
        this.installTo(featureViewer);
        this.installTo(gQuery);
        this.installTo(ScoreDefaults);
        this.installTo(FDRPresentation);
        this.installTo(ScoreFilterModule);
        this.installTo(IGVManager);
        this.installTo(IGVTrackManager);
        this.installTo(BuildHelpPanel);
        this.installTo(ConfigModal);

        ScoreFilterModule.init({});

        gQuery.init({
            href: this.galaxyConfiguration.href,
            datasetID: this.galaxyConfiguration.datasetID,
        });

        featureViewer.init({
            galaxyConfiguration: this.galaxyConfiguration,
            baseDiv: "protein_viewer",
            queryFunc: gQuery.query,
            dbkey: this.galaxyConfiguration.dbkey,
        });

        RenderPSM.init({
            galaxyConfiguration: this.galaxyConfiguration,
        });

        VerifiedScans.init({
            galaxyConfiguration: this.galaxyConfiguration,
        });

        PeptideSequenceFilter.init({
            galaxyConfiguration: this.galaxyConfiguration,
        });

        ScoreSummary.init({
            href: this.galaxyConfiguration.href,
            datasetID: this.galaxyConfiguration.datasetID,
        });

        IGVManager.init({
            galaxyConfiguration: this.galaxyConfiguration,
        });

        IGVTrackManager.init({
            galaxyConfiguration: this.galaxyConfiguration,
        });

        if ("protein_detection_protocol" in confObj.tableRowCount) {
            FDRPresentation.init({
                href: this.galaxyConfiguration.href,
                datasetID: this.galaxyConfiguration.datasetID,
                divID: "fdr_div",
                callBackFN: PeptideView.reBuildTable,
            });
        }
        $('[data-toggle="tooltip"]').tooltip();

        $("#mvp_help").on("click", function () {
            BuildHelpPanel.showHelp({
                helpText: MVPHelp.text,
                title: "Multi-omics Visualization Platform (MVP) Viewer",
            });
        });

        $("#mvp_full_window").on("click", function () {
            $("#mvp_full_window").tooltip("hide");
            window.open("#", "_blank");
        });

        $("#mvp_config").on("click", function () {
            ConfigModal.showConfig();
        });
    };

    return {
        run: function (confbj) {
            app.init(confbj);
        },
    };
})(MVPApplication || {}); // eslint-disable-line no-use-before-define

window.MVPApplication = MVPApplication;
