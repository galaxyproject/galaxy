/**
 * Created with IntelliJ IDEA.
 * User: thankia
 * Date: 26/06/2014
 * Time: 16:30
 * To change this template use File | Settings | File Templates.
 */

/**
 * draws exons on genes for normal view
 * @param g group element of svg to draw genes
 * @param svg svg to add group in
 * @param track transcript information
 * @param genestrand gene strand forward or reverse
 * @param div
 * @param gene_start gene start position
 * @param width gene width
 * @param max_len maximum length information
 * @param id
 */


function dispGeneExon(g, svg, track, genestrand, gene_start, width, max_len) {
    var disp_exon = false;
    var geneexons = track.Exon;

    if (geneexons.length > 0) {
        var strand = genestrand;

        var spanclass = ">";

        if (strand == -1 || strand == "-1") {
            spanclass = "<";
        }

        var newStart_temp = gene_start;
        var maxLentemp = width;


        var exon_len = geneexons.length;
        var startposition = 0;
        var stopposition = 0;
        var translation_start;
        var translation_end;

        if (track.Translation) {
            if (track.Translation.start < track.Translation.end) {
                translation_start = track.Translation.start;
                translation_end = track.Translation.end;
            }
            else {
                translation_start = track.Translation.start;
                translation_end = track.Translation.end;
            }
        } else {
            translation_start = geneexons[0].start;
            translation_end = geneexons[exon_len - 1].end;
        }

        var last = null, current = null;

        while (exon_len--) {

            var exon_start;
            var exon_stop;
            if (geneexons[exon_len].start < geneexons[exon_len].end) {
                exon_start = geneexons[exon_len].start;
                exon_stop = geneexons[exon_len].end;
            }
            else {
                exon_start = geneexons[exon_len].end;
                exon_stop = geneexons[exon_len].start;
            }

            current = exon_start;

            startposition = (exon_start - newStart_temp) * parseFloat(maxLentemp) / (max_len);
            stopposition = ((exon_stop - exon_start) + 1) * parseFloat(maxLentemp) / (max_len);

            stopposition -= 1

            if (stopposition < 1) {
                stopposition = 1
            }
            startposition += 1

            svg.rect(g, startposition, 1, stopposition, 10, 2, 2, {
                'id': "exon" + geneexons[exon_len].id + "style1",
                fill: 'white',
                stroke: 'green',
                strokeWidth: 2
            });

            if (exon_len > 0) {
                svg.text(g, startposition - 20, 8, spanclass, {stroke: 'green'});
            }
            disp_exon = true;
        }

        var exon_len = geneexons.length;

        while (exon_len--) {

            var exon_start;
            var exon_stop;
            if (geneexons[exon_len].start < geneexons[exon_len].end) {
                exon_start = geneexons[exon_len].start;
                exon_stop = geneexons[exon_len].end;
            }
            else {
                exon_start = geneexons[exon_len].end;
                exon_stop = geneexons[exon_len].start;
            }

            current = exon_start;

            if (exon_start < translation_start && exon_stop < translation_start) {

                startposition = 0;// ((exon_start - newStart_temp)) * parseFloat(maxLentemp) / (max_len);
                stopposition = ((exon_stop - exon_start) + 1) * parseFloat(maxLentemp) / (max_len);

                startposition = parseFloat(startposition) + parseFloat(jQuery("#exon" + geneexons[exon_len].id + "style1").attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr1', fill: 'gray'});

                last = current;

            }
            else if (exon_start < translation_start && exon_stop > translation_end) {


                startposition = 0;//((exon_start - newStart_temp)) * parseFloat(maxLentemp) / (max_len);
                stopposition = (translation_start - exon_start) * parseFloat(maxLentemp) / (max_len);
                startposition = parseFloat(startposition) + parseFloat(jQuery("#exon" + geneexons[exon_len].id + "style1").attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr2', fill: 'gray'});

                startposition = ((translation_end - exon_start) - 1) * parseFloat(maxLentemp) / (max_len);
                stopposition = (exon_stop - translation_end + 1) * parseFloat(maxLentemp) / (max_len);
                startposition = parseFloat(startposition) + parseFloat(jQuery("#exon" + geneexons[exon_len].id + "style1").attr("x"))


                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr3', fill: 'gray'});

                last = current;
            }
            else if (exon_stop > translation_start && exon_start < translation_start) {

                startposition = 0;
                stopposition = (translation_start - exon_start) * parseFloat(maxLentemp) / (max_len);
                startposition = parseFloat(startposition) + parseFloat(jQuery("#exon" + geneexons[exon_len].id + "style1").attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr4', fill: 'gray'});

                last = current;

            }
            else if (exon_stop > translation_end && exon_start < translation_end) {

                startposition = ((translation_end - exon_start)) * parseFloat(maxLentemp) / (max_len);
                stopposition = (exon_stop - translation_end) * parseFloat(maxLentemp) / (max_len);
                startposition = parseFloat(startposition) + parseFloat(jQuery("#exon" + geneexons[exon_len].id + "style1").attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr5', fill: 'gray'});

                last = current;
            }

            else if (exon_start > translation_start && exon_stop > translation_end) {

                startposition = 1;
                stopposition = (exon_stop - exon_start) * parseFloat(maxLentemp) / (max_len);
                startposition = parseFloat(startposition) + parseFloat(jQuery("#exon" + geneexons[exon_len].id + "style1").attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr6', fill: 'gray'});

                last = current;
            }
        }

    }
}

/**
 * draw normal view gene for specified member and protein id
 * @param member_id member id for the gene to draw
 * @param protein_id translation id for the member gene
 * @param ref gene is reference or hit true or false
 */
function dispGenesForMember_id(div, cigar, member_id, protein_id, ref_cigar) {
    var gene;
    if (ref_cigar) {
        gene = syntenic_data.member[member_id];
    } else {
        gene = syntenic_data.member[member_id];

    }


    var svg = jQuery(div).svg("get")
    var maxLentemp = jQuery(window).width() * 0.6;
    var label = "";
    var j = 0;

    var transcript_len = gene.Transcript.length;

    while (transcript_len--) {

        if (gene.Transcript[transcript_len].Translation && (gene.Transcript[transcript_len].Translation.id == protein_id || gene.Transcript[transcript_len].id == protein_id)) {

            max = gene.Transcript[transcript_len].end - gene.Transcript[transcript_len].start
            var gene_start;
            var gene_stop;
            var gene_length = gene.Transcript[transcript_len].end - gene.Transcript[transcript_len].start

            var translation_start = gene.Transcript[transcript_len].start;
            var translation_end = gene.Transcript[transcript_len].end;
            if (gene.Transcript[transcript_len].Translation) {
                translation_start = gene.Transcript[transcript_len].Translation.start;
                translation_end = gene.Transcript[transcript_len].Translation.end;
            }

            if (gene.Transcript[transcript_len].start < gene.Transcript[transcript_len].end) {
                gene_start = gene.Transcript[transcript_len].start;
                gene_stop = gene.Transcript[transcript_len].end;
            }
            else {
                gene_start = gene.Transcript[transcript_len].end;
                gene_stop = gene.Transcript[transcript_len].start;
            }

            if (gene.Transcript[transcript_len].desc) {
                label = gene.Transcript[transcript_len].desc;
            }
            var border = " border-left: 1px solid #000000; border-right: 1px solid #000000;";
            label = gene.Transcript[transcript_len].desc;
            if (gene.Transcript[transcript_len].layer > j) {
                j = gene.Transcript[transcript_len].layer;
            }
            var top = transcript_len * 25 + 25;
            var stopposition = maxLentemp;//((gene_stop - gene_start) + 1) * parseFloat(maxLentemp) / (newEnd_temp - newStart_temp);
            var margin = "margin-top:15px;margin-bottom:5px;";


            if (transcript_len == 0) {
                margin = "margin-top:15px;margin-bottom:25px;";
            }

            label += gene.reference;

            if (ref_cigar) {

                var ref = syntenic_data.ref

                var ref_transcript = 0

                jQuery.map(syntenic_data.member[syntenic_data.ref].Transcript, function (obj) {
                    if (obj.Translation && obj.Translation.id == protein_member_id) {
                        ref_transcript = syntenic_data.member[syntenic_data.ref].Transcript.indexOf(obj)
                    }
                });

                var text = syntenic_data.member[member_id].species;

                if(syntenic_data.member[member_id].display_name){
                    text += ":"+syntenic_data.member[member_id].display_name
                }else if(syntenic_data.member[member_id].description){
                    text += ":"+syntenic_data.member[member_id].description
                }
                // var text = syntenic_data.member[member_id].species + ":" + syntenic_data.member[member_id].display_name ? "yes" : "no"//syntenic_data.member[member_id].description

                svg.text(parseInt(stopposition) + 10, 10, text, {
                    fontFamily: 'Verdana',
                    fontSize: 10,
                    textAnchor: 'begin',
                    fill: "gray",
                    class: "geneinfo genelabel " + protein_id + "genetext"
                });

                var text = syntenic_data.member[member_id].species + ":" + syntenic_data.member[member_id].id

                svg.text(parseInt(stopposition) + 10, 10, text, {
                    fontFamily: 'Verdana',
                    fontSize: 10,
                    textAnchor: 'begin',
                    fill: "gray",
                    class: "stable genelabel " + protein_id + "genetext"
                });

                var text = syntenic_data.member[member_id].species + ":" + syntenic_data.member[member_id].Transcript[transcript_len].Translation.id

                svg.text(parseInt(stopposition) + 10, 10, text, {
                    fontFamily: 'Verdana',
                    fontSize: 10,
                    textAnchor: 'begin',
                    fill: "gray",
                    class: "protein_id genelabel " + protein_id + "genetext"
                });


                var temp_div = svg;
                svg.line(0, 6, stopposition, 6, {id: 'id' + protein_id + 'geneline', stroke: 'green', strokeWidth: 1});

                var strand = gene.Transcript[transcript_len].strand;

                // if (syntenic_data.member[syntenic_data.ref].strand == gene.Transcript[transcript_len].strand) {
                //     strand = 1;
                // } else {
                //     strand = -1;
                // }
                gene.Transcript[transcript_len].Exon.sort(sort_by('start', true, parseInt));

                var g = svg.group({class: 'style1'});
                dispGeneExon(g, svg, gene.Transcript[transcript_len], gene.strand, gene_start, stopposition, gene_length);

                var g = svg.group({id: 'id' + protein_id + 'style1CIGAR', class: 'style1'});


                dispCigarLine(g, cigar, 1, top, stopposition, gene_start, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, ref_data.Transcript[ref_transcript].Exon.toJSON(), translation_start, strand, ref_cigar, ref_data.strand,  "style1", protein_id);

            }
            else {

                var text = syntenic_data.member[member_id].species;

                if(syntenic_data.member[member_id].display_name){
                    text += ":"+syntenic_data.member[member_id].display_name
                }else if(syntenic_data.member[member_id].description){
                    text += ":"+syntenic_data.member[member_id].description
                }

                svg.text(parseInt(stopposition) + 10, 10, text, {
                    fontFamily: 'Verdana',
                    fontSize: 10,
                    textAnchor: 'red',
                    fill: "red",
                    class: "geneinfo genelabel " + protein_id + "genetext"
                });

                var text = syntenic_data.member[member_id].species + ":" + syntenic_data.member[member_id].id

                svg.text(parseInt(stopposition) + 10, 10, text, {
                    fontFamily: 'Verdana',
                    fontSize: 10,
                    textAnchor: 'begin',
                    fill: "red",
                    class: "stable genelabel " + protein_id + "genetext"
                });

                var text = syntenic_data.member[member_id].species + ":" + syntenic_data.member[member_id].Transcript[transcript_len].Translation.id

                svg.text(parseInt(stopposition) + 10, 10, text, {
                    fontFamily: 'Verdana',
                    fontSize: 10,
                    textAnchor: 'begin',
                    fill: "red",
                    class: "protein_id genelabel " + protein_id + "genetext"
                });


                svg.line(0, 6, stopposition, 6, {id: 'id' + protein_id + 'geneline', stroke: 'red', strokeWidth: 2});


                var temp_div = svg;


                var g = svg.group({class: 'style1'});

                dispGeneExon(g, svg, gene.Transcript[transcript_len], gene.strand, gene_start, stopposition, gene_length);

                var g = svg.group({id: 'id' + protein_id + 'style1CIGAR', class: 'style1 CIGAR'});

                dispCigarLineRef(g, cigar, 1, top,  stopposition, gene_start,  gene.Transcript[transcript_len].Exon.toJSON(), temp_div, gene.Transcript[transcript_len].Exon.toJSON(), translation_start,  "style1", protein_id, gene.strand);

            }

        }
    }
}
