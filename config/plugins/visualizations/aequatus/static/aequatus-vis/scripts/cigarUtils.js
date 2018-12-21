/**
 * Created by thankia on 16/09/2016.
 */
/**
 * Useful when dealing with a subtree and deletion is present because of  absence member, replaces with it 'I' to ignore
 * @param ref_cigar_string reference cigar string
 * @returns {*}
 */
function checkCigar() {
    var cigar_list = [];
    var cigar_id = [];
    var cigars_json = {};

    var member = syntenic_data.cigar

    var reverse_cigar = []
    jQuery.map(syntenic_data.member, function (obj) {
        if (syntenic_data.ref.strand != obj.strand) {
            jQuery.map(obj.Transcript, function (transcript) {
                if(transcript.Translation){
                    reverse_cigar.push(transcript.Translation.id)
                }
            })
        }
    });

    for (var id in syntenic_data.cigar) {

        if (member.hasOwnProperty(id)) {

            var cigar_string = expandCigar(member[id])


            if (reverse_cigar.indexOf(id) >= 0) {
                cigar_string.split("").reverse().join()
            }

            cigar_list.push(cigar_string);
            cigar_id.push(id)
        }
    }
    var pos = [];
    for (var i = 0; i < cigar_list[0].length; i++) {
        if (cigar_list[0][i] == 'D') {
            for (var j = 1; j < cigar_list.length; j++) {
                if (cigar_list[j][i] == 'M') {
                    break;
                }
                if (j == cigar_list.length - 1) {
                    cigar_list[0] = replaceAt(cigar_list[0], i, "I")
                    pos.push(i)
                }
            }
        }
    }

    // to clean all cigars...
    for (var i = 0; i < cigar_list.length; i++) {
        cigar_list[i] = cigar_list[i].split("")

        for (var j = pos.length - 1; j >= 0; j--) {
            cigar_list[i].splice(pos[j], 1);
        }

        cigar_string = cigar_list[i].join("")

        if (reverse_cigar.indexOf(cigar_id[i]) >= 0) {
            cigar_string.split("").reverse().join()
        }


        var new_cigar = compressCigar(cigar_string)


        cigars_json[cigar_id[i]] = new_cigar

    }


    return cigars_json
}


function expandCigar(cigar, toNucleotide) {
    var cigar_string = "";
    var cigar = cigar.replace(/([SIXMND])/g, ":$1,");
    var cigars_array = cigar.split(',');

    var multiply = 1;
    if(toNucleotide){
        multiply = 3
    }

    for (var j = 0; j < cigars_array.length - 1; j++) {
        var cigar = cigars_array[j].split(":");
        var key = cigar[1];
        var length = cigar[0] * multiply;
        if (!length) {
            length = multiply
        }
        while (length--) {
            cigar_string += key;
        }

        cigar_string += "";
    }

    return cigar_string
}

function compressCigar(cigar_string) {
    cigar_string = cigar_string.replace(/(MD)/g, "M,D");
    cigar_string = cigar_string.replace(/(DM)/g, "D,M");
    var cigar_array = cigar_string.split(",")
    var new_cigar = ""

    for (var a = 0; a < cigar_array.length; a++) {
        var key = cigar_array[a].charAt(0)
        var length = cigar_array[a].length;

        if (length > 1) {
            new_cigar += length
        }
        new_cigar += key
    }

    return new_cigar;
}

/**
 * formats hit cigar to match with reference cigar for drawing on genes
 * @param ref_exons list of reference exons
 * @param hit_cigar hit cigar string
 * @param colours colour array
 * @param ref_cigar reference cigar string
 * @param reverse hit strand is reverse or not
 * @param ref_strand reference strand
 * @returns {string} formated cigar
 */
function format_ref_cigar() {
    var i = null;
    jQuery.map(syntenic_data.member[syntenic_data.ref].Transcript, function (obj) {
        if (obj.Translation && obj.Translation.id == protein_member_id) {
            i = syntenic_data.member[syntenic_data.ref].Transcript.indexOf(obj)
        }
    });

    var ref_exons = syntenic_data.member[syntenic_data.ref].Transcript[i].Exon

    var ref_cigar = syntenic_data.cigar[protein_member_id]

    var no_of_exons = ref_exons.length;

    var ref_strand = syntenic_data.member[syntenic_data.ref].strand;

    var ref_exon_array = [];

    while (i < no_of_exons) {
        var length = ref_exons[i].length

        var ref_exon = length
        if (parseInt(length) >= 0) {
            ref_exon_array.push(ref_exon)
        }
        i++;
    }


    var cigar_string = expandCigar(ref_cigar, "true")


    var i = 0
    var total_len = 0;
    var flag = false;
    var cigar_string_match = cigar_string.replace(/D/g, '');

    // if cigar is shorter than CDS than last CDSs becomes 0

    while (i < ref_exon_array.length) {
        if (flag == false) {
            if (parseInt(total_len) + parseInt(ref_exon_array[i]) < cigar_string_match.length) {
                total_len += ref_exon_array[i];
            }
            else {
                ref_exon_array[i] = cigar_string_match.length - total_len;
                total_len = cigar_string_match.length;
                flag = true;
            }
        } else {
            ref_exon_array[i] = 0;
        }
        i++;
    }


    var ref_cigar_count = 0;

    var hit_position = 0;

    var ref_exon_number = 0;
    var count_match = 0;

    var formated_ref_cigar = []

    var last_pos = 0;
    // dividing reference cigar into chunks based on exon length (ignoring deletions)
    while (ref_cigar_count < cigar_string.length) {

        if (cigar_string.charAt(ref_cigar_count) == 'M') {
            if (count_match == ref_exon_array[ref_exon_number]) {
                ref_exon_number++;
                formated_ref_cigar.push(cigar_string.substr(last_pos, hit_position));
                count_match = 0;
                last_pos += hit_position;
                hit_position = 0;
            }
            count_match++;
        }
        hit_position++;
        ref_cigar_count++;
    }

    formated_ref_cigar.push(cigar_string.substr(last_pos, hit_position));
    var i = 0;


    return formated_ref_cigar;

}

/**
 * formats hit cigar to match with reference cigar for drawing on genes
 * @param ref_exons list of reference exons
 * @param hit_cigar hit cigar string
 * @param colours colour array
 * @param ref_cigar reference cigar string
 * @param reverse hit strand is reverse or not
 * @param ref_strand reference strand
 * @returns {string} formated cigar
 */
function formatCigar(ref_exons, hit_cigar, colours, ref_cigar, hit_strand, ref_strand) {

    var no_of_exons = ref_exons.length
    var hit_cigar_arr = [];
    var ref_exon_array = [];
    var last_pos = 0;
    var i = 0
    var j = 0;

    var ref_cigar_array = ref_data.formated_cigar;
    var cigar_string = expandCigar(ref_cigar, "true")
    hit_cigar = expandCigar(hit_cigar, "true")

    while (i < ref_cigar_array.length) {
        ref_exon_array.push(ref_cigar_array[i].replace(/D/g, "").length)
        // ref_exons[i] = ref_exons[i].length;
        i++;
    }

    var i = 0
    while (i < ref_exons.length) {
        // ref_exon_array.push(ref_cigar_array[i].replace(/D/g, "").length)
        ref_exons[i] = ref_exons[i].length;
        i++;
    }
    if (hit_strand != ref_strand) {
        ref_exons = ref_exons.reverse();
        var sum = 0;

        for (i = 0; i < ref_exons.length; i++) {
            sum += Number(ref_exons[i]);
        }
        var ref_cigar = cigar_string.replace(/D/g, "").length
    }

    if (hit_strand != ref_strand && ref_strand == 1) {
        cigar_string = cigar_string.split("").reverse().join("");
        hit_cigar = hit_cigar.split("").reverse().join("");
        //     // ref_cigar_array = ref_cigar_array.reverse()
    }
    else if(hit_strand == ref_strand && ref_strand == -1){// && hit_strand != -1){
        cigar_string = cigar_string.split("").reverse().join("");
        hit_cigar = hit_cigar.split("").reverse().join("");

    }



    // if cigar string is D in all sequences (because of subset) that that part get removed
    while (j < cigar_string.length) {
        if (cigar_string.charAt(j) == 'D') {
            if (hit_cigar.charAt(j) == 'M') {
                hit_cigar = replaceAt(hit_cigar, j, "_");
            }
            else if (hit_cigar.charAt(j) == 'D') {
                hit_cigar = replaceAt(hit_cigar, j, "I");
            }
        }
        j++;
    }


    var ref_cigar_count = 0;

    var hit_position = 0;

    var ref_exon_number = 0;
    var count_match = 0;

    var temp_array = [];

    // dividing reference cigar into chunks based on exon length (ignoring deletions)
    while (ref_cigar_count < cigar_string.length) {

        if (cigar_string.charAt(ref_cigar_count) == 'M') {

            if (count_match == ref_exons[ref_exon_number]) {
                ref_exon_number++;
                hit_cigar_arr.push(hit_cigar.substr(last_pos, hit_position));
                temp_array.push(hit_position + " : " + ref_exon_number)

                count_match = 0;
                last_pos += hit_position;
                hit_position = 0;
                if (hit_strand != ref_strand) {
                }

            }
            count_match++;
        }

        hit_position++;
        ref_cigar_count++;
    }
    hit_cigar_arr.push(hit_cigar.substr(last_pos, hit_position));
    return hit_cigar_arr.join("-");

}
