/***

Chimera interactions viewer. It reads sqlite file 
and shows up the list of interactions and a summary
in multiple plots, comic alignments

***/

var RNAInteractionViewer = (function(riv) {
  riv.configObject = null;
  riv.model = null;
  riv.nIncrement = 25;
  riv.counterRecords = 0;
  riv.minQueryLength = 3;
  riv.type1 = null;
  riv.type2 = null;
  riv.symbol1 = null;
  riv.symbol2 = null;
  riv.exportColNames =
    "tagid, txid1, txid2, geneid1, geneid2, symbol1, symbol2, region1, region2, tx_pos_start1, tx_pos_end1, tx_pos_strand1, length1, tx_pos_start2, tx_pos_end2, tx_pos_strand2, length2, read_info, genomic_pos1, genomic_pos2, locus1, locus2, groupid1, groupid2, tpm1, tpm2, score1, score2, score, sequences, hybrid, hybrid_pos, mfe";
  riv.$elLoader = $(".loader");

  /** Create a url with the specified query */
  riv.formUrl = (configObject, query) => {
    return (
      configObject.href +
      "/api/datasets/" +
      configObject.datasetID +
      "?data_type=raw_data&provider=sqlite-table&headers=True" +
      query
    );
  };

  /** Make an ajax call with a url */
  riv.ajaxCall = (url, callBack, configOb = {}) => {
    riv.$elLoader.show();
    $.get(url, data => {
      callBack(data, configOb);
    });
  };

  /** Load sqlite dataset records on first load of the visualization */
  riv.loadData = configObject => {
    let query =
        "&query=SELECT region1, region2, symbol1, symbol2, tpm1, tpm2 FROM " +
        configObject.tableNames["name"] +
        " group by tagid",
      url = riv.formUrl(configObject, query);
    riv.configObject = configObject;
    riv.$elLoader.show();
    riv.ajaxCall(url, riv.createUI, configObject);
  };

  /** Create the UI when a sqlite file is clicked */
  riv.createUI = data => {
    let templateText = "",
      $elContainer = $(".main-container");
    templateText = riv.createInteractionTemplate();
    $elContainer.append(templateText);
    $elContainer.find(".one-sample").show();
    riv.registerPageEvents();
    riv.loadRNATypes(data);
    riv.$elLoader.hide();
  };

  /** Register events for UI elements */
  riv.registerPageEvents = () => {
    let $elSearchGene = $(".search-gene"),
      $elSort = $(".rna-sort"),
      $elFilterVal = $(".filter-value"),
      $elExport = $(".export-results"),
      $elBackHome = $(".back-home"),
      $elResetFilters = $(".reset-filters"),
      $elSummary = $(".rna-summary"),
      $elCheckAll = $(".check-all-interactions"),
      $elSearchGeneImage = $(".search-gene-image"),
      $elFilterValueImage = $(".filter-value-image");
    $elbtnGetInteractions = $("#btnGetInteractions");
    $elbtnPrev = $("#btnPrev");
    $elbtnNext = $("#btnNext");

    // search box
    $elSearchGeneImage.off("click").on("click", e => {
      let query = $elSearchGene.val();
      if (query.length >= riv.minQueryLength) {
        riv.cascadeSearch();
      }
    });

    // search icon in the search box
    $elFilterValueImage.off("click").on("click", e => {
      let query = $elFilterVal.val();
      if (query.length > 0) {
        riv.cascadeSearch();
      }
    });

    // search box on enter click
    $elSearchGene.off("keyup").on("keyup", e => {
      if (e.which === 13 || e.keyCode === 13) {
        // search on enter click
        riv.cascadeSearch();
      }
    });

    // onchange event for sort
    $elSort.off("change").on("change", e => {
      riv.cascadeSearch();
    });

    // fetch records using filter's value
    $elFilterVal.off("keyup").on("keyup", e => {
      if (e.which === 13 || e.keyCode === 13) {
        // search on enter click
        riv.cascadeSearch();
      }
    });

    // export selected records
    $elExport.off("click").on("click", e => {
      riv.fetchAndExport();
    });

    // summary event
    $elSummary.off("click").on("click", e => {
      riv.getInteractionsSummary(e);
    });

    // check all event
    $elCheckAll.off("click").on("click", e => {
      riv.checkAllInteractions(e);
    });

    // get records for the selected types
    $elbtnGetInteractions.off("click").on("click", e => {
      riv.makeInteractionsQ(e);
    });

    // get previous records
    $elbtnPrev.off("click").on("click", e => {
      riv.fetchPrevInteractions(e);
    });

    // get next records
    $elbtnNext.off("click").on("click", e => {
      riv.fetchNextInteractions(e);
    });

    $elBackHome.off("click").on("click", e => {
      riv.backHome(e);
    });
  };

  /** Go back to home page */
  riv.backHome = e => {
    let config = {
      href: riv.configObject.href,
      dataName: riv.configObject.dataName,
      datasetID: riv.configObject.datasetID,
      tableNames: {
        name: riv.configObject.tableNames["name"]
      }
    };
    riv.loadData(config);
    riv.showLandingPage();
  };

  /** Get next set of records in the left panel using pagination */
  riv.fetchNextInteractions = () => {
    if (riv.counterRecords + riv.nIncrement < riv.model.length) {
      riv.counterRecords += riv.nIncrement;
      riv.resetSummary();
      riv.resetFilters();
      riv.resetCheckAll();
      riv.buildInteractionsPanel();
    }
  };

  /** Get previous set of records in the left panel using pagination */
  riv.fetchPrevInteractions = e => {
    if (riv.counterRecords > 0) {
      riv.counterRecords -= riv.nIncrement;
      riv.resetSummary();
      riv.resetFilters();
      riv.resetCheckAll();
      riv.buildInteractionsPanel();
    }
  };

  /** Remove existing elements in dropdowns */
  riv.clearDropdown = ddId => {
    $("#" + ddId)
      .find("option")
      .remove()
      .end();
  };

  /** Fill the dropdowns of type on the first page */
  riv.fillDropdowns = (ddId, list, openText) => {
    riv.clearDropdown(ddId);
    let select = document.getElementById(ddId);
    select.options = [];
    select.options[select.options.length] = new Option(openText, "-1");
    select.options[select.options.length] = new Option("all", "all");
    _.each(list, s1 => {
      select.options[select.options.length] = new Option(s1, s1);
    });
  };

  /** Get topk symbols based on highest gene expression */
  riv.getTopKItems = (dict, topK) => {
    let values = [],
      labels = [],
      items = Object.keys(dict).map(key => {
        return [key, dict[key]];
      });
    items.sort((first, second) => {
      return second[1] - first[1];
    });
    items = items.slice(0, topK);
    _.each(items, item => {
      values.push(item[1]);
      labels.push(item[0]);
    });
    return { values: values, names: labels };
  };

  /** Merge combined regions - a:b and b:a */
  riv.filterCombinedRegions = combineRegions => {
    let slicedRegionPie = {};
    for (let key in combineRegions) {
      let regions = key.split(":"),
        revKey = regions[1] + ":" + regions[0];
      if (revKey in combineRegions) {
        slicedRegionPie[key] =
          parseInt(combineRegions[key]) + parseInt(combineRegions[revKey]);
        delete combineRegions[revKey];
      } else {
        slicedRegionPie[key] = combineRegions[key];
      }
    }
    return slicedRegionPie;
  };

  /** Get the symbol with the maximum gene expression */
  riv.collectTopSymGeneExp = (symbolGeneExp, sym1, sym2, tpm1, tpm2) => {
    if (sym1 in symbolGeneExp === true) {
      let currentTpm = symbolGeneExp[sym1];
      if (currentTpm < tpm1) {
        symbolGeneExp[sym1] = parseFloat(tpm1);
      }
    } else {
      symbolGeneExp[sym1] = parseFloat(tpm1);
    }
    if (sym2 in symbolGeneExp === true) {
      let currentTpm = symbolGeneExp[sym2];
      if (currentTpm < tpm2) {
        symbolGeneExp[sym2] = parseFloat(tpm2);
      }
    } else {
      symbolGeneExp[sym2] = parseFloat(tpm2);
    }
    return symbolGeneExp;
  };

  /** Load both the types of RNA */
  riv.loadRNATypes = records => {
    let recordsData = records.data,
      topGeneExpressed = 50,
      symbolGeneExpTop = {};
    if (recordsData && recordsData.length > 1) {
      let nRecords = recordsData.length,
        typ1 = [],
        typ2 = [],
        typ1Pie = {},
        typ2Pie = {},
        regionPie = {},
        symbolGeneExp = {};
      recordsData = recordsData.slice(1);
      _.each(recordsData, item => {
        let tName1 = item[0],
          tName2 = item[1],
          sym1 = item[2],
          sym2 = item[3],
          tpm1 = item[4],
          tpm2 = item[5],
          combinedRegions = "";
        typ1.push(tName1);
        typ2.push(tName2);
        typ1Pie[tName1] = (typ1Pie[tName1] || 0) + 1;
        typ2Pie[tName2] = (typ2Pie[tName2] || 0) + 1;
        combinedRegions = tName1 + ":" + tName2;
        regionPie[combinedRegions] = (regionPie[combinedRegions] || 0) + 1;
        symbolGeneExp = riv.collectTopSymGeneExp(
          symbolGeneExp,
          sym1,
          sym2,
          tpm1,
          tpm2
        );
      });
      // get unique types
      typ1Uniq = Array.from(new Set(typ1));
      typ2Uniq = Array.from(new Set(typ2));
      // fill dropdowns with unique types
      riv.fillDropdowns("type1", typ1Uniq, "--Choose RNA region1--");
      riv.fillDropdowns("type2", typ2Uniq, "--Choose RNA region2--");
      // merge low concentration entries to others group
      typ1Pie = riv.mergeFamiliesToOthers(typ1Pie, nRecords);
      typ2Pie = riv.mergeFamiliesToOthers(typ2Pie, nRecords);
      regionPie = riv.filterCombinedRegions(regionPie);
      regionPie = riv.mergeFamiliesToOthers(regionPie, nRecords);
      // histograms
      symbolGeneExpTop = riv.getTopKItems(symbolGeneExp, topGeneExpressed);
      // plot charts on the landing page
      riv.plotPieChart(typ1Pie, "type1-piechart", "Left chimeric arm biotypes");
      riv.plotPieChart(
        typ2Pie,
        "type2-piechart",
        "Right chimeric arm biotypes"
      );
      riv.plotPieChart(
        regionPie,
        "type1-type2-piechart",
        "Types of interactions"
      );
      riv.plotHistogram(
        symbolGeneExpTop["values"],
        "rna-expr-sym",
        "Top 50 symbols based on expression",
        "Symbols",
        "Expression (TPM)",
        symbolGeneExpTop["names"]
      );
      riv.registerPlotClick("rna-expr-sym");
    }
    riv.$elLoader.hide();
  };

  /** Show the number of records */
  riv.setDisplayRecordsMessage = () => {
    let textMessage = "",
      modelLen = riv.model.length;
    if (modelLen === 0) {
      textMessage = "No records found";
    } else {
      let ctr = parseInt(riv.counterRecords),
        inCtr = parseInt(riv.nIncrement),
        toRecord = ctr + inCtr;
      if (toRecord > modelLen) {
        toRecord = modelLen;
      }
      textMessage =
        "Showing <b>" +
        (ctr + 1) +
        "-" +
        toRecord +
        " of " +
        modelLen +
        " records";
    }
    return textMessage;
  };

  /** Create a list of interactions panel */
  riv.buildInteractionsPanel = () => {
    let $elParentInteractionIds = $(".rna-transcriptions-container"),
      $elShowModelSizeText = $(".sample-current-size"),
      $elInteractionsList = null,
      interactionsTemplate = "",
      templateInteractionIds = "<div class='transcriptions-ids'></div",
      templateNoRecords = "<div> No results found. </div>",
      model = riv.model;
    riv.resetPairsList();
    $elParentInteractionIds.append(templateInteractionIds);
    $elInteractionsList = $(".transcriptions-ids");
    riv.showDetailsPage();
    if (model && model.length > 1) {
      // get a fraction of the complete model
      let showModel = model.slice(
        riv.counterRecords,
        riv.counterRecords + riv.nIncrement
      );
      // show how many records being shown
      $elShowModelSizeText.html(riv.setDisplayRecordsMessage());
      // create the pairs of symbols in the left panel
      _.each(showModel, item => {
        interactionsTemplate =
          interactionsTemplate + riv.createInteractionsListTemplate(item);
      });
      // set the left panel
      $elInteractionsList.empty().append(interactionsTemplate);
      riv.registerEventsInteractions();
    } else {
      $elInteractionsList.html(templateNoRecords);
    }
    $elInteractionsList.show();
    riv.$elLoader.hide();
  };

  /** Register events for the items in the interactions list */
  riv.registerEventsInteractions = () => {
    let $elImgPlus = $(".plus-symbols");
    $elImgPlus.off("click").on("click", e => {
      riv.fetchSymbolsInteractions(e);
    });
  };

  /** Fetch all interactions for a pair of symbols */
  riv.fetchSymbolsInteractions = e => {
    e.stopPropagation();
    let symbols = e.currentTarget.previousElementSibling.id,
      clsSymbols = "symbols-records",
      isOpen = 0,
      tableName = riv.configObject.tableNames["name"],
      dbQuery = "SELECT tagid, txid1, txid2 FROM " + tableName,
      url = "",
      $elParentElem = $(e.currentTarget.parentElement),
      $elSymbols = null;
    isOpen = $elParentElem.find("." + clsSymbols).length;
    $("." + clsSymbols).remove();
    // construct rows section only if the section does not exist, otherwise clear them
    if (isOpen === 0) {
      $elParentElem.append("<div class='" + clsSymbols + "'></div>");
      $elSymbols = $("." + clsSymbols);
      symbols = symbols.split(":");
      riv.symbol1 = symbols[0];
      riv.symbol2 = symbols[1];
      // construct the query
      dbQuery = riv.makeRegionQ(dbQuery);
      if (dbQuery.indexOf("WHERE") > -1) {
        dbQuery += " AND ";
      } else {
        dbQuery += " WHERE ";
      }
      tableName += ".";
      dbQuery +=
        tableName +
        "symbol1 = '" +
        riv.symbol1 +
        "' AND " +
        tableName +
        "symbol2 = '" +
        riv.symbol2 +
        "'";
      dbQuery = "&query=" + dbQuery;
      url = riv.formUrl(riv.configObject, dbQuery);
      riv.$elLoader.show();
      // async call to fetch from database
      $.get(url, records => {
        let data = records.data,
          template = "",
          $elSymbolRecord = null;
        data = riv.removeHeaders(data);
        _.each(data, item => {
          // show this combination on UI
          let idxCombination = item[0] + ":" + item[1] + ":" + item[2];
          template +=
            "<div class='sym-record' id='" +
            idxCombination +
            "' title='" +
            idxCombination +
            "'>" +
            idxCombination +
            "</div>";
        });
        $elSymbols.html(template);
        $elSymbolRecord = $(".sym-record");
        // set event to fetch information for the selected record
        $elSymbolRecord.off("click").on("click", et => {
          et.stopPropagation();
          // set color when selected
          $elSymbolRecord.removeClass("selected-item");
          $(et.currentTarget).addClass("selected-item");
          riv.fetchSingleSummary(et);
        });
        riv.$elLoader.hide();
      });
    }
  };

  /** Get details of the selected row/interaction */
  riv.fetchSingleSummary = e => {
    let interactionIds = e.currentTarget.id,
      tableName = riv.configObject.tableNames["name"],
      dbQuery = "SELECT " + riv.exportColNames + "  FROM " + tableName,
      url = "";
    interactionIds = interactionIds.split(":");
    // construct query to fetch the selected row
    dbQuery = riv.makeRegionQ(dbQuery);
    if (dbQuery.indexOf("WHERE") > -1) {
      dbQuery += " AND ";
    } else {
      dbQuery += " WHERE ";
    }
    tableName += ".";
    dbQuery +=
      tableName +
      "symbol1 = '" +
      riv.symbol1 +
      "' AND " +
      tableName +
      "symbol2 = '" +
      riv.symbol2 +
      "'";
    dbQuery +=
      " AND " +
      tableName +
      "txid1 = '" +
      interactionIds[1] +
      "' AND " +
      tableName +
      "txid2 = '" +
      interactionIds[2] +
      "'";
    dbQuery += " AND " + tableName + "tagid = '" + interactionIds[0] + "'";
    dbQuery = "&query=" + dbQuery;
    url = riv.formUrl(riv.configObject, dbQuery);
    riv.$elLoader.show();
    riv.resetSummary();
    $.get(url, records => {
      let data = records.data;
      data = riv.removeHeaders(data);
      // build two sections, one for each gene
      riv.buildRNAPairInformation(data[0]);
      riv.$elLoader.hide();
    });
  };

  /** Fetch alignment between two sequences */
  riv.fetchAlignment = sequenceInfo => {
    let sequences = sequenceInfo.sequences;
    (dotBrackets = sequenceInfo.dotbrackets),
      (startIndices = sequenceInfo.startindices),
      (dotbracket1 = []),
      (docbracket2 = []),
      (alignmentPositions = []),
      (dotbracket1Length = 0),
      (dotbracket2Length = 0),
      (startIndex1 = 0),
      (startIndex2 = 0),
      (viz4d = null),
      (alignment = null);

    sequences = sequences.split("&");
    dotBrackets = dotBrackets.split("&");
    startIndices = startIndices.split("&");
    dotbracket1 = dotBrackets[0].split("");
    dotbracket2 = dotBrackets[1].split("");
    dotbracket1Length = dotbracket1.length;
    dotbracket2Length = dotbracket2.length;

    // find corresponding alignment positions using dotbracket notations
    // look for corresponding opening and closing brackets in both sequences
    // having second sequence in the reverse order
    for (let dotbrac1Ctr = 0; dotbrac1Ctr < dotbracket1Length; dotbrac1Ctr++) {
      if (dotbracket1[dotbrac1Ctr] === "(") {
        let alignPos = [];
        alignPos.push(dotbrac1Ctr + 1);
        dotbracket1[dotbrac1Ctr] = ".";
        for (
          let dotbrac2Ctr = dotbracket2Length - 1;
          dotbrac2Ctr >= 0;
          dotbrac2Ctr--
        ) {
          if (dotbracket2[dotbrac2Ctr] === ")") {
            alignPos.push(dotbrac2Ctr + 1);
            alignmentPositions.push(alignPos);
            dotbracket2[dotbrac2Ctr] = ".";
            break;
          }
        }
      }
    }

    // get the alignment
    viz4d = VisualizeAlignment.visualize4d(
      sequences[0],
      sequences[1],
      alignmentPositions
    );
    alignment = VisualizeAlignment.repres(viz4d);
    return alignment;
  };

  /** Export alignment */
  riv.exportAlignment = () => {
    let link = document.createElement("a"),
      downloadData = $(".pre-align").text();
    let encodedData = window.encodeURIComponent(downloadData);
    link.setAttribute("href", "data:application/octet-stream," + encodedData);
    link.setAttribute(
      "download",
      Date.now().toString(16) + "_seq_alignment.txt"
    );
    document.body.appendChild(link);
    linkClick = link.click();
  };

  riv.createSVG = item => {
    /** Draw SVG graphics */
    let xOffset = 10,
      heightDiff = 20,
      textYDiff = 5,
      readInfo = item[17].split(","),
      start1 = parseInt(readInfo[0]),
      end1 = parseInt(readInfo[1]),
      color1 = "fill: green",
      start2 = parseInt(readInfo[2]),
      end2 = parseInt(readInfo[3]),
      color2 = "fill: blue",
      seqLen = parseInt(readInfo[4]),
      template = "";
    template =
      '<line x1="' +
      xOffset +
      '" y1="' +
      heightDiff +
      '" x2="' +
      (start1 + xOffset) +
      '" y2="' +
      heightDiff +
      '" style="stroke:black;stroke-width:2" />' +
      '<rect x="' +
      (start1 + xOffset) +
      '" y="' +
      (heightDiff - 5) +
      '" width="' +
      (end1 - start1) +
      '" height="10" style="' +
      color1 +
      '" />' +
      '<text x="' +
      (start1 + xOffset) +
      '" y="' +
      (heightDiff + 20) +
      '" fill="' +
      color1 +
      '">' +
      start1 +
      "-" +
      end1 +
      "</text>" +
      '<line x1="' +
      (end1 + xOffset) +
      '" y1="' +
      heightDiff +
      '" x2="' +
      (start2 + xOffset) +
      '" y2="' +
      heightDiff +
      '" style="stroke:black;stroke-width:2" />' +
      '<rect x="' +
      (start2 + xOffset) +
      '" y="' +
      (heightDiff - 5) +
      '" width="' +
      (end2 - start2) +
      '" height="10" style="' +
      color2 +
      '" />' +
      '<text x="' +
      (start2 + xOffset) +
      '" y="' +
      (heightDiff - 10) +
      '" fill="' +
      color2 +
      '">' +
      start2 +
      "-" +
      end2 +
      "</text>" +
      '<line x1="' +
      (end2 + xOffset) +
      '" y1="' +
      heightDiff +
      '" x2="' +
      (seqLen + xOffset) +
      '" y2="' +
      heightDiff +
      '" style="stroke:black;stroke-width:2" />' +
      '<text x="' +
      (xOffset + xOffset + seqLen) +
      '" y="' +
      (heightDiff + textYDiff) +
      '" fill="black">' +
      seqLen +
      "</text>";
    return template;
  };

  /** Show information of the selected row/interaction */
  riv.buildRNAPairInformation = item => {
    let $elBothGenes = $(".both-genes"),
      alignment = "",
      sequenceInfo = {},
      noAlignmentTemplate =
        "<span class='no-alignment'>No alignment available</span>",
      hybrid = "";
    riv.showRow();
    $elBothGenes.append(
      "<div class='interaction-header'>Chimera</div><div><svg height='60' width='300' id='one-svg'></svg></div>"
    );
    $elBothGenes.find("#one-svg").html(riv.createSVG(item));
    $elBothGenes.append(
      "<div class='interaction-header'> Interacting partners </div>"
    );
    // first gene
    $elBothGenes.append(
      riv.createSelectedPairInformation(item, "info-gene1", 0)
    );
    // second gene
    $elBothGenes.append(
      riv.createSelectedPairInformation(item, "info-gene2", 1)
    );
    // construct alignment using SVG
    riv.buildAligmentGraphics(item);
    sequenceInfo = {
      sequences: item[29],
      dotbrackets: item[30],
      startindices: "1&1"
    };
    alignment =
      sequenceInfo.dotbrackets.indexOf(")") === -1
        ? noAlignmentTemplate
        : riv.fetchAlignment(sequenceInfo);
    $elBothGenes.append(riv.createAlignmentTemplate(alignment, item));
    // event for downloading alignment as text file
    $(".download-alignment")
      .off("click")
      .on("click", e => {
        riv.exportAlignment();
      });
  };

  /** Create section for a gene */
  riv.createSelectedPairInformation = (item, id, filePos) => {
    let svgTitle = "Gene aligning positions",
      tpm = parseFloat(item[24 + filePos]),
      score = parseFloat(item[26 + filePos]);
    return (
      '<span id="' +
      id +
      '" class="single-interactions-info">' +
      "<p><b>Transcript id</b>: " +
      item[1 + filePos] +
      "</p>" +
      "<p><b>Gene id</b>: " +
      item[3 + filePos] +
      "</p>" +
      "<p><b>Symbol</b>: " +
      item[5 + filePos] +
      "</p>" +
      "<p><b>Region</b>: " +
      item[7 + filePos] +
      "</p>" +
      "<p><b>Aligned position</b>: " +
      item[18 + filePos] +
      "</p>" +
      "<p><b>Merged locus position</b>: " +
      item[20 + filePos] +
      "</p>" +
      "<p><b>Locus expression (TPM)</b>: " +
      tpm +
      "</p>" +
      "<p><b>Score</b>: " +
      score.toFixed(4) +
      "</p>" +
      '<p><b>Alignment position on transcripts:</b></p><svg height="50" width="300" id="align-pos-' +
      (filePos + 1) +
      '" title=""></svg>' +
      "</span>"
    );
  };

  /** Set the model for the left panel and build it */
  riv.buildModel = records => {
    let recordsData = records.data;
    riv.model = riv.removeHeaders(recordsData);
    riv.counterRecords = 0;
    riv.resetCheckAll();
    // build the left panel
    riv.buildInteractionsPanel();
  };

  riv.makeRegionQ = baseQ => {
    let tableName = riv.configObject.tableNames["name"],
      col1Name = tableName + ".region1",
      col2Name = tableName + ".region2",
      query = "";

    if (riv.type1 === "all" && riv.type2 !== "all") {
      query = " WHERE " + col2Name + " = '" + riv.type2 + "'";
    } else if (riv.type1 !== "all" && riv.type2 === "all") {
      query = " WHERE " + col1Name + " = '" + riv.type1 + "'";
    } else if (riv.type1 !== "all" && riv.type2 !== "all") {
      query =
        " WHERE " +
        col1Name +
        " = '" +
        riv.type1 +
        "' AND " +
        col2Name +
        " = '" +
        riv.type2 +
        "'";
    }
    return baseQ + query;
  };

  /** Register click event for Plotly plots */
  riv.registerPlotClick = elemId => {
    let myPlot = document.getElementById(elemId);
    // register click event for bar plots on landing page
    myPlot.on("plotly_click", data => {
      let tableName = riv.configObject.tableNames["name"],
        dbQuery = riv.getSymbolsBaseQuery(tableName),
        plotSelectedOpt = data.points[0].x,
        selectedOpt = "all";
      riv.type1 = selectedOpt;
      riv.type2 = selectedOpt;
      $("#type1").val(selectedOpt);
      $("#type2").val(selectedOpt);
      $(".search-gene").val(plotSelectedOpt);
      dbQuery +=
        " WHERE symbol1 = " +
        "'" +
        plotSelectedOpt +
        "' OR symbol2 = " +
        "'" +
        plotSelectedOpt +
        "'";
      riv.resetSummary();
      riv.resetFilters();
      riv.resetCheckAll();
      riv.getInteractions(dbQuery);
    });
  };

  /** Create query for showing interactions */
  riv.makeInteractionsQ = e => {
    let tableName = riv.configObject.tableNames["name"],
      dbQuery = riv.getSymbolsBaseQuery(tableName),
      url = "";
    // collect the selected types
    riv.type1 = document.getElementById("type1").value;
    riv.type2 = document.getElementById("type2").value;
    // form query
    dbQuery = riv.makeRegionQ(dbQuery);
    riv.resetSummary();
    riv.resetFilters();
    riv.resetCheckAll();
    riv.getInteractions(dbQuery);
  };

  /** Fetch data for the selected types */
  riv.getInteractions = updatedQ => {
    let $elFilters = $(".filter-row");
    riv.$elLoader.show();
    updatedQ = "&query=" + updatedQ;
    url = riv.formUrl(riv.configObject, updatedQ);
    $.get(url, data => {
      riv.buildModel(data);
      riv.$elLoader.hide();
      $elFilters.show();
    });
  };

  riv.getSymbolsBaseQuery = tableName => {
    return (
      "SELECT DISTINCT (symbol1 || ':' || symbol2) as symbols FROM " + tableName
    );
  };

  /** Filter combining all the elements - search, sort and filter */
  riv.cascadeSearch = () => {
    let url = riv.makeSearchURL();
    riv.resetSummary();
    riv.ajaxCall(url, riv.buildModel);
  };

  /** Select all the interactions in the left panel */
  riv.checkAllInteractions = e => {
    let $elInteractionsChecked = $(".rna-interaction"),
      checkallStatus = e.target.checked;
    // set true if checked
    _.each($elInteractionsChecked, item => {
      item.checked = checkallStatus ? true : false;
    });
  };

  /** Prepare url for searching taking multiple columns from the database table */
  riv.makeSearchURL = () => {
    let searchQuery = $(".search-gene").val(),
      filterOperator = $(".filter-operator")
        .find(":selected")
        .val(),
      filterType = $(".rna-filter")
        .find(":selected")
        .val(),
      filterQuery = $(".filter-value").val(),
      sortByVal = $(".rna-sort")
        .find(":selected")
        .val(),
      colNames = {},
      dbQuery = "",
      url = "",
      searchClause = "",
      filterClause = "",
      sortClause = "",
      tableName = riv.configObject.tableNames["name"],
      isSearchQuery = false;
    // create a composite query considering all the filters together
    dbQuery = riv.getSymbolsBaseQuery(tableName);
    // form query for filter types
    tableName += ".";
    if (filterType === "score") {
      filterClause =
        tableName + "score" + " " + filterOperator + " " + filterQuery;
    } else if (filterType === "hybrid") {
      filterClause =
        tableName +
        "hybrid" +
        " " +
        filterOperator +
        " " +
        "'" +
        filterQuery +
        "'";
    } else if (filterType === "mfe") {
      filterClause =
        tableName + "mfe" + " " + filterOperator + " " + filterQuery;
    } else {
      filterClause = tableName + "score BETWEEN 0.0 AND 10.0";
    }
    // form sort clause
    if (sortByVal !== "-1") {
      sortByVal = sortByVal.split("_");
      sortClause =
        " ORDER BY " +
        tableName +
        sortByVal[0] +
        " " +
        sortByVal[1].toUpperCase();
    } else {
      sortClause = " ORDER BY " + tableName + "score DESC";
    }
    // form search clause
    if (searchQuery.length >= riv.minQueryLength) {
      let queryLike = "%" + searchQuery + "%",
        colNames = {
          txid1: queryLike,
          txid2: queryLike,
          geneid1: queryLike,
          geneid2: queryLike,
          symbol1: queryLike,
          symbol2: queryLike,
          region1: queryLike,
          region2: queryLike
        },
        colsNum = Object.keys(colNames).length;
      // iterate a dictionary
      Object.keys(colNames).forEach((key, index) => {
        searchClause += tableName + key + " LIKE " + "'" + colNames[key] + "'";
        if (index < colsNum - 1) {
          searchClause += " OR ";
        }
      });
      isSearchQuery = true;
    }
    dbQuery = riv.makeRegionQ(dbQuery);
    if (dbQuery.indexOf("WHERE") > -1) {
      dbQuery += " AND ";
    } else {
      dbQuery += " WHERE ";
    }
    if (isSearchQuery === true) {
      dbQuery += "(" + filterClause + ") AND (" + searchClause + ")";
    } else {
      dbQuery += filterClause;
    }
    dbQuery += sortClause;
    dbQuery = "&query=" + dbQuery;
    url = riv.formUrl(riv.configObject, dbQuery);
    return url;
  };

  /** Prepare summary of interactions either from the selected ones or taken from the file */
  riv.getInteractionsSummary = e => {
    let checkedIds = [],
      checkboxes = $(".rna-interaction");
    e.preventDefault();
    _.each(checkboxes, item => {
      if (item.checked) {
        if (!checkedIds.includes(item.id)) {
          checkedIds.push(item.id);
        }
      }
    });
    // fetch summary for the selected items
    if (checkedIds.length > 0) {
      riv.fetchSummary(checkedIds);
    }
  };

  /** Fetch data for the selected combinations of symbols */
  riv.fetchSummary = checkedSymbols => {
    let tableName = riv.configObject.tableNames["name"],
      dbQuery = "SELECT " + riv.exportColNames + " FROM " + tableName,
      url = riv.makeSummaryExportURL(dbQuery, checkedSymbols, tableName);
    riv.$elLoader.show();
    riv.resetSummary();
    riv.showSummary();
    // fetch records using async call
    $.get(url, records => {
      let data = records.data;
      data = riv.removeHeaders(data);
      riv.createSummary(data);
      riv.$elLoader.hide();
    });
  };

  /** Fetch data for exporting */
  riv.fetchAndExport = () => {
    let checkedIds = [],
      url = "",
      tableName = riv.configObject.tableNames["name"],
      dbQuery = "SELECT * FROM " + tableName,
      checkboxes = $(".rna-interaction");
    // get all checked items
    _.each(checkboxes, item => {
      if (item.checked) {
        if (!checkedIds.includes(item.id)) {
          checkedIds.push(item.id);
        }
      }
    });
    // make summary for checked items
    if (checkedIds.length > 0) {
      url = riv.makeSummaryExportURL(dbQuery, checkedIds, tableName);
      riv.$elLoader.show();
      $.get(url, records => {
        riv.createExportData(records.data);
      });
    }
  };

  /** Formulate the where clause of query and create URL */
  riv.makeSummaryExportURL = (dbQ, checkedIds, tableName) => {
    // formulate the where clause
    let whereIdx = -1;
    dbQ = riv.makeRegionQ(dbQ);
    whereIdx = dbQ.indexOf("WHERE");
    if (whereIdx > -1) {
      dbQ += " AND (";
    } else {
      dbQ += " WHERE ";
    }
    tableName += ".";
    _.each(checkedIds, (symbols, index) => {
      symbols = symbols.split(":");
      if (index == checkedIds.length - 1) {
        dbQ +=
          "( " +
          tableName +
          "symbol1 = '" +
          symbols[0] +
          "' AND " +
          tableName +
          "symbol2 = '" +
          symbols[1] +
          "')";
      } else {
        dbQ +=
          "( " +
          tableName +
          "symbol1 = '" +
          symbols[0] +
          "' AND " +
          tableName +
          "symbol2 = '" +
          symbols[1] +
          "') OR ";
      }
    });
    if (whereIdx > -1) {
      dbQ += ")";
    }
    dbQ = "&query=" + dbQ;
    let url = riv.formUrl(riv.configObject, dbQ);
    return url;
  };

  /** Callback event for exporting data using export button */
  riv.createExportData = records => {
    let tsv_data = "",
      link = document.createElement("a"),
      file_name = Date.now().toString(16) + "_results.tsv";
    // create tab-separated items
    _.each(records, item => {
      tsv_data += item.join("\t") + "\n";
    });
    // make arrangements for downloading the file
    tsv_data = window.encodeURIComponent(tsv_data);
    link.setAttribute("href", "data:application/octet-stream," + tsv_data);
    link.setAttribute("download", file_name);
    document.body.appendChild(link);
    linkClick = link.click();
    riv.$elLoader.hide();
  };

  /** Create summary datasets for generating plots */
  riv.createSummary = summaryItems => {
    let summaryResultRegion1 = {},
      summaryResultRegion2 = {},
      summaryRegionTypes = {},
      summaryResultScore = [],
      summaryResultScore1 = [],
      summaryResultScore2 = [],
      summaryResultAlignment1 = [],
      summaryResultAlignment2 = [],
      summaryResultGeneExpr1 = {},
      summaryResultGeneExpr2 = {},
      summaryResultSymbol1 = {},
      summaryResultSymbol2 = {},
      nRec = summaryItems.length;
    // summary fields - geneid (1 and 2), type (1 and 2), region (1 and 2), symbol (1 and 2), score (1 and 2)
    _.each(summaryItems, item => {
      let sym1 = item[5],
        sym2 = item[6],
        reg1 = item[7],
        reg2 = item[8],
        tpm1 = parseFloat(item[24]),
        tpm2 = parseFloat(item[25]),
        combinedRegions = "";
      summaryResultRegion1[reg1] = (summaryResultRegion1[reg1] || 0) + 1;
      summaryResultRegion2[reg2] = (summaryResultRegion2[reg2] || 0) + 1;
      summaryResultScore1.push(item[26]);
      summaryResultScore2.push(item[27]);
      summaryResultScore.push(item[28]);

      // collect symbols with maximum gene expression - symbol1
      if (sym1 in summaryResultGeneExpr1 === true) {
        let currentTpm = summaryResultGeneExpr1[sym1];
        if (currentTpm < tpm1) {
          summaryResultGeneExpr1[sym1] = tpm1;
        }
      } else {
        summaryResultGeneExpr1[sym1] = tpm1;
      }
      // collect symbols with maximum gene expression - symbol2
      if (sym2 in summaryResultGeneExpr2 === true) {
        let currentTpm = summaryResultGeneExpr2[sym2];
        if (currentTpm < tpm2) {
          summaryResultGeneExpr2[sym2] = tpm2;
        }
      } else {
        summaryResultGeneExpr2[sym2] = tpm2;
      }
      // create collection for pie chart showing combined regions in legend
      combinedRegions = reg1 + ":" + reg2;
      summaryRegionTypes[combinedRegions] =
        (summaryRegionTypes[combinedRegions] || 0) + 1;

      summaryResultSymbol1[item[5]] = (summaryResultSymbol1[item[5]] || 0) + 1;
      summaryResultSymbol2[item[6]] = (summaryResultSymbol2[item[6]] || 0) + 1;
      // get only unique alignment positions
      presentGene1 = _.findWhere(summaryResultAlignment1, {
        geneid: item[3],
        startPos: parseInt(item[9]),
        endPos: parseInt(item[10])
      });
      if (!presentGene1) {
        summaryResultAlignment1.push({
          startPos: parseInt(item[9]),
          endPos: parseInt(item[10]),
          seqLength: parseInt(item[12]),
          geneid: item[3],
          symbol: item[5],
          scale: 100
        });
      }
      let presentGene2 = _.findWhere(summaryResultAlignment2, {
        geneid: item[4],
        startPos: parseInt(item[13]),
        endPos: parseInt(item[14])
      });
      if (!presentGene2) {
        summaryResultAlignment2.push({
          startPos: parseInt(item[13]),
          endPos: parseInt(item[14]),
          seqLength: parseInt(item[16]),
          geneid: item[4],
          symbol: item[6],
          scale: 100
        });
      }
    });
    // get only top 50 regions based on gene expression
    summaryResultGeneExpr1 = riv.getTopKItems(summaryResultGeneExpr1, 50);
    summaryResultGeneExpr2 = riv.getTopKItems(summaryResultGeneExpr2, 50);

    summaryRegionTypes = riv.filterCombinedRegions(summaryRegionTypes);
    summaryRegionTypes = riv.mergeFamiliesToOthers(summaryRegionTypes, nRec);

    let plottingData = {
      region1: summaryResultRegion1,
      region2: summaryResultRegion2,
      score: summaryResultScore,
      score1: summaryResultScore1,
      score2: summaryResultScore2,
      rnaexpr1: summaryResultGeneExpr1,
      rnaexpr2: summaryResultGeneExpr2,
      symbol1: summaryResultSymbol1,
      symbol2: summaryResultSymbol2,
      summaryRegionTypes: summaryRegionTypes
    };
    // merge low concentration items to others group
    plottingData.region1 = riv.mergeFamiliesToOthers(
      plottingData.region1,
      summaryResultRegion1.length
    );
    plottingData.region2 = riv.mergeFamiliesToOthers(
      plottingData.region2,
      summaryResultRegion2.length
    );
    plottingData.summaryResultSymbol1 = riv.mergeFamiliesToOthers(
      plottingData.summaryResultSymbol1,
      summaryResultSymbol1.length
    );
    plottingData.summaryResultSymbol2 = riv.mergeFamiliesToOthers(
      plottingData.summaryResultSymbol2,
      summaryResultSymbol2.length
    );
    // plot
    riv.plotInteractions(plottingData);
    // alignment summary
    riv.makeAlignmentSummary(summaryResultAlignment1, summaryResultAlignment2);
  };

  /** Send data for summary plotting */
  riv.plotInteractions = data => {
    let fileName = riv.configObject.tableNames["name"],
      expr1Len = data.rnaexpr1.values.length,
      expr2Len = data.rnaexpr2.values.length;
    // plot the summary as pie charts and histograms
    riv.plotPieChart(data.symbol1, "rna-symbol1", "Left arm RNA distribution");
    riv.plotPieChart(data.symbol2, "rna-symbol2", "Right arm RNA distribution");
    riv.plotPieChart(data.region1, "rna-region1", "Left arm RNA biotypes");
    riv.plotPieChart(data.region2, "rna-region2", "Right arm RNA biotypes");
    riv.plotPieChart(
      data.summaryRegionTypes,
      "selected-types",
      "Types of interactions"
    );
    riv.plotHistogram(
      data.score,
      "rna-score",
      "Overall score for the chimeras",
      "Score",
      "# Interactions"
    );
    riv.plotHistogram(
      data.score1,
      "rna-score1",
      "Score for left interacting partners",
      "Score",
      "# Interactions"
    );
    riv.plotHistogram(
      data.score2,
      "rna-score2",
      "Score for right interacting partners",
      "Score",
      "# Interactions"
    );
    riv.plotHistogram(
      data.rnaexpr1.values,
      "rna-expr1",
      "Top " + expr1Len + " symbols based on expression",
      "Symbols",
      "Expression (TPM)",
      data.rnaexpr1.names
    );
    riv.plotHistogram(
      data.rnaexpr2.values,
      "rna-expr2",
      "Top " + expr2Len + " symbols based on expression",
      "Symbols",
      "Expression (TPM)",
      data.rnaexpr2.names
    );
  };

  /** Plot pie chart for interactions chosen for summary */
  riv.plotPieChart = (dict, container, name) => {
    let layout = {
        title: name,
        autosize: true,
        automargin: true
      },
      labels = [],
      values = [],
      data = null;
    // separate keys and their values
    _.mapObject(dict, (value, key) => {
      labels.push(key);
      values.push(value);
    });
    data = [
      {
        values: values,
        labels: labels,
        type: "pie",
        showlegend: true
      }
    ];
    Plotly.newPlot(container, data, layout);
  };

  /** Plot histogram for interactions chosen for summary */
  riv.plotHistogram = (data, container, name, xTitle, yTitle, labels) => {
    let trace = {},
      layout = {};
    if (labels === undefined) {
      trace = {
        x: data,
        type: "histogram"
      };
    } else {
      trace = {
        y: data,
        x: labels,
        type: "bar"
      };
    }
    layout = {
      autosize: true,
      margin: {
        autoexpand: true
      },
      title: name,
      xaxis: {
        title: xTitle
      },
      yaxis: {
        title: yTitle
      }
    };
    Plotly.newPlot(container, [trace], layout);
  };

  /**Merge the families whose counts are very small to others category */
  riv.mergeFamiliesToOthers = (symbolsCount, interactionsCount) => {
    let otherCategoryCount = 0,
      familiesCount = {},
      minShare = 0.01;
    for (let item in symbolsCount) {
      let count = symbolsCount[item];
      share = count / interactionsCount;
      // merge if share of one key is less
      if (share < minShare) {
        otherCategoryCount += count;
      } else {
        familiesCount[item] = count;
      }
    }
    if (otherCategoryCount > 0) {
      familiesCount["others"] = otherCategoryCount;
    }
    return familiesCount;
  };

  /** Make alignment graphics summary for all checked combination of symbols */
  riv.makeAlignmentSummary = (alignment1, alignment2) => {
    let $elAlignmentGraphics1 = $("#rna-alignment-graphics1"),
      $elAlignmentGraphics2 = $("#rna-alignment-graphics2");
    $elAlignmentGraphics1.empty();
    $elAlignmentGraphics1.append(
      "<p>Alignment positions on " + alignment1.length + " transcripts<p>"
    );
    $elAlignmentGraphics1.append(
      riv.buildSVGgraphics(alignment1, "gene1", "green")
    );
    $elAlignmentGraphics2.empty();
    $elAlignmentGraphics2.append(
      "<p>Alignment positions on " + alignment2.length + " transcripts<p>"
    );
    $elAlignmentGraphics2.append(
      riv.buildSVGgraphics(alignment2, "gene2", "blue")
    );
  };

  /** Draw graphics for alignment */
  riv.buildAligmentGraphics = item => {
    let dataGene = {};
    // first gene
    dataGene = {
      startPos: parseInt(item[9]),
      endPos: parseInt(item[10]),
      seqLength: parseInt(item[12]),
      color: "green",
      scale: 100
    };
    $("#align-pos-1").html(riv.drawSingleSvg(dataGene));
    // second gene
    dataGene = {
      startPos: parseInt(item[13]),
      endPos: parseInt(item[14]),
      seqLength: parseInt(item[16]),
      color: "blue",
      scale: 100
    };
    $("#align-pos-2").html(riv.drawSingleSvg(dataGene));
  };

  /** Build SVG graphics  */
  riv.buildSVGgraphics = (alignmentCollection, geneType, boxColor) => {
    let tableTemplate = "",
      heightDiff = 12,
      alignmentHeight = 30,
      svgHeight = alignmentCollection.length * alignmentHeight + heightDiff,
      xOffset = 10,
      yOffset = 2,
      seqLengthXPos = 160,
      symbolXPos = 200,
      symbolSearchUrl = "#";

    tableTemplate = '<div><svg height="' + svgHeight + '" width="500">';
    _.each(alignmentCollection, (item, index) => {
      let scale = item.seqLength < item.scale ? item.seqLength : item.scale;
      (ratio = scale / item.seqLength),
        (scaledBegin = parseInt(ratio * item.startPos) + xOffset),
        (scaledEnd = parseInt(ratio * item.endPos) + xOffset),
        (barLength = item.endPos - item.startPos),
        (seqEndPos =
          scaledBegin + barLength + ratio * (item.seqLength - item.endPos)),
        (color = "fill:" + boxColor);
      geneId = item.geneid;
      if (geneId.startsWith("ENS") === true) {
        symbolSearchUrl = "http://www.ensembl.org/id/" + geneId;
      }
      tableTemplate +=
        '<line x1="' +
        xOffset +
        '" y1="' +
        heightDiff +
        '" x2="' +
        scaledBegin +
        '" y2="' +
        heightDiff +
        '" style="stroke:black;stroke-width:2" />' +
        '<rect x="' +
        scaledBegin +
        '" y="' +
        (heightDiff - 5) +
        '" width="' +
        barLength +
        '" height="10" style="' +
        color +
        '" />' +
        '<text x="' +
        scaledBegin +
        '" y="' +
        (heightDiff + 20) +
        '" fill="black">' +
        item.startPos +
        "-" +
        item.endPos +
        "</text>" +
        '<line x1="' +
        (scaledBegin + barLength) +
        '" y1="' +
        heightDiff +
        '" x2="' +
        seqEndPos +
        '" y2="' +
        heightDiff +
        '" style="stroke:black;stroke-width:2" />' +
        '<text x="' +
        seqLengthXPos +
        '" y="' +
        (heightDiff + yOffset) +
        '" fill="black">' +
        item.seqLength +
        "</text>" +
        '<a xlink:href="' +
        symbolSearchUrl +
        '" target="_blank" class="symbol-link" title="Search for this gene">' +
        '<text x="' +
        symbolXPos +
        '" y="' +
        (heightDiff + yOffset) +
        '" fill="black">' +
        item.symbol +
        "</text>" +
        "</a>";
      heightDiff += alignmentHeight;
    });
    tableTemplate += "</svg></div>";
    return tableTemplate;
  };

  /** Draw SVG graphics */
  riv.drawSingleSvg = data => {
    let scale = data.seqLength < data.scale ? data.seqLength : data.scale,
      ratio = scale / data.seqLength,
      xOffset = 10,
      scaledBegin = parseInt(ratio * data.startPos) + xOffset,
      scaledEnd = parseInt(ratio * data.endPos) + xOffset,
      heightDiff = 20,
      textYDiff = 5,
      barLength = data.endPos - data.startPos,
      seqEndPos =
        scaledBegin + barLength + ratio * (data.seqLength - data.endPos),
      color = "fill:" + data.color;
    template = "";
    template =
      '<line x1="' +
      xOffset +
      '" y1="' +
      heightDiff +
      '" x2="' +
      scaledBegin +
      '" y2="' +
      heightDiff +
      '" style="stroke:black;stroke-width:2" />' +
      '<rect x="' +
      scaledBegin +
      '" y="' +
      (heightDiff - 5) +
      '" width="' +
      barLength +
      '" height="10" style="' +
      color +
      '" />' +
      '<text x="' +
      scaledBegin +
      '" y="' +
      (heightDiff + 20) +
      '" fill="black">' +
      data.startPos +
      "-" +
      data.endPos +
      "</text>" +
      '<line x1="' +
      (scaledBegin + barLength) +
      '" y1="' +
      heightDiff +
      '" x2="' +
      seqEndPos +
      '" y2="' +
      heightDiff +
      '" style="stroke:black;stroke-width:2" />' +
      '<text x="' +
      (xOffset + seqEndPos) +
      '" y="' +
      (heightDiff + textYDiff) +
      '" fill="black">' +
      data.seqLength +
      "</text>";
    return template;
  };

  riv.showSummary = () => {
    $(".both-genes").hide();
    $(".first-gene").show();
    $(".common-genes").show();
    $(".second-gene").show();
  };

  riv.showRow = () => {
    $(".both-genes").show();
    $(".first-gene").hide();
    $(".second-gene").hide();
    $(".common-genes").hide();
  };

  /** Clear the UI elements */
  riv.resetSummary = () => {
    $("#rna-score").empty();
    $("#selected-types").empty();
    $("#rna-type2").empty();
    $("#rna-score1").empty();
    $("#rna-score2").empty();
    $("#rna-energy").empty();
    $("#rna-alignment-graphics1").empty();
    $("#rna-alignment-graphics2").empty();
    $("#rna-expr1").empty();
    $("#rna-expr2").empty();
    $("#rna-region1").empty();
    $("#rna-region2").empty();
    $("#rna-symbol1").empty();
    $("#rna-symbol2").empty();
    $(".both-genes").empty();
  };

  riv.resetFilters = () => {
    $(".search-gene")[0].value = "";
    $(".rna-sort").val("-1");
    $(".rna-filter").val("-1");
    $(".filter-operator").val("-1");
    $(".filter-value")[0].value = "";
  };

  riv.resetCheckAll = () => {
    $(".check-all-interactions")[0].checked = false;
  };

  riv.resetTypes = () => {
    $("#type1").val("-1");
    $("#type2").val("-1");
    $(".rna-pair").empty();
  };

  riv.showLandingPage = () => {
    $(".rna-results").hide();
    $(".footer-row").hide();
    $(".landing-page").show();
    $(".sample-current-size").hide();
    $(".filter-row").hide();
    $("#type1").val("-1");
    $("#type2").val("-1");
  };

  riv.showDetailsPage = () => {
    $(".rna-results").show();
    $(".footer-row").show();
    $(".sample-current-size").show();
    $(".landing-page").hide();
  };

  riv.resetPairsList = () => {
    $(".sample-current-size").empty();
    $(".transcriptions-ids").remove();
  };

  riv.removeHeaders = data => {
    return data.slice(1);
  };

  riv.createAlignmentTemplate = (alignment, item) => {
    let mfe = item[32] === "NA" ? "Not applicable" : item[32] + " kcal/mol";
    return (
      "<div class='interaction-header'>Alignment Information" +
      "<a data-id='" +
      item[0] +
      "' href='#' class='download-alignment' title='Download the alignment as text file'>" +
      "Download alignment" +
      "</a>" +
      "</div>" +
      "<div class='seq-alignment' title='Sequence alignment'>" +
      "<pre class='pre-align'>" +
      alignment +
      "</pre>" +
      "<span class='mfe-info'> Minimum free energy (MFE): " +
      mfe +
      "</span>" +
      "</div>"
    );
  };

  riv.createInteractionsListTemplate = record => {
    return (
      '<div class="rna-pair">' +
      '<input type="checkbox" id="' +
      record +
      '" value="" class="rna-interaction chkbx-interaction" />' +
      '<img class="plus-symbols plus-icon" title="See interactions" src="/static/plugins/visualizations/chiraviz/static/images/plus-icon.png" />' +
      '<span class="rna-pair-interaction" title="Gene symbols">' +
      record +
      "</span>" +
      "</div>"
    );
  };

  riv.createInteractionTemplate = () => {
    return (
      '<div class="container one-sample">' +
      '<div class="row top-row">' +
      '<div class="col-sm-2 elem-rna">' +
      '<div class="sample-name" title="' +
      riv.configObject.dataName +
      '">' +
      riv.configObject.dataName.substring(0, 30) +
      "..." +
      "</div>" +
      '<div class="sample-current-size"></div>' +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<select id="type1" class="form-control elem-rna" title="Region1">' +
      "</select>" +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<select id="type2" class="form-control elem-rna" title="Region2">' +
      "</select>" +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<input type="button" id="btnGetInteractions" class="btn btn-success elem-rna form-control" value="Get interactions" />' +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<button type="button" class="back-home btn btn-success btn-rna btn-interaction elem-rna" title="Back to home page">Home</button>' +
      "</div>" +
      "</div>" +
      '<div class="row filter-row">' +
      '<div class="col-sm-1 elem-rna">' +
      '<input type="button" id="btnPrev" class="btn btn-success elem-rna form-control" value="<" title="Previous" />' +
      "</div>" +
      '<div class="col-sm-1 elem-rna">' +
      '<input type="button" id="btnNext" class="btn btn-success elem-rna form-control" value=">" title="Next" />' +
      "</div>" +
      '<div class="col-sm-2 elem-rna search-input">' +
      '<input type="text" class="search-gene form-control elem-rna" value="" placeholder="Search..." title="Search">' +
      '<img class="search-gene-image" src="/static/plugins/visualizations/chiraviz/static/images/search-icon.png" />' +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<select name="sort" class="rna-sort form-control elem-rna" title="Sort">' +
      '<option value="-1">--sort--</option>' +
      '<option value="score_asc">Score asc</option>' +
      '<option value="score_desc">Score desc</option>' +
      "</select>" +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<select name="filter" class="rna-filter form-control elem-rna" title="Filter">' +
      '<option value="-1">--filter--</option>' +
      '<option value="score">Score</option>' +
      '<option value="hybrid">Hybrid</option>' +
      '<option value="mfe">Free energy</option>' +
      "</select>" +
      "</div>" +
      '<div class="col-sm-2 elem-rna">' +
      '<select name="filter-operator" class="filter-operator form-control elem-rna" title="Filter operator">' +
      '<option value="-1">--operator--</option>' +
      '<option value="=">=</option>' +
      '<option value=">">></option>' +
      '<option value="<"><</option>' +
      '<option value="<="><=</option>' +
      '<option value=">=">>=</option>' +
      '<option value="<>"><></option>' +
      "</select>" +
      "</div>" +
      '<div class="col-sm-2 elem-rna search-input">' +
      '<input type="text" class="filter-value form-control elem-rna" title="Enter the selected filter value"' +
      'value="" placeholder="Enter value..." />' +
      '<img class="filter-value-image" src="/static/plugins/visualizations/chiraviz/static/images/search-icon.png" />' +
      "</div>" +
      "</div>" +
      '<div class="row landing-page">' +
      '<div class="col-sm-6">' +
      '<div id="type1-piechart"></div>' +
      "</div>" +
      '<div class="col-sm-6">' +
      '<div id="type2-piechart"></div>' +
      "</div>" +
      '<div class="col-sm-12">' +
      '<div id="type1-type2-piechart"></div>' +
      "</div>" +
      '<div class="col-sm-12">' +
      '<div id="rna-expr-sym"></div>' +
      "</div>" +
      "</div>" +
      '<div class="row rna-results">' +
      '<div class="col-sm-2 rna-transcriptions-container">' +
      '<div class="transcriptions-ids"></div>' +
      "</div>" +
      '<div class="col-sm-10 both-genes"></div>' +
      '<div class="col-sm-10 common-genes">' +
      '<div id="selected-types"></div>' +
      '<div id="rna-score"></div>' +
      "</div>" +
      '<div class="col-sm-5 first-gene">' +
      '<div id="rna-region1"></div>' +
      '<div id="rna-symbol1"></div>' +
      '<div id="rna-score1"></div>' +
      '<div id="rna-expr1"></div>' +
      '<div id="rna-alignment-graphics1"></div>' +
      "</div>" +
      '<div class="col-sm-5 second-gene">' +
      '<div id="rna-region2"></div>' +
      '<div id="rna-symbol2"></div>' +
      '<div id="rna-score2"></div>' +
      '<div id="rna-expr2"></div>' +
      '<div id="rna-alignment-graphics2"></div>' +
      "</div>" +
      "</div>" +
      '<div class="row footer-row">' +
      '<div class="col-sm-10">' +
      '<input id="check-all" type="checkbox" class="check-all-interactions"' +
      'value="false" title="Check all displayed interactions" />' +
      "<span>Check all</span>" +
      '<button type="button" class="rna-summary btn btn-success btn-rna btn-interaction" title="Get summary of RNA-RNA interactions">' +
      "Summary" +
      "</button>" +
      '<button type="button" class="export-results btn btn-success btn-rna btn-interaction"' +
      'title="Export results as tab-separated file">' +
      "Export" +
      "</button>" +
      "</div>" +
      '<div class="col-sm-2"></div>' +
      "</div>" +
      "</div>"
    );
  };
  return riv;
})(RNAInteractionViewer || {});
