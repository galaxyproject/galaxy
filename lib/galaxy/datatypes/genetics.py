"""
rgenetics datatypes
Use at your peril
Ross Lazarus
for the rgenetics and galaxy projects

genome graphs datatypes derived from Interval datatypes
genome graphs datasets have a header row with appropriate columnames
The first column is always the marker - eg columname = rs, first row= rs12345 if the rows are snps
subsequent row values are all numeric ! Will fail if any non numeric (eg '+' or 'NA') values
ross lazarus for rgenetics
august 20 2007
"""
import logging
import os
import re
import sys
from typing import (
    Dict,
    IO,
    List,
    Optional,
    Union,
)
from urllib.parse import quote_plus

from markupsafe import escape

from galaxy.datatypes import metadata
from galaxy.datatypes.data import (
    DatatypeValidation,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasExtraFilesAndMetadata,
    HasMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.text import Html
from galaxy.util import (
    nice_size,
    unicodify,
)
from galaxy.util.compression_utils import FileObjType

gal_Log = logging.getLogger(__name__)
verbose = False

# https://genome.ucsc.edu/goldenpath/help/hgGenomeHelp.html
VALID_GENOME_GRAPH_MARKERS = re.compile(r"^(chr.*|RH.*|rs.*|SNP_.*|CN.*|A_.*)")
VALID_GENOTYPES_LINE = re.compile(r"^([a-zA-Z0-9]+)(\s([0-9]{2}|[A-Z]{2}|NC|\?\?))+\s*$")


@build_sniff_from_prefix
class GenomeGraphs(Tabular):
    """
    Tab delimited data containing a marker id and any number of numeric values
    """

    MetadataElement(name="markerCol", default=1, desc="Marker ID column", param=metadata.ColumnParameter)
    MetadataElement(name="columns", default=3, desc="Number of columns", readonly=True)
    MetadataElement(name="column_types", default=[], desc="Column types", readonly=True, visible=False)
    file_ext = "gg"

    def __init__(self, **kwd):
        """
        Initialize gg datatype, by adding UCSC display apps
        """
        super().__init__(**kwd)
        self.add_display_app("ucsc", "Genome Graph", "as_ucsc_display_file", "ucsc_links")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        dataset.metadata.markerCol = 1
        header = open(dataset.file_name).readlines()[0].strip().split("\t")
        dataset.metadata.columns = len(header)
        t = ["numeric" for x in header]
        t[0] = "string"
        dataset.metadata.column_types = t

    def as_ucsc_display_file(self, dataset: DatasetProtocol, **kwd) -> Union[FileObjType, str]:
        """
        Returns file
        """
        return open(dataset.file_name, "rb")

    def ucsc_links(self, dataset: DatasetProtocol, type: str, app, base_url: str) -> List:
        """
        from the ever-helpful angie hinrichs angie@soe.ucsc.edu
        a genome graphs call looks like this

        http://genome.ucsc.edu/cgi-bin/hgGenome?clade=mammal&org=Human&db=hg18&hgGenome_dataSetName=dname
        &hgGenome_dataSetDescription=test&hgGenome_formatType=best%20guess&hgGenome_markerType=best%20guess
        &hgGenome_columnLabels=best%20guess&hgGenome_maxVal=&hgGenome_labelVals=
        &hgGenome_maxGapToFill=25000000&hgGenome_uploadFile=http://galaxy.esphealth.org/datasets/333/display/index
        &hgGenome_doSubmitUpload=submit

        Galaxy gives this for an interval file

        http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg18&position=chr1:1-1000&hgt.customText=
        http%3A%2F%2Fgalaxy.esphealth.org%2Fdisplay_as%3Fid%3D339%26display_app%3Ducsc

        """
        ret_val = []
        if not dataset.dbkey:
            dataset.dbkey = "hg18"  # punt!
        if dataset.has_data():
            for site_name, site_url in app.datatypes_registry.get_legacy_sites_by_build("ucsc", dataset.dbkey):
                if site_name in app.datatypes_registry.get_display_sites("ucsc"):
                    site_url = site_url.replace("/hgTracks?", "/hgGenome?")  # for genome graphs
                    internal_url = "%s" % app.url_for(
                        controller="dataset", dataset_id=dataset.id, action="display_at", filename=f"ucsc_{site_name}"
                    )
                    display_url = "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at" % (
                        base_url,
                        app.url_for(controller="root"),
                        dataset.id,
                        type,
                    )
                    display_url = quote_plus(display_url)
                    # was display_url = quote_plus( "%s/display_as?id=%i&display_app=%s" % (base_url, dataset.id, type) )
                    # redirect_url = quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" % (site_url, dataset.dbkey, chrom, start, stop) )
                    sl = [
                        f"{site_url}db={dataset.dbkey}",
                    ]
                    # sl.append("&hgt.customText=%s")
                    sl.append(f"&hgGenome_dataSetName={dataset.name}&hgGenome_dataSetDescription=GalaxyGG_data")
                    sl.append("&hgGenome_formatType=best guess&hgGenome_markerType=best guess")
                    sl.append("&hgGenome_columnLabels=first row&hgGenome_maxVal=&hgGenome_labelVals=")
                    sl.append("&hgGenome_doSubmitUpload=submit")
                    sl.append(f"&hgGenome_maxGapToFill=25000000&hgGenome_uploadFile={display_url}")
                    s = "".join(sl)
                    s = quote_plus(s)
                    redirect_url = s
                    link = f"{internal_url}?redirect_url={redirect_url}&display_url={display_url}"
                    ret_val.append((site_name, link))
        return ret_val

    def make_html_table(self, dataset: DatasetProtocol, **kwargs) -> str:
        """
        Create HTML table, used for displaying peek
        """
        try:
            out = ['<table cellspacing="0" cellpadding="3">']
            with open(dataset.file_name) as f:
                d = f.readlines()[:5]
            if len(d) == 0:
                return f"Cannot find anything to parse in {dataset.name}"
            hasheader = 0
            try:
                [f"{x:f}" for x in d[0][1:]]  # first is name - see if starts all numerics
            except Exception:
                hasheader = 1
            # Generate column header
            out.append("<tr>")
            if hasheader:
                for i, name in enumerate(d[0].split()):
                    out.append(f"<th>{i + 1}.{name}</th>")
                d.pop(0)
                out.append("</tr>")
            for row in d:
                out.append("<tr>")
                out.append("".join(f"<td>{x}</td>" for x in row.split()))
                out.append("</tr>")
            out.append("</table>")
            return "".join(out)
        except Exception as exc:
            return f"Can't create peek {exc}"

    def validate(self, dataset: DatasetProtocol, **kwd) -> DatatypeValidation:
        """
        Validate a gg file - all numeric after header row
        """
        with open(dataset.file_name) as infile:
            next(infile)  # header
            for row in infile:
                ll = row.strip().split("\t")[1:]  # first is alpha feature identifier
                for x in ll:
                    float(x)
        return DatatypeValidation.validated()

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Determines whether the file is in gg format

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'test_space.txt' )
        >>> GenomeGraphs().sniff( fname )
        False
        >>> fname = get_test_fname( '1.gg' )
        >>> GenomeGraphs().sniff( fname )
        True
        """
        buf = file_prefix.contents_header
        rows = [line.split() for line in buf.splitlines()[1:4]]  # break on lines and drop header, small sample

        if len(rows) < 1:
            return False

        for row in rows:
            if len(row) < 2:
                # Must actually have a marker and at least one numeric value
                return False
            first_val = row[0]
            if not VALID_GENOME_GRAPH_MARKERS.match(first_val):
                return False
            rest_row = row[1:]
            try:
                [float(x) for x in rest_row]  # first col has been removed
            except ValueError:
                return False
        return True

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "application/vnd.ms-excel"


class rgTabList(Tabular):
    """
    for sampleid and for featureid lists of exclusions or inclusions in the clean tool
    featureid subsets on statistical criteria -> specialized display such as gg
    """

    file_ext = "rgTList"

    def __init__(self, **kwd):
        """
        Initialize featurelistt datatype
        """
        super().__init__(**kwd)
        self.column_names = []

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Returns formated html of peek"""
        return self.make_html_table(dataset, column_names=self.column_names)

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "text/html"


class rgSampleList(rgTabList):
    """
    for sampleid exclusions or inclusions in the clean tool
    output from QC eg excess het, gender error, ibd pair member,eigen outlier,excess mendel errors,...
    since they can be uploaded, should be flexible
    but they are persistent at least
    same infrastructure for expression?
    """

    file_ext = "rgSList"

    def __init__(self, **kwd):
        """
        Initialize samplelist datatype
        """
        super().__init__(**kwd)
        self.column_names[0] = "FID"
        self.column_names[1] = "IID"
        # this is what Plink wants as at 2009


class rgFeatureList(rgTabList):
    """
    for featureid lists of exclusions or inclusions in the clean tool
    output from QC eg low maf, high missingness, bad hwe in controls, excess mendel errors,...
    featureid subsets on statistical criteria -> specialized display such as gg
    same infrastructure for expression?
    """

    file_ext = "rgFList"

    def __init__(self, **kwd):
        """Initialize featurelist datatype"""
        super().__init__(**kwd)
        for i, s in enumerate(["#FeatureId", "Chr", "Genpos", "Mappos"]):
            self.column_names[i] = s


class Rgenetics(Html):
    """
    base class to use for rgenetics datatypes
    derived from html - composite datatype elements
    stored in extra files path
    """

    MetadataElement(
        name="base_name",
        desc="base name for all transformed versions of this genetic dataset",
        default="RgeneticsData",
        readonly=True,
        set_in_upload=True,
    )

    composite_type = "auto_primary_file"
    file_ext = "rgenetics"

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Rgenetics Galaxy Composite Dataset </title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"application/binary\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="application/binary">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)

    def regenerate_primary_file(self, dataset: DatasetProtocol) -> None:
        """
        cannot do this until we are setting metadata
        """
        efp = dataset.extra_files_path
        flist = os.listdir(efp)
        rval = [
            f"<html><head><title>Files for Composite Dataset {dataset.name}</title></head><body><p/>Composite {dataset.name} contains:<p/><ul>"
        ]
        for fname in flist:
            sfname = os.path.split(fname)[-1]
            f, e = os.path.splitext(fname)
            rval.append(f'<li><a href="{sfname}">{sfname}</a></li>')
        rval.append("</ul></body></html>")
        with open(dataset.file_name, "w") as f:
            f.write("\n".join(rval))
            f.write("\n")

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "text/html"

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        for lped/pbed eg

        """
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        if not overwrite:
            if verbose:
                gal_Log.debug("@@@ rgenetics set_meta called with overwrite = False")
            return
        try:
            efp = dataset.extra_files_path
        except Exception:
            if verbose:
                gal_Log.debug(f"@@@rgenetics set_meta failed {sys.exc_info()[0]} - dataset {dataset.name} has no efp ?")
            return
        try:
            flist = os.listdir(efp)
        except Exception:
            if verbose:
                gal_Log.debug(f"@@@rgenetics set_meta failed {sys.exc_info()[0]} - dataset {dataset.name} has no efp ?")
            return
        if len(flist) == 0:
            if verbose:
                gal_Log.debug(f"@@@rgenetics set_meta failed - {dataset.name} efp {efp} is empty?")
            return
        self.regenerate_primary_file(dataset)
        if not dataset.info:
            dataset.info = "Galaxy genotype datatype object"
        if not dataset.blurb:
            dataset.blurb = "Composite file - Rgenetics Galaxy toolkit"


class SNPMatrix(Rgenetics):
    """
    BioC SNPMatrix Rgenetics data collections
    """

    file_ext = "snpmatrix"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "Binary RGenetics file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename: str) -> bool:
        """need to check the file header hex code"""
        with open(filename, "b") as infile:
            head = infile.read(16)
        head = [hex(x) for x in head]
        if head != "":
            return False
        else:
            return True


class Lped(Rgenetics):
    """
    linkage pedigree (ped,map) Rgenetics data collections
    """

    file_ext = "lped"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.ped", description="Pedigree File", substitute_name_with_metadata="base_name", is_binary=False
        )
        self.add_composite_file(
            "%s.map", description="Map File", substitute_name_with_metadata="base_name", is_binary=False
        )


class Pphe(Rgenetics):
    """
    Plink phenotype file - header must have FID\tIID... Rgenetics data collections
    """

    file_ext = "pphe"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.pphe", description="Plink Phenotype File", substitute_name_with_metadata="base_name", is_binary=False
        )


class Fphe(Rgenetics):
    """
    fbat pedigree file - mad format with ! as first char on header row
    Rgenetics data collections
    """

    file_ext = "fphe"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("%s.fphe", description="FBAT Phenotype File", substitute_name_with_metadata="base_name")


class Phe(Rgenetics):
    """
    Phenotype file
    """

    file_ext = "phe"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.phe", description="Phenotype File", substitute_name_with_metadata="base_name", is_binary=False
        )


class Fped(Rgenetics):
    """
    FBAT pedigree format - single file, map is header row of rs numbers. Strange.
    Rgenetics data collections
    """

    file_ext = "fped"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.fped", description="FBAT format pedfile", substitute_name_with_metadata="base_name", is_binary=False
        )


class Pbed(Rgenetics):
    """
    Plink Binary compressed 2bit/geno Rgenetics data collections
    """

    file_ext = "pbed"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("%s.bim", substitute_name_with_metadata="base_name", is_binary=False)
        self.add_composite_file("%s.bed", substitute_name_with_metadata="base_name", is_binary=True)
        self.add_composite_file("%s.fam", substitute_name_with_metadata="base_name", is_binary=False)


class ldIndep(Rgenetics):
    """
    LD (a good measure of redundancy of information) depleted Plink Binary compressed 2bit/geno
    This is really a plink binary, but some tools work better with less redundancy so are constrained to
    these files
    """

    file_ext = "ldreduced"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("%s.bim", substitute_name_with_metadata="base_name", is_binary=False)
        self.add_composite_file("%s.bed", substitute_name_with_metadata="base_name", is_binary=True)
        self.add_composite_file("%s.fam", substitute_name_with_metadata="base_name", is_binary=False)


class Eigenstratgeno(Rgenetics):
    """
    Eigenstrat format - may be able to get rid of this
    if we move to shellfish
    Rgenetics data collections
    """

    file_ext = "eigenstratgeno"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("%s.eigenstratgeno", substitute_name_with_metadata="base_name", is_binary=False)
        self.add_composite_file("%s.ind", substitute_name_with_metadata="base_name", is_binary=False)
        self.add_composite_file("%s.map", substitute_name_with_metadata="base_name", is_binary=False)


class Eigenstratpca(Rgenetics):
    """
    Eigenstrat PCA file for case control adjustment
    Rgenetics data collections
    """

    file_ext = "eigenstratpca"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.eigenstratpca", description="Eigenstrat PCA file", substitute_name_with_metadata="base_name"
        )


class Snptest(Rgenetics):
    """
    BioC snptest Rgenetics data collections
    """

    file_ext = "snptest"


class IdeasPre(Html):
    """
    This datatype defines the input format required by IDEAS:
    https://academic.oup.com/nar/article/44/14/6721/2468150
    The IDEAS preprocessor tool produces an output using this
    format.  The extra_files_path of the primary input dataset
    contains the following files and directories.
    - chromosome_windows.txt (optional)
    - chromosomes.bed (optional)
    - IDEAS_input_config.txt
    - compressed archived tmp directory containing a number of compressed bed files.
    """

    MetadataElement(
        name="base_name", desc="Base name for this dataset", default="IDEASData", readonly=True, set_in_upload=True
    )
    MetadataElement(name="chrom_bed", desc="Bed file specifying window positions", default=None, readonly=True)
    MetadataElement(name="chrom_windows", desc="Chromosome window positions", default=None, readonly=True)
    MetadataElement(name="input_config", desc="IDEAS input config", default=None, readonly=True)
    MetadataElement(name="tmp_archive", desc="Compressed archive of compressed bed files", default=None, readonly=True)

    composite_type = "auto_primary_file"
    file_ext = "ideaspre"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "chromosome_windows.txt", description="Chromosome window positions", is_binary=False, optional=True
        )
        self.add_composite_file(
            "chromosomes.bed", description="Bed file specifying window positions", is_binary=False, optional=True
        )
        self.add_composite_file("IDEAS_input_config.txt", description="IDEAS input config", is_binary=False)
        self.add_composite_file("tmp.tar.gz", description="Compressed archive of compressed bed files", is_binary=True)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        for fname in os.listdir(dataset.extra_files_path):
            if fname.startswith("chromosomes"):
                dataset.metadata.chrom_bed = os.path.join(dataset.extra_files_path, fname)
            elif fname.startswith("chromosome_windows"):
                dataset.metadata.chrom_windows = os.path.join(dataset.extra_files_path, fname)
            elif fname.startswith("IDEAS_input_config"):
                dataset.metadata.input_config = os.path.join(dataset.extra_files_path, fname)
            elif fname.startswith("tmp"):
                dataset.metadata.tmp_archive = os.path.join(dataset.extra_files_path, fname)
        self.regenerate_primary_file(dataset)

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head></head><body>"]
        rval.append("<h3>Files prepared for IDEAS</h3>")
        rval.append("<ul>")
        for composite_name in self.get_composite_files(dataset=dataset).keys():
            fn = composite_name
            rval.append(f'<li><a href="{fn}>{fn}</a></li>')
        rval.append("</ul></body></html>\n")
        return "\n".join(rval)

    def regenerate_primary_file(self, dataset: DatasetProtocol) -> None:
        # Cannot do this until we are setting metadata.
        rval = ["<html><head></head><body>"]
        rval.append("<h3>Files prepared for IDEAS</h3>")
        rval.append("<ul>")
        for fname in os.listdir(dataset.extra_files_path):
            fn = os.path.split(fname)[-1]
            rval.append(f'<li><a href="{fn}">{fn}</a></li>')
        rval.append("</ul></body></html>")
        with open(dataset.file_name, "w") as f:
            f.write("\n".join(rval))
            f.write("\n")


class Pheno(Tabular):
    """
    base class for pheno files
    """

    file_ext = "pheno"


class RexpBase(Html):
    """
    base class for BioC data structures in Galaxy
    must be constructed with the pheno data in place since that
    goes into the metadata for each instance
    """

    MetadataElement(name="columns", default=0, desc="Number of columns", visible=True)
    MetadataElement(name="column_names", default=[], desc="Column names", visible=True)
    MetadataElement(name="pheCols", default=[], desc="Select list for potentially interesting variables", visible=True)
    MetadataElement(
        name="base_name",
        desc="base name for all transformed versions of this expression dataset",
        default="rexpression",
        set_in_upload=True,
    )
    MetadataElement(
        name="pheno_path", desc="Path to phenotype data for this experiment", default="rexpression.pheno", visible=True
    )
    file_ext = "rexpbase"
    html_table = None
    composite_type = "auto_primary_file"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.pheno",
            description="Phenodata tab text file",
            substitute_name_with_metadata="base_name",
            is_binary=False,
        )

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        return "<html><head></head><body>AutoGenerated Primary File for Composite Dataset</body></html>"

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "text/html"

    def get_phecols(self, phenolist: List, maxConc: int = 20) -> List:
        """
        sept 2009: cannot use whitespace to split - make a more complex structure here
        and adjust the methods that rely on this structure
        return interesting phenotype column names for an rexpression eset or affybatch
        to use in array subsetting and so on. Returns a data structure for a
        dynamic Galaxy select parameter.
        A column with only 1 value doesn't change, so is not interesting for
        analysis. A column with a different value in every row is equivalent to a unique
        identifier so is also not interesting for anova or limma analysis - both these
        are removed after the concordance (count of unique terms) is constructed for each
        column. Then a complication - each remaining pair of columns is tested for
        redundancy - if two columns are always paired, then only one is needed :)
        """
        for nrows, row in enumerate(phenolist):  # construct concordance
            if len(row.strip()) == 0:
                break
            row = row.strip().split("\t")
            if nrows == 0:  # set up from header
                head = row
                totcols = len(row)
                concordance: List[Dict] = [{} for x in head]
            else:
                for col, code in enumerate(row):  # keep column order correct
                    if col >= totcols:
                        gal_Log.warning(
                            "### get_phecols error in pheno file - row %d col %d (%s) longer than header %s"
                            % (nrows, col, row, head)
                        )
                    else:
                        concordance[col].setdefault(code, 0)  # first one is zero
                        concordance[col][code] += 1
        useCols = []
        useConc = []  # columns of interest to keep
        nrows = len(phenolist)
        nrows -= 1  # drop head from count
        for c, conc in enumerate(concordance):  # c is column number
            if (len(conc) > 1) and (len(conc) < min(nrows, maxConc)):  # not all same and not all different!!
                useConc.append(conc)  # keep concordance
                useCols.append(c)  # keep column
        nuse = len(useCols)
        # now to check for pairs of concordant columns - drop one of these.
        delme = []
        p = phenolist[1:]  # drop header
        plist = [x.strip().split("\t") for x in p]  # list of lists
        phe = [[x[i] for i in useCols] for x in plist if len(x) >= totcols]  # strip unused data
        for i in range(0, (nuse - 1)):  # for each interesting column
            for j in range(i + 1, nuse):
                kdict = {}
                for row in phe:  # row is a list of lists
                    k = f"{row[i]}{row[j]}"  # composite key
                    kdict[k] = k
                if len(kdict.keys()) == len(concordance[useCols[j]]):  # i and j are always matched
                    delme.append(j)
        delme = list(set(delme))  # remove dupes
        listCol = []
        delme.sort()
        delme.reverse()  # must delete from far end!
        for i in delme:
            del useConc[i]  # get rid of concordance
            del useCols[i]  # and usecols entry
        for i, conc in enumerate(useConc):  # these are all unique columns for the design matrix
            ccounts = sorted((conc.get(code, 0), code) for code in conc.keys())  # decorate
            cc = [(x[1], x[0]) for x in ccounts]  # list of code count tuples
            codeDetails = (head[useCols[i]], cc)  # ('foo',[('a',3),('b',11),..])
            listCol.append(codeDetails)
        if len(listCol) > 0:
            res = listCol
            # metadata.pheCols becomes [('bar;22,zot;113','foo'), ...]
        else:
            res = [
                (
                    "no usable phenotype columns found",
                    [
                        ("?", 0),
                    ],
                ),
            ]
        return res

    def get_pheno(self, dataset):
        """
        expects a .pheno file in the extra_files_dir - ugh
        note that R is wierd and adds the row.name in
        the header so the columns are all wrong - unless you tell it not to.
        A file can be written as
        write.table(file='foo.pheno',pData(foo),sep='\t',quote=F,row.names=F)
        """
        p = open(dataset.metadata.pheno_path).readlines()
        if len(p) > 0:  # should only need to fix an R pheno file once
            head = p[0].strip().split("\t")
            line1 = p[1].strip().split("\t")
            if len(head) < len(line1):
                head.insert(0, "ChipFileName")  # fix R write.table b0rken-ness
                p[0] = "\t".join(head)
        else:
            p = []
        return "\n".join(p)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """
        expects a .pheno file in the extra_files_dir - ugh
        note that R is weird and does not include the row.name in
        the header. why?"""
        if not dataset.dataset.purged:
            pp = os.path.join(dataset.extra_files_path, f"{dataset.metadata.base_name}.pheno")
            try:
                with open(pp) as f:
                    p = f.readlines()
            except Exception:
                p = [
                    f"##failed to find {pp}",
                ]
            dataset.peek = "".join(p[:5])
            dataset.blurb = "Galaxy Rexpression composite file"
        else:
            dataset.peek = "file does not exist\n"
            dataset.blurb = "file purged from disk"

    def get_peek(self, dataset):
        """
        expects a .pheno file in the extra_files_dir - ugh
        """
        pp = os.path.join(dataset.extra_files_path, f"{dataset.metadata.base_name}.pheno")
        try:
            with open(pp) as f:
                p = f.readlines()
        except Exception:
            p = [f"##failed to find {pp}"]
        return "".join(p[:5])

    def get_file_peek(self, filename: str) -> str:
        """
        Read and return the first `max_lines`.
        (Can't really peek at a filename - need the extra_files_path and such?)
        """
        max_lines = 5
        try:
            with open(filename) as f:
                lines = []
                for line in f:
                    lines.append(line)
                    if len(lines) == max_lines:
                        break
                return "".join(lines)
        except Exception:
            return "## rexpression get_file_peek: no file found"

    def regenerate_primary_file(self, dataset: DatasetProtocol) -> None:
        """
        cannot do this until we are setting metadata
        """
        bn = dataset.metadata.base_name
        flist = os.listdir(dataset.extra_files_path)
        rval = [
            f"<html><head><title>Files for Composite Dataset {bn}</title></head><p/>Comprises the following files:<p/><ul>"
        ]
        for fname in flist:
            sfname = os.path.split(fname)[-1]
            rval.append(f'<li><a href="{sfname}">{sfname}</a>')
        rval.append("</ul></html>")
        with open(dataset.file_name, "w") as f:
            f.write("\n".join(rval))
            f.write("\n")

    def init_meta(self, dataset: HasMetadata, copy_from: Optional[HasMetadata] = None) -> None:
        if copy_from:
            dataset.metadata = copy_from.metadata

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        NOTE we apply the tabular machinary to the phenodata extracted
        from a BioC eSet or affybatch.

        """
        super().set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            flist = os.listdir(dataset.extra_files_path)
        except Exception:
            if verbose:
                gal_Log.debug("@@@rexpression set_meta failed - no dataset?")
            return
        bn = dataset.metadata.base_name
        if not bn:
            for f in flist:
                n = os.path.splitext(f)[0]
                bn = n
                dataset.metadata.base_name = bn
        if not bn:
            bn = "?"
            dataset.metadata.base_name = bn
        pn = f"{bn}.pheno"
        pp = os.path.join(dataset.extra_files_path, pn)
        dataset.metadata.pheno_path = pp
        try:
            with open(pp) as f:
                pf = f.readlines()  # read the basename.phenodata in the extra_files_path
        except Exception:
            pf = None
        if pf:
            h = pf[0].strip()
            h = h.split("\t")  # hope is header
            h = [escape(x) for x in h]
            dataset.metadata.column_names = h
            dataset.metadata.columns = len(h)
            dataset.peek = "".join(pf[:5])
        else:
            dataset.metadata.column_names = []
            dataset.metadata.columns = 0
            dataset.peek = "No pheno file found"
        if pf and len(pf) > 1:
            dataset.metadata.pheCols = self.get_phecols(phenolist=pf)
        else:
            dataset.metadata.pheCols = [
                ("", "No useable phenotypes found", False),
            ]
        if not dataset.info:
            dataset.info = "Galaxy Expression datatype object"
        if not dataset.blurb:
            dataset.blurb = "R loadable BioC expression object for the Rexpression Galaxy toolkit"

    def make_html_table(self, pp: str = "nothing supplied from peek\n") -> str:
        """
        Create HTML table, used for displaying peek
        """
        try:
            out = ['<table cellspacing="0" cellpadding="3">']
            # Generate column header
            p = pp.split("\n")
            for i, row in enumerate(p):
                lrow = row.strip().split("\t")
                if i == 0:
                    orow = [f"<th>{escape(x)}</th>" for x in lrow]
                    orow.insert(0, "<tr>")
                    orow.append("</tr>")
                else:
                    orow = [f"<td>{escape(x)}</td>" for x in lrow]
                    orow.insert(0, "<tr>")
                    orow.append("</tr>")
                out.append("".join(orow))
            out.append("</table>")
            return "\n".join(out)
        except Exception as exc:
            return f"Can't create html table {unicodify(exc)}"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """
        Returns formatted html of peek
        """
        out = self.make_html_table(dataset.peek)
        return out


class Affybatch(RexpBase):
    """
    derived class for BioC data structures in Galaxy
    """

    file_ext = "affybatch"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.affybatch",
            description="AffyBatch R object saved to file",
            substitute_name_with_metadata="base_name",
            is_binary=True,
        )


class Eset(RexpBase):
    """
    derived class for BioC data structures in Galaxy
    """

    file_ext = "eset"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.eset",
            description="ESet R object saved to file",
            substitute_name_with_metadata="base_name",
            is_binary=True,
        )


class MAlist(RexpBase):
    """
    derived class for BioC data structures in Galaxy
    """

    file_ext = "malist"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file(
            "%s.malist",
            description="MAlist R object saved to file",
            substitute_name_with_metadata="base_name",
            is_binary=True,
        )


class LinkageStudies(Text):
    """
    superclass for classical linkage analysis suites
    """

    test_files = [
        "linkstudies.allegro_fparam",
        "linkstudies.alohomora_gts",
        "linkstudies.linkage_datain",
        "linkstudies.linkage_map",
    ]

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.max_lines = 10


@build_sniff_from_prefix
class GenotypeMatrix(LinkageStudies):
    """
    Sample matrix of genotypes
    - GTs as columns
    """

    file_ext = "alohomora_gts"

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def header_check(self, fio: IO) -> bool:
        header_elems = fio.readline().split("\t")

        if header_elems[0] != "Name":
            return False

        try:
            return all(int(sid) > 0 for sid in header_elems[1:])
        except ValueError:
            return False

        return True

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> classname = GenotypeMatrix
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> extn_true = classname().file_ext
        >>> file_true = get_test_fname("linkstudies." + extn_true)
        >>> classname().sniff(file_true)
        True
        >>> false_files = list(LinkageStudies.test_files)
        >>> false_files.remove("linkstudies." + extn_true)
        >>> result_true = []
        >>> for fname in false_files:
        ...     file_false = get_test_fname(fname)
        ...     res = classname().sniff(file_false)
        ...     if res:
        ...         result_true.append(fname)
        >>>
        >>> result_true
        []
        """
        fio = file_prefix.string_io()
        num_cols = -1

        if not self.header_check(fio):
            return False

        for lcount, line in enumerate(fio):
            if lcount > self.max_lines:
                return True

            tokens = line.split("\t")

            if num_cols == -1:
                num_cols = len(tokens)
            elif num_cols != len(tokens):
                return False
            if not VALID_GENOTYPES_LINE.match(line):
                return False

        return True


@build_sniff_from_prefix
class MarkerMap(LinkageStudies):
    """
    Map of genetic markers including physical and genetic distance
    Common input format for linkage programs

    chrom, genetic pos, markername, physical pos, Nr
    """

    file_ext = "linkage_map"

    def header_check(self, fio: IO) -> bool:
        headers = fio.readline().split()

        if len(headers) == 5 and headers[0] == "#Chr":
            return True

        return False

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> classname = MarkerMap
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> extn_true = classname().file_ext
        >>> file_true = get_test_fname("linkstudies." + extn_true)
        >>> classname().sniff(file_true)
        True
        >>> false_files = list(LinkageStudies.test_files)
        >>> false_files.remove("linkstudies." + extn_true)
        >>> result_true = []
        >>> for fname in false_files:
        ...     file_false = get_test_fname(fname)
        ...     res = classname().sniff(file_false)
        ...     if res:
        ...         result_true.append(fname)
        >>>
        >>> result_true
        []
        """
        fio = file_prefix.string_io()
        if not self.header_check(fio):
            return False

        for lcount, line in enumerate(fio):
            if lcount > self.max_lines:
                return True

            try:
                chrm, gpos, nam, bpos, row = line.split()
                float(gpos)
                int(bpos)

                try:
                    int(chrm)
                except ValueError:
                    if chrm.lower()[0] not in ("x", "y", "m"):
                        return False

            except ValueError:
                return False

        return True


@build_sniff_from_prefix
class DataIn(LinkageStudies):
    """
    Common linkage input file for intermarker distances
    and recombination rates
    """

    file_ext = "linkage_datain"

    def __init__(self, **kwd):
        super().__init__(**kwd)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> classname = DataIn
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> extn_true = classname().file_ext
        >>> file_true = get_test_fname("linkstudies." + extn_true)
        >>> classname().sniff(file_true)
        True
        >>> false_files = list(LinkageStudies.test_files)
        >>> false_files.remove("linkstudies." + extn_true)
        >>> result_true = []
        >>> for fname in false_files:
        ...     file_false = get_test_fname(fname)
        ...     res = classname().sniff(file_false)
        ...     if res:
        ...         result_true.append(fname)
        >>>
        >>> result_true
        []
        """
        intermarkers = 0
        num_markers = None

        def eof_function():
            return intermarkers > 0

        fio = file_prefix.string_io()
        for lcount, line in enumerate(fio):
            if lcount > self.max_lines:
                return eof_function()

            tokens = line.split()
            try:
                if lcount == 0:
                    num_markers = int(tokens[0])
                    map(int, tokens[1:])
                elif lcount == 1:
                    map(float, tokens)

                    if len(tokens) != 4:
                        return False
                elif lcount == 2:
                    map(int, tokens)
                    last_token = int(tokens[-1])

                    if num_markers is None:
                        return False
                    if len(tokens) != last_token:
                        return False
                    if num_markers != last_token:
                        return False
                elif tokens[0] == "3" and tokens[1] == "2":
                    intermarkers += 1

            except (ValueError, IndexError):
                return False

        return eof_function()


@build_sniff_from_prefix
class AllegroLOD(LinkageStudies):
    """
    Allegro output format for LOD scores
    """

    file_ext = "allegro_fparam"

    def header_check(self, fio: IO) -> bool:
        header = fio.readline().splitlines()[0].split()
        if len(header) == 4 and header == ["family", "location", "LOD", "marker"]:
            return True

        return False

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        >>> classname = AllegroLOD
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> extn_true = classname().file_ext
        >>> file_true = get_test_fname("linkstudies." + extn_true)
        >>> classname().sniff(file_true)
        True
        >>> false_files = list(LinkageStudies.test_files)
        >>> false_files.remove("linkstudies." + extn_true)
        >>> result_true = []
        >>> for fname in false_files:
        ...     file_false = get_test_fname(fname)
        ...     res = classname().sniff(file_false)
        ...     if res:
        ...         result_true.append(fname)
        >>>
        >>> result_true
        []
        """
        fio = file_prefix.string_io()

        if not self.header_check(fio):
            return False

        for lcount, line in enumerate(fio):
            if lcount > self.max_lines:
                return True

            tokens = line.split()

            try:
                int(tokens[0])
                float(tokens[1])

                if tokens[2] != "-inf":
                    float(tokens[2])

            except (ValueError, IndexError):
                return False

        return True
