# post processing, add sequence and additional annoation info if available
from six.moves.urllib.parse import urlencode

from galaxy.datatypes.images import create_applet_tag_peek


def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    primary_data = next(iter(out_data.values()))

    # default params for LAJ type
    params = {
        "alignfile1": "display?id=%s" % primary_data.id,
        "buttonlabel": "Launch LAJ",
        "title": "LAJ in Galaxy",
        "posturl": "history_add_to?%s"
        % urlencode(
            {
                "history_id": primary_data.history_id,
                "ext": "lav",
                "name": "LAJ Output",
                "info": "Added by LAJ",
                "dbkey": primary_data.dbkey,
            }
        ),
    }
    for name, data in inp_data.items():
        if name == "maf_input":
            params["alignfile1"] = "display?id=%s" % data.id
        elif name == "seq_file1" and data.state == data.states.OK and data.has_data():
            params["file1seq1"] = "display?id=%s" % data.id
        elif name == "seq_file2" and data.state == data.states.OK and data.has_data():
            params["file1seq2"] = "display?id=%s" % data.id
        elif name == "exonfile" and data.state == data.states.OK and data.has_data():
            params["exonfile"] = "display?id=%s" % data.id
        elif name == "repeatfile" and data.state == data.states.OK and data.has_data():
            params["repeatfile"] = "display?id=%s" % data.id
        elif name == "annotationfile" and data.state == data.states.OK and data.has_data():
            params["annotationfile"] = "display?id=%s" % data.id
        elif name == "underlayfile" and data.state == data.states.OK and data.has_data():
            params["underlayfile"] = "display?id=%s" % data.id
        elif name == "highlightfile" and data.state == data.states.OK and data.has_data():
            params["highlightfile"] = "display?id=%s" % data.id

    if "file1seq1" not in params and "file1seq2" not in params:
        params["noseq"] = "true"

    class_name = "edu.psu.cse.bio.laj.LajApplet.class"
    archive = "/static/laj/laj.jar"
    primary_data.peek = create_applet_tag_peek(class_name, archive, params)
    app.model.context.add(primary_data)
    app.model.context.flush()
