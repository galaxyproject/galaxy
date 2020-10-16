/**
 * Created with IntelliJ IDEA.
 * User: thankia
 * Date: 26/06/2014
 * Time: 16:30
 * To change this template use File | Settings | File Templates.
 */

/**
 * draws exons on genes for exon focused view
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

function dispExon(g, svg, track, genestrand, gene_start, width, max_len, protein_id) {


    var disp_exon = false;
    var geneexons = track.Exon;

    var space = 10 * (geneexons.length - 1)


    if (geneexons.length > 0) {
        var strand = genestrand;

        var spanclass = ">";

        if (strand == -1 || strand == "-1") {
            spanclass = "<";
        }

        var maxLentemp = width - space;


        var exon_len = geneexons.length;
        var startposition = 0;
        var stopposition = 0;
        var transcript_start;
        var transcript_end;

        if (track.Translation) {
            if (track.Translation.start < track.Translation.end) {
                transcript_start = track.Translation.start;
                transcript_end = track.Translation.end;
            }
            else {
                transcript_start = track.Translation.start;
                transcript_end = track.Translation.end;
            }
        } else {
            transcript_start = geneexons[0].start;
            transcript_end = geneexons[exon_len - 1].end;
        }


        geneexons.sort(sort_by('start', true, parseInt));

        var last = null, current = null;

        for (var exon_len = 0; exon_len < geneexons.length; exon_len++) {

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


            if (geneexons[exon_len - 1]) {
                startposition = parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len - 1].id + 'style2').attr("width")) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len - 1].id + 'style2').attr("x")) + 10//(exon_start - newStart_temp) * parseFloat(maxLentemp) / (max_len);
            } else {
                startposition = 1
            }
            stopposition = ((exon_stop - exon_start) + 1) * parseFloat(maxLentemp) / (max_len);

            stopposition -= 1
            startposition += 1

            if (stopposition < 1) {
                stopposition = 1
            }
            svg.rect(g, startposition, 1, stopposition, 10, 2, 2, {
                id: "exon" + geneexons[exon_len].id + "style2",
                fill: 'white',
                stroke: 'green',
                strokeWidth: 2
            });

            if (exon_len < geneexons.length - 1 && disp_exon) {
                svg.text(g, startposition + stopposition + 1, 8, spanclass, {stroke: 'green'});
                disp_exon = false
            } else {
                disp_exon = true;
            }

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

            if (exon_start < transcript_start && exon_stop < transcript_start) {
                startposition = 0;
                stopposition = (exon_stop - exon_start) * parseFloat(maxLentemp) / (max_len);

                startposition = parseFloat(startposition) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len].id + 'style2').attr("x"))

                stopposition = parseInt(stopposition)

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr1', fill: 'gray'});

                last = current;

            }
            else if (exon_start < transcript_start && exon_stop > transcript_end) {
                startposition = 0
                stopposition = (transcript_start - exon_start) * parseFloat(maxLentemp) / (max_len);
                startposition = parseFloat(startposition) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len].id + 'style2').attr("x"))
                stopposition = parseInt(stopposition)

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr2', fill: 'gray'});

                startposition = ((transcript_end - exon_start) - 1) * parseFloat(maxLentemp) / (max_len);
                stopposition = 0;//(exon_stop - transcript_end + 1) * parseFloat(maxLentemp) / (max_len);
                stopposition = parseInt(stopposition)
                startposition = parseFloat(startposition) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len].id + 'style2').attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr3', fill: 'gray'});

                last = current;
            }
            else if (exon_stop > transcript_start && exon_start < transcript_start) {
                startposition = 0;// ((exon_start - newStart_temp)) * parseFloat(maxLentemp) / (max_len);
                stopposition = (transcript_start - exon_start) * parseFloat(maxLentemp) / (max_len);
                stopposition = parseInt(stopposition)

                startposition = parseFloat(startposition) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len].id + 'style2').attr("x"))
                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr4', fill: 'gray'});

                last = current;

            }
            else if (exon_stop > transcript_end && exon_start < transcript_end) {
                startposition = ((transcript_end - exon_start)) * parseFloat(maxLentemp) / (max_len);

                stopposition = (exon_stop - transcript_end) * parseFloat(maxLentemp) / (max_len);
                stopposition = parseInt(stopposition)

                startposition = parseFloat(startposition) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len].id + 'style2').attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr5', fill: 'gray'});

                last = current;

            }

            else if (exon_start > transcript_start && exon_stop > transcript_end) {
                startposition = 1;
                stopposition = (exon_stop - exon_start) * parseFloat(maxLentemp) / (max_len);
                stopposition = parseInt(stopposition)
                startposition = parseFloat(startposition) + parseFloat(jQuery('div[id*="' + protein_id + '"] #exon' + geneexons[exon_len].id + 'style2').attr("x"))

                svg.rect(g, startposition, 1, stopposition, 10, {class: 'utr6', fill: 'gray'});

                last = current;
            }
        }

    }
}

/**
 * draw exon focused view gene for specified member and protein id
 * @param member_id member id for the gene to draw
 * @param protein_id translation id for the member gene
 * @param ref gene is reference or hit true or false
 */

function dispGenesExonForMember_id(div, cigar, member_id, protein_id, ref_cigar) {

    var gene;
    if (ref_cigar) {
        gene = syntenic_data.member[member_id];
    } else {
        gene = syntenic_data.member[member_id];

    }


    var svg = jQuery(div).svg("get")
    var g = svg.group({class: 'style2'});

    var maxLentemp = jQuery(window).width() * 0.6;

    var label = "";
    var j = 0;

    var transcript_len = gene.Transcript.length;
    while (transcript_len--) {
        if (gene.Transcript[transcript_len].Translation && (gene.Transcript[transcript_len].Translation.id == protein_id || gene.Transcript[transcript_len].id == protein_id)) {
            max = gene.Transcript[transcript_len].end - gene.Transcript[transcript_len].start
            var gene_start;
            var gene_stop;
            var gene_length = 0;

            var geneexons = gene.Transcript[transcript_len].Exon;
            if (geneexons.length > 0) {
                var exon_len = geneexons.length;
                while (exon_len--) {
                    gene_length += geneexons[exon_len].end - geneexons[exon_len].start;
                }
            }


            var transcript_start = gene.Transcript[transcript_len].start;
            var transcript_end = gene.Transcript[transcript_len].end;
            if (gene.Transcript[transcript_len].Translation) {
                transcript_start = gene.Transcript[transcript_len].Translation.start;
                transcript_end = gene.Transcript[transcript_len].Translation.end;
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
            var stopposition = maxLentemp
            var margin = "margin-top:15px;margin-bottom:5px;";

            if (transcript_len == 0) {
                margin = "margin-top:15px;margin-bottom:25px;";
            }

            label += gene.reference;

            if (ref_cigar) {

                var ref = syntenic_data.ref
                var temp_div = svg;
                var strand = gene.Transcript[transcript_len].strand;


                gene.Transcript[transcript_len].Exon.sort(sort_by('start', true, parseInt));


                dispExon(g, svg, gene.Transcript[transcript_len], gene.strand, gene_start, stopposition, gene_length, protein_id);

                var g = svg.group({id: 'id' + protein_id + 'style2CIGAR', class: 'style2 CIGAR'});


                var ref_transcript = 0
                jQuery.map(syntenic_data.member[syntenic_data.ref].Transcript, function (obj) {
                    if (obj.Translation && obj.Translation.id == protein_member_id) {
                        ref_transcript = syntenic_data.member[syntenic_data.ref].Transcript.indexOf(obj)
                    }
                });


                dispCigarLine(g, cigar, 1, top, stopposition, gene_start, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, ref_data.Transcript[ref_transcript].Exon.toJSON(), transcript_start, strand, ref_cigar, ref_data.strand, "style2", protein_id);
            }
            else {
                var temp_div = svg;

                dispExon(g, svg, gene.Transcript[transcript_len], gene.strand, gene_start, stopposition, gene_length, protein_id);

                var g = svg.group({id: 'id' + protein_id + 'style2CIGAR', class: 'style2 CIGAR'});


                dispCigarLineRef(g, cigar, 1, top, stopposition, gene_start, gene.Transcript[transcript_len].Exon.toJSON(), temp_div, gene.Transcript[transcript_len].Exon.toJSON(), transcript_start, "style2", protein_id, gene.strand);
            }
        }
    }
}
