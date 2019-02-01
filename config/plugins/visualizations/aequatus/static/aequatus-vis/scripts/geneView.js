/**
 * Created with IntelliJ IDEA.
 * User: thankia
 * Date: 14/08/2013
 * Time: 11:17
 * To change this template use File | Settings | File Templates.
 */

var data = "";

var colours = ['rgb(166,206,227)', 'rgb(31,120,180)', 'rgb(178,223,138)', 'rgb(51,160,44)', 'rgb(251,154,153)', 'rgb(227,26,28)', 'rgb(253,191,111)', 'rgb(255,127,0)', 'rgb(202,178,214)', 'rgb(106,61,154)', 'rgb(255,255,153)', 'rgb(177,89,40)', 'rgb(141,211,199)', 'rgb(255,255,179)', 'rgb(190,186,218)', 'rgb(251,128,114)', 'rgb(128,177,211)', 'rgb(253,180,98)', 'rgb(179,222,105)', 'rgb(252,205,229)', 'rgb(217,217,217)', 'rgb(188,128,189)', 'rgb(204,235,197)', 'rgb(255,237,111)']

var gene_list_array = [];
var ref_member = null
var syntenic_data = null;
var genome_db_id = null;
var chr = null;
var member_id = null;
var members = null;
var protein_member_id = null;
var transcript_member_id = null;
var ref_data = null;
var filter_div = null;
var slider_filter_div = null;


/**
 * cleans gene tree for . and -
 * @param tree
 * @returns {*}
 */


function cleanTree(tree) {
    /*
     *
     * .toSource() will not work in Safari so using Stringify
     *
     * var treestring = tree.toSource()
     * treestring = treestring.substring(1, treestring.length - 1)
     * treestring = treestring.replace(/(['"])?([a-zA-Z0-9_]+)(['"])?:([^\/])/g, '"$2":$4');
     *
     */

    var treestring = JSON.stringify(tree)
    /*
     * removes unwated quotes
     */
    treestring = treestring.replace(/\"\[/g, '\[');
    treestring = treestring.replace(/\\\"/g, '\"');
    treestring = treestring.replace(/\]\"/g, '\]');

    var re = /"accession":\s*"([a-z0-9_]*)([\.-])([\.a-z0-9_-]*)"/gi;

    var matches = [];
    var match = re.exec(treestring);
    while (match) {
        matches.push(match[1]);
        var matchString = match[1] + match[2] + match[3];
        var replaceString = matchString.replace(/[\.-]/g, "_");
        treestring = treestring.replace(matchString, replaceString)
        match = re.exec(treestring);
    }

    tree = JSON.parse(treestring)

    return tree;
}

/**
 * cleans genes and transcript ID for . and -
 * @param member
 * @returns {*}
 */
function cleanGenes(member) {
    member = JSON.stringify(member)
    member = member.replace(/[.|-]/g, '_')
    member = member.replace(/:_1/g, ":-1")
    member = JSON.parse(member)
    jQuery.each(member, function (key, data) {
        var transcript = member[key].Transcript.replace(/:\s*_1/g, ":-1")
        transcript = transcript.replace(/\./g, "")
        key = key.replace(/[.|-]/g, '_')
        member[key].Transcript = JSON.parse(transcript)
    })

    return member;

}

/**
 * cleans cigarIDs for . and -
 * @param cigar
 * @returns {*}
 */
function cleanCIGARs(cigar) {
    jQuery.each(cigar, function (key, data) {
        var key = key.replace(/[^a-zA-Z0-9]/g, '_')
        cigar[key] = data
    })

    cigar = checkCigar()


    return cigar;
}

/**
 * initialise aequatus-vis with setting up controls, filters parsing tree and cigar
 * @param json aequatus JSON
 * @param control_div controls place holder name
 * @param filter_spacer filters place holder name
 */
function init(json, control_div, filter_spacer, slider_filter) {
    member_id = json.ref.replace(/[^a-zA-Z0-9]/g, '_');

    ranked = false;
    syntenic_data = json
    if (control_div) {
        setControls(control_div)
    }

    if (filter_spacer) {
        jQuery(filter_spacer).html("")
        filter_div = filter_spacer
    }

    if (slider_filter) {
        slider_filter_div = slider_filter
    }

    if (jQuery.type(syntenic_data.tree) == 'object') {
    }
    else {
        syntenic_data.tree = NewickToJSON(syntenic_data.tree)
    }
    syntenic_data.tree = cleanTree(syntenic_data.tree)
    syntenic_data.member = cleanGenes(syntenic_data.member)

    if (!syntenic_data.cigar) {
        syntenic_data.cigar = {};
        syntenic_data.sequence = {};

        recursive_tree(syntenic_data.tree)
    }
    syntenic_data.cigar = cleanCIGARs(syntenic_data.cigar)

    ref_data = syntenic_data.member[member_id]
    protein_member_id = json.protein_id.replace(/[^a-zA-Z0-9]/g, '_')
    transcript_member_id = json.transcript_id

    set_members_length();

}

/**
 * recursively calls same function to retrieve cigar information from subnodes
 * @param tree node_tree
 */
function recursive_tree(tree) {

    var child_lenth = tree.children.length;

    while (child_lenth--) {
        if (tree.children[child_lenth].sequence) {
            addCigar(tree.children[child_lenth])
        } else {
            recursive_tree(tree.children[child_lenth])
        }
    }

}

/**
 * retrieves and stores cigar for each leaf
 * @param child
 */
function addCigar(child) {

    var id = child.sequence.id[0].accession.replace(/[^a-zA-Z0-9]/g, '_')
    var cigar = child.sequence.mol_seq.cigar_line
    syntenic_data.cigar[id] = cigar;
    syntenic_data.sequence[id] = child.sequence.mol_seq.seq ? child.sequence.mol_seq.seq : "No sequence available";
    if(child.id.accession == syntenic_data.ref && syntenic_data.ref == syntenic_data.protein_id){
        syntenic_data.protein_id = id
    }
}


function addZero(x, n) {
    while (x.toString().length < n) {
        x = "0" + x;
    }
    return x;
}


/**
 * redraws cigar lines on genes in case of reference gene changed
 */
function redrawCIGAR() {


    ranked = false;
    rank()

    var json = syntenic_data;
    if (json.ref) {

        gene_list_array = []
        var core_data = json.member;
        var max = 0;
        var keys = [];
        var ptn_keys = [];

        for (var k in core_data) keys.push(k);

        for (var k in json.cigar) ptn_keys.push(k);

        for (var i = 0; i < keys.length; i++) {

            var gene_member_id = keys[i]

            var gene = syntenic_data.member[gene_member_id];
            if (max < gene.end - gene.start) {
                max = gene.end - gene.start;
            }


            var transcript_len = gene.Transcript.length;
            while (transcript_len--) {

                if (gene.Transcript[transcript_len].Translation && ptn_keys.indexOf(gene.Transcript[transcript_len].Translation.id) >= 0) {

                    var temp_member_id = gene.Transcript[transcript_len].Translation.id
                    if (document.getElementById("id" + temp_member_id) !== null) {

                        var gene_start;

                        var gene_stop;
                        var svg = jQuery("#id" + temp_member_id).svg("get")

                        var translation_start = gene.Transcript[transcript_len].Translation.start;

                        if (gene.Transcript[transcript_len].start < gene.Transcript[transcript_len].end) {
                            gene_start = gene.Transcript[transcript_len].start;
                            gene_stop = gene.Transcript[transcript_len].end;
                        }
                        else {
                            gene_start = gene.Transcript[transcript_len].end;
                            gene_stop = gene.Transcript[transcript_len].start;

                        }
                        var maxLentemp = jQuery(window).width() * 0.6;
                        var newEnd_temp = max;
                        var stopposition = ((gene_stop - gene_start) + 1) * parseFloat(maxLentemp) / (newEnd_temp);
                        var temp_div = svg;

                        var strand = gene.Transcript[transcript_len].strand

                        if (temp_member_id != protein_member_id) {

                            var g = svg.group({class: 'style1'});

                            var ref_transcript = 0
                            jQuery.map(syntenic_data.member[syntenic_data.ref].Transcript, function (obj) {
                                if (obj.Translation && obj.Translation.id == protein_member_id) {
                                    ref_transcript = syntenic_data.member[syntenic_data.ref].Transcript.indexOf(obj)
                                }
                            });


                            dispCigarLine(g, syntenic_data.cigar[gene.Transcript[transcript_len].Translation.id], 1, top, gene_start, stopposition, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, ref_data.Transcript[ref_transcript].Exon.toJSON(), translation_start, strand, syntenic_data.cigar[protein_member_id], ref_data.strand, "style1", gene.Transcript[transcript_len].Translation.id);


                            var g = svg.group({class: 'style2'});

                            dispCigarLine(g, syntenic_data.cigar[gene.Transcript[transcript_len].Translation.id], 1, top, stopposition, gene_start, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, ref_data.Transcript[ref_transcript].Exon.toJSON(), translation_start, strand, syntenic_data.cigar[protein_member_id], ref_data.strand, "style2", gene.Transcript[transcript_len].Translation.id);

                        } else {


                            var g = svg.group({class: 'style1'});

                            dispCigarLineRef(g, syntenic_data.cigar[gene.Transcript[transcript_len].Translation.id], 1, top, gene_start, stopposition, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, gene.Transcript[transcript_len].Exon.toJSON(), translation_start, "style1", gene.Transcript[transcript_len].Translation.id, gene.strand);


                            var g = svg.group({class: 'style2'});

                            dispCigarLineRef(g, syntenic_data.cigar[gene.Transcript[transcript_len].Translation.id], 1, top, stopposition, gene_start, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, gene.Transcript[transcript_len].Exon.toJSON(), translation_start, "style2", gene.Transcript[transcript_len].Translation.id, gene.strand);

                        }
                    }
                }

            }

        }

        checkVisuals();


    } else {
        jQuery("#gene_widget").html("")
        jQuery("#gene_widget").html("Selected Gene not found.")
        jQuery("#gene_tree_nj").html("<span style='font-size: large; text-align: center'>Selected Gene not found.</span>")
    }
}

/**
 * changes length of exons of reference gene based on transcript start and end position
 */
function set_members_length() {
    var exon_nu = 0
    var noofrefcds = 0;
    var i = null;

    jQuery.each(syntenic_data.member, function (key, data) {
        var transcripts = syntenic_data.member[key].Transcript.length
        for(var t=0; t<transcripts; t++){
            if(syntenic_data.member[key].Transcript[t].Translation){
                var exon_nu = 0
                syntenic_data.member[key].Transcript[t].Exon.sort(sort_by('start', true, parseInt));

                var diff = parseInt(syntenic_data.member[key].Transcript[t].Exon[exon_nu].end - syntenic_data.member[key].Transcript[t].Translation.start) + parseInt(1)

                while (diff < 0) {
                    syntenic_data.member[key].Transcript[t].Exon[exon_nu].length = 0
                    exon_nu++;
                    diff = parseInt(syntenic_data.member[key].Transcript[t].Exon[exon_nu].end - syntenic_data.member[key].Transcript[t].Translation.start) + parseInt(1)
                }

                syntenic_data.member[key].Transcript[t].Exon[exon_nu].length = diff;
                syntenic_data.member[key].Transcript[t].Exon[exon_nu]._start += syntenic_data.member[key].Transcript[t].Translation.start - syntenic_data.member[key].Transcript[t].Exon[exon_nu].start;
                exon_nu++;


                var check = parseInt(syntenic_data.member[key].Transcript[t].Translation.end - syntenic_data.member[key].Transcript[t].Exon[exon_nu].end)

                while (check > 0) {
                    diff = parseInt(syntenic_data.member[key].Transcript[t].Exon[exon_nu].end - syntenic_data.member[key].Transcript[t].Exon[exon_nu].start) + parseInt(1)
                    syntenic_data.member[key].Transcript[t].Exon[exon_nu].length = diff;
                    exon_nu++;
                    check = parseInt(syntenic_data.member[key].Transcript[t].Translation.end - syntenic_data.member[key].Transcript[t].Exon[exon_nu].end)
                }

                var diff = parseInt(syntenic_data.member[key].Transcript[t].Translation.end - syntenic_data.member[key].Transcript[t].Exon[exon_nu].start)
                syntenic_data.member[key].Transcript[t].Exon[exon_nu].length = diff
                exon_nu++;

                for (var exon_nu; exon_nu < syntenic_data.member[key].Transcript[t].Exon.length; exon_nu++) {
                    syntenic_data.member[key].Transcript[t].Exon[exon_nu].length = 0
                }

                for (var exon_nu = 0; exon_nu < syntenic_data.member[key].Transcript[t].Exon.length; exon_nu++) {
                    if (syntenic_data.member[key].Transcript[t].Exon[exon_nu].length > 0) {
                        noofrefcds++;
                    }
                }

            }
        }

        if(key == syntenic_data.ref){
            ref_data.formated_cigar = format_ref_cigar();
            ref_data.noofrefcds = noofrefcds;
        }
    })
}

/**
 * resets length of exons of reference gene
 */
function set_members_length_to_def() {
    var i = 10;

    jQuery.each(syntenic_data.member, function (key, data) {
        var transcripts = syntenic_data.member[key].Transcript.length
        for(var t=0; t<transcripts; t++){
            var exon_nu = syntenic_data.member[key].Transcript[t].Exon.length;

            while (exon_nu--) {
                syntenic_data.member[key].Transcript[t].Exon[exon_nu].length = (syntenic_data.member[key].Transcript[t].Exon[exon_nu].end - syntenic_data.member[key].Transcript[t].Exon[exon_nu].start) + 1
            }
        }
    })
}


/**
 * replaces a character in string with index and alternative character
 * @param str string
 * @param index index of character to be replaced
 * @param character alternative character
 * @returns {string}
 */
function replaceAt(str, index, character) {
    return str.substr(0, index) + character + str.substr(index + character.length);
}


/**
 * updates reference gene information when reference change happens
 * @param new_gene_id new reference gene id
 * @param new_protein_id new reference protein id
 */
function changeReference(new_gene_id, new_protein_id) {
    jQuery("#id" + protein_member_id + "geneline").attr("stroke", "green")
    jQuery(".genelabel").attr("fill", "gray")

    set_members_length_to_def()

    ranked = false;

    jQuery("#circle" + protein_member_id).attr("r", 4)
    jQuery("#circle" + new_protein_id).attr("r", 6)


    jQuery("#circle" + protein_member_id).css("stroke-width", "1px")
    jQuery("#circle" + new_protein_id).css("stroke-width", "2px")

    jQuery("#circle" + protein_member_id).css("stroke", "steelblue")
    jQuery("#circle" + new_protein_id).css("stroke", "black")

    jQuery("#id" + new_protein_id + "geneline").attr("stroke", "red")
    jQuery("." + new_protein_id + "genetext").attr("fill", "red")

    syntenic_data.ref = new_gene_id;
    protein_member_id = new_protein_id
    syntenic_data.protein_id = new_protein_id;

    jQuery.map(syntenic_data.member[syntenic_data.ref].Transcript, function (obj) {
        if (obj.Translation && obj.Translation.id == protein_member_id) {
            var i = syntenic_data.member[syntenic_data.ref].Transcript.indexOf(obj)
            syntenic_data.transcript_id = syntenic_data.member[syntenic_data.ref].Transcript[i].id;
        }
    });

    jQuery(".match").remove()
    jQuery(".insert").remove()
    jQuery(".delete").remove()

    member_id = new_gene_id;
    ref_data = syntenic_data.member[member_id]


    set_members_length();
    redrawCIGAR()
}

var sort_by = function (field, reverse, primer) {

    var key = primer ?
        function (x) {
            return primer(x[field])
        } :
        function (x) {
            return x[field]
        };

    reverse = [1, 1][+!!reverse];

    return function (a, b) {
        return a = key(a), b = key(b), reverse * ((a > b) - (b > a));
    }
}

/**
 * set control elements in div
 * @param control_div div name place holder
 */
function setControls(control_div) {

    var table = jQuery("<table cellpadding='2px'></table>");

    var row_spacing = jQuery("<tr></tr>");
    var column_spanning = jQuery("<th colspan=6></th>");
    column_spanning.html("Visual Controls")
    row_spacing.append(column_spanning)

    table.append(row_spacing)


    var row1 = jQuery("<tr></tr>");
    var column1 = jQuery("<td></td>");

    var input1 = jQuery('<input>', {
        type: "checkbox",
        id: "deleteCheck",
        onclick: 'toggleCigar(".delete")',
        "checked": "checked"
    });
    column1.html(input1)
    row1.append(column1)

    var column2 = jQuery("<td></td>");
    column2.html("Deletion")
    row1.append(column2)
    table.append(row1)

    var row2 = jQuery("<tr></tr>");
    var column1 = jQuery("<td></td>");

    var input = jQuery('<input>', {
        type: "checkbox",
        id: "matchCheck",
        onclick: 'toggleCigar(".match")',
        "checked": "checked"
    });
    column1.html(input)
    row1.append(column1)
    var column2 = jQuery("<td></td>");

    column2.html("Exon Match")
    row1.append(column2)

    table.append(row2)

    var row3 = jQuery("<tr></tr>");
    var column1 = jQuery("<td></td>");
    var input = jQuery('<input>', {
        type: "checkbox",
        id: "insertCheck",
        onclick: 'toggleCigar(".insert")',
        "checked": "checked"
    });
    column1.html(input)
    row1.append(column1)

    var column2 = jQuery("<td></td>");

    column2.html("Insertion")
    row1.append(column2)

    table.append(row3)


    var row_spacing = jQuery("<tr></tr>");
    var column_spanning = jQuery("<th colspan=4></th>");
    column_spanning.html("Label")
    row_spacing.append(column_spanning)

    table.append(row_spacing)


    var row4 = jQuery("<tr></tr>");
    var column1 = jQuery("<td></td>");
    var input = jQuery('<input>', {
        type: "radio",
        name: "label_type",
        value: "gene_info",
        onclick: 'changeToGeneInfo()',
        "checked": "checked"
    });
    column1.html(input)
    row4.append(column1)

    var column2 = jQuery("<td></td>");

    column2.html("Gene Info")
    row4.append(column2)

    // table.append(row4)


    // var row5 = jQuery("<tr></tr>");
    var column3 = jQuery("<td></td>");
    var input = jQuery('<input>', {
        type: "radio",
        name: "label_type",
        value: "gene_stable",
        onclick: 'changeToStable()',
    });
    column3.html(input)
    row4.append(column3)

    var column4 = jQuery("<td></td>");

    column4.html("Stable ID")
    row4.append(column4)

    var column5 = jQuery("<td></td>");
    var input = jQuery('<input>', {
        type: "radio",
        name: "label_type",
        value: "ptn_stable",
        onclick: 'changeToProteinId()',
    });
    column5.html(input)
    row4.append(column5)

    var column6 = jQuery("<td></td>");

    column6.html("Protein ID")
    row4.append(column6)


    table.append(row4)

    var row_spacing = jQuery("<tr></tr>");
    var column_spanning = jQuery("<th colspan=4></th>");
    column_spanning.html("Introns")
    row_spacing.append(column_spanning)

    table.append(row_spacing)

    var row6 = jQuery("<tr></tr>");
    var column1 = jQuery("<td></td>");
    var input = jQuery('<input>', {
        type: "radio",
        name: "view_type",
        value: "without",
        onclick: 'changeToNormal()'
    });
    column1.html(input)
    row6.append(column1)

    var column2 = jQuery("<td></td>");

    column2.html("Full length")
    row6.append(column2)

    var column3 = jQuery("<td></td>");
    var input = jQuery('<input>', {
        type: "radio",
        name: "view_type",
        onclick: 'changeToExon()',
        value: "with",
        "checked": "checked"
    });
    column3.html(input)
    row6.append(column3)

    var column4 = jQuery("<td></td>");

    column4.html("Fixed length")
    row6.append(column4)

    table.append(row6)

    jQuery(control_div).html(table)

}

/**
 * toggles visuals elemets of gene viw depends on controls
 * @param kind
 */
function toggleCigar(kind) {
    jQuery(kind).toggle()
}
