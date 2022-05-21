from __future__ import print_function

from shutil import copyfile


def load_microbial_data(GALAXY_DATA_INDEX_DIR, sep="\t"):
    # FIXME: this function is duplicated in the DynamicOptions class.  It is used here only to
    # set data.name in exec_after_process().
    microbe_info = {}
    orgs = {}

    filename = "%s/microbial_data.loc" % GALAXY_DATA_INDEX_DIR
    for line in open(filename):
        line = line.rstrip("\r\n")
        if line and not line.startswith("#"):
            fields = line.split(sep)
            # read each line, if not enough fields, go to next line
            try:
                info_type = fields.pop(0)
                if info_type.upper() == "ORG":
                    # ORG     12521   Clostridium perfringens SM101   bacteria        Firmicutes      CP000312,CP000313,CP000314,CP000315     http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?db=genomeprj&cmd=Retrieve&dopt=Overview&list_uids=12521
                    org_num = fields.pop(0)
                    name = fields.pop(0)
                    kingdom = fields.pop(0)
                    group = fields.pop(0)
                    chromosomes = fields.pop(0)
                    info_url = fields.pop(0)
                    link_site = fields.pop(0)
                    if org_num not in orgs:
                        orgs[org_num] = {}
                        orgs[org_num]["chrs"] = {}
                    orgs[org_num]["name"] = name
                    orgs[org_num]["kingdom"] = kingdom
                    orgs[org_num]["group"] = group
                    orgs[org_num]["chromosomes"] = chromosomes
                    orgs[org_num]["info_url"] = info_url
                    orgs[org_num]["link_site"] = link_site
                elif info_type.upper() == "CHR":
                    # CHR     12521   CP000315        Clostridium perfringens phage phiSM101, complete genome 38092   110684521       CP000315.1
                    org_num = fields.pop(0)
                    chr_acc = fields.pop(0)
                    name = fields.pop(0)
                    length = fields.pop(0)
                    gi = fields.pop(0)
                    gb = fields.pop(0)
                    info_url = fields.pop(0)
                    chr = {}
                    chr["name"] = name
                    chr["length"] = length
                    chr["gi"] = gi
                    chr["gb"] = gb
                    chr["info_url"] = info_url
                    if org_num not in orgs:
                        orgs[org_num] = {}
                        orgs[org_num]["chrs"] = {}
                    orgs[org_num]["chrs"][chr_acc] = chr
                elif info_type.upper() == "DATA":
                    # DATA    12521_12521_CDS 12521   CP000315        CDS     bed     /home/djb396/alignments/playground/bacteria/12521/CP000315.CDS.bed
                    uid = fields.pop(0)
                    org_num = fields.pop(0)
                    chr_acc = fields.pop(0)
                    feature = fields.pop(0)
                    filetype = fields.pop(0)
                    path = fields.pop(0)
                    data = {}
                    data["filetype"] = filetype
                    data["path"] = path
                    data["feature"] = feature

                    if org_num not in orgs:
                        orgs[org_num] = {}
                        orgs[org_num]["chrs"] = {}
                    if "data" not in orgs[org_num]["chrs"][chr_acc]:
                        orgs[org_num]["chrs"][chr_acc]["data"] = {}
                    orgs[org_num]["chrs"][chr_acc]["data"][uid] = data
                else:
                    continue
            except Exception:
                continue
    for org_num in orgs:
        org = orgs[org_num]
        if org["kingdom"] not in microbe_info:
            microbe_info[org["kingdom"]] = {}
        if org_num not in microbe_info[org["kingdom"]]:
            microbe_info[org["kingdom"]][org_num] = org
    return microbe_info


# post processing, set build for data and add additional data to history
def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    base_dataset = next(iter(out_data.values()))
    history = base_dataset.history
    if history is None:
        print("unknown history!")
        return
    kingdom = param_dict.get("kingdom", None)
    org = param_dict.get("org", None)

    # if not (kingdom or group or org):
    if not (kingdom or org):
        print("Parameters are not available.")

    GALAXY_DATA_INDEX_DIR = app.config.tool_data_path
    microbe_info = load_microbial_data(GALAXY_DATA_INDEX_DIR, sep="\t")
    split_stdout = stdout.split("\n")
    basic_name = ""
    for line in split_stdout:
        fields = line.split("\t")
        if fields[0] == "#File1":
            description = fields[1]
            chr = fields[2]
            dbkey = fields[3]
            file_type = fields[4]
            data = next(iter(out_data.values()))
            data.set_size()
            basic_name = data.name
            data.name = (
                data.name
                + " ("
                + microbe_info[kingdom][org]["chrs"][chr]["data"][description]["feature"]
                + " for "
                + microbe_info[kingdom][org]["name"]
                + ":"
                + chr
                + ")"
            )
            data.dbkey = dbkey
            data.info = data.name
            data = app.datatypes_registry.change_datatype(data, file_type)
            data.init_meta()
            data.set_peek()
            app.model.context.add(data)
            app.model.context.flush()
        elif fields[0] == "#NewFile":
            description = fields[1]
            chr = fields[2]
            dbkey = fields[3]
            filepath = fields[4]
            file_type = fields[5]
            newdata = app.model.HistoryDatasetAssociation(
                create_dataset=True, sa_session=app.model.context
            )  # This import should become a library
            newdata.set_size()
            newdata.extension = file_type
            newdata.name = (
                basic_name
                + " ("
                + microbe_info[kingdom][org]["chrs"][chr]["data"][description]["feature"]
                + " for "
                + microbe_info[kingdom][org]["name"]
                + ":"
                + chr
                + ")"
            )
            app.model.context.add(newdata)
            app.model.context.flush()
            app.security_agent.copy_dataset_permissions(base_dataset.dataset, newdata.dataset)
            history.add_dataset(newdata)
            app.model.context.add(history)
            app.model.context.flush()
            try:
                copyfile(filepath, newdata.file_name)
                newdata.info = newdata.name
                newdata.state = newdata.states.OK
            except Exception:
                newdata.info = "The requested file is missing from the system."
                newdata.state = newdata.states.ERROR
            newdata.dbkey = dbkey
            newdata.init_meta()
            newdata.set_peek()
            app.model.context.flush()
