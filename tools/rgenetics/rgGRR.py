"""
# july 2009: Need to see outliers so need to draw them last?
# could use clustering on the zscores to guess real relationships for unrelateds
# but definitely need to draw last
# added MAX_SHOW_ROWS to limit the length of the main report page
# Changes for Galaxy integration
# added more robust knuth method for one pass mean and sd
# no difference really - let's use scipy.mean() and scipy.std() instead...
# fixed labels and changed to .xls for outlier reports so can open in excel
# interesting - with a few hundred subjects, 5k gives good resolution
# and 100k gives better but not by much
# TODO remove non autosomal markers
# TODO it would be best if label had the zmean and zsd as these are what matter for
# outliers rather than the group mean/sd
# mods to rgGRR.py from channing CVS which John Ziniti has rewritten to produce SVG plots
# to make a Galaxy tool - we need the table of mean and SD for interesting pairs, the SVG and the log
# so the result should be an HTML file

# rgIBS.py
# use a random subset of markers for a quick ibs
# to identify sample dups and closely related subjects
# try snpMatrix and plink and see which one works best for us?
# abecasis grr plots mean*sd for every subject to show clusters
# mods june 23 rml to avoid non-autosomal markers
# we seem to be distinguishing parent-child by gender - 2 clouds!


snpMatrix from David Clayton has:
ibs.stats function to calculate the identity-by-state stats of a group of samples
Description
Given a snp.matrix-class or a X.snp.matrix-class object with N samples, calculates some statistics
about the relatedness of every pair of samples within.

Usage
ibs.stats(x)
8 ibs.stats
Arguments
x a snp.matrix-class or a X.snp.matrix-class object containing N samples
Details
No-calls are excluded from consideration here.
Value
A data.frame containing N(N - 1)/2 rows, where the row names are the sample name pairs separated
by a comma, and the columns are:
Count count of identical calls, exclusing no-calls
Fraction fraction of identical calls comparied to actual calls being made in both samples
Warning
In some applications, it may be preferable to subset a (random) selection of SNPs first - the
calculation
time increases as N(N - 1)M/2 . Typically for N = 800 samples and M = 3000 SNPs, the
calculation time is about 1 minute. A full GWA scan could take hours, and quite unnecessary for
simple applications such as checking for duplicate or related samples.
Note
This is mostly written to find mislabelled and/or duplicate samples.
Illumina indexes their SNPs in alphabetical order so the mitochondria SNPs comes first - for most
purpose it is undesirable to use these SNPs for IBS purposes.
TODO: Worst-case S4 subsetting seems to make 2 copies of a large object, so one might want to
subset before rbind(), etc; a future version of this routine may contain a built-in subsetting facility
"""
import sys,os,time,random,string,copy,optparse

try:
  set
except NameError:
  from Sets import Set as set

from rgutils import timenow,plinke

import plinkbinJZ


opts = None
verbose = False

showPolygons = False

class NullDevice:
  def write(self, s):
    pass

tempstderr = sys.stderr # save
#sys.stderr = NullDevice()
# need to avoid blather about deprecation and other strange stuff from scipy
# the current galaxy job runner assumes that
# the job is in error if anything appears on sys.stderr
# grrrrr. James wants to keep it that way instead of using the
# status flag for some strange reason. Presumably he doesn't use R or (in this case, scipy)
import numpy
import scipy
from scipy import weave


sys.stderr=tempstderr


PROGNAME = os.path.split(sys.argv[0])[-1]
X_AXIS_LABEL = 'Mean Alleles Shared'
Y_AXIS_LABEL = 'SD Alleles Shared'
LEGEND_ALIGN = 'topleft'
LEGEND_TITLE = 'Relationship'
DEFAULT_SYMBOL_SIZE = 1.0 # default symbol size
DEFAULT_SYMBOL_SIZE = 0.5 # default symbol size

### Some colors for R/rpy
R_BLACK  = 1
R_RED    = 2
R_GREEN  = 3
R_BLUE   = 4
R_CYAN   = 5
R_PURPLE = 6
R_YELLOW = 7
R_GRAY   = 8

### ... and some point-styles

###
PLOT_HEIGHT = 600
PLOT_WIDTH = 1150


#SVG_COLORS = ('black', 'darkblue', 'blue', 'deepskyblue', 'firebrick','maroon','crimson')
#SVG_COLORS = ('cyan','dodgerblue','mediumpurple', 'fuchsia', 'red','gold','gray')
SVG_COLORS = ('cyan','dodgerblue','mediumpurple','forestgreen', 'lightgreen','gold','gray')
# dupe,parentchild,sibpair,halfsib,parents,unrel,unkn
#('orange', 'red', 'green', 'chartreuse', 'blue', 'purple', 'gray')

OUTLIERS_HEADER_list = ['Mean','Sdev','ZMean','ZSdev','FID1','IID1','FID2','IID2','RelMean_M','RelMean_SD','RelSD_M','RelSD_SD','PID1','MID1','PID2','MID2','Ped']
OUTLIERS_HEADER = '\t'.join(OUTLIERS_HEADER_list)
TABLE_HEADER='fid1_iid1\tfid2_iid2\tmean\tsdev\tzmean\tzsdev\tgeno\trelcode\tpid1\tmid1\tpid2\tmid2\n'


### Relationship codes, text, and lookups/mappings
N_RELATIONSHIP_TYPES = 7
REL_DUPE, REL_PARENTCHILD, REL_SIBS, REL_HALFSIBS, REL_RELATED, REL_UNRELATED, REL_UNKNOWN = range(N_RELATIONSHIP_TYPES)
REL_LOOKUP = {
    REL_DUPE:        ('dupe',        R_BLUE,   1),
    REL_PARENTCHILD: ('parentchild', R_YELLOW, 1),
    REL_SIBS:        ('sibpairs',    R_RED,    1),
    REL_HALFSIBS:    ('halfsibs',    R_GREEN,  1),
    REL_RELATED:     ('parents',     R_PURPLE, 1),
    REL_UNRELATED:   ('unrelated',   R_CYAN,   1),
    REL_UNKNOWN:     ('unknown',     R_GRAY,   1),
    }
OUTLIER_STDEVS = {
    REL_DUPE:        2,
    REL_PARENTCHILD: 2,
    REL_SIBS:        2,
    REL_HALFSIBS:    2,
    REL_RELATED:     2,
    REL_UNRELATED:   3,
    REL_UNKNOWN:     2,
    }
# note now Z can be passed in

REL_STATES = [REL_LOOKUP[r][0] for r in range(N_RELATIONSHIP_TYPES)]
REL_COLORS = SVG_COLORS
REL_POINTS = [REL_LOOKUP[r][2] for r in range(N_RELATIONSHIP_TYPES)]

DEFAULT_MAX_SAMPLE_SIZE = 10000

REF_COUNT_HOM1 = 3
REF_COUNT_HET  = 2
REF_COUNT_HOM2 = 1
MISSING        = 0
MAX_SHOW_ROWS = 100 # framingham has millions - delays showing output page - so truncate and explain
MARKER_PAIRS_PER_SECOND_SLOW = 15000000.0
MARKER_PAIRS_PER_SECOND_FAST = 70000000.0


galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""


SVG_HEADER = '''<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.2//EN" "http://www.w3.org/Graphics/SVG/1.2/DTD/svg12.dtd">

<svg width="1280" height="800"
     xmlns="http://www.w3.org/2000/svg" version="1.2"
     xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1280 800" onload="init()">

  <script type="text/ecmascript" xlink:href="/static/scripts/checkbox_and_radiobutton.js"/>
  <script type="text/ecmascript" xlink:href="/static/scripts/helper_functions.js"/>
  <script type="text/ecmascript" xlink:href="/static/scripts/timer.js"/>
  <script type="text/ecmascript">
    <![CDATA[
      var checkBoxes = new Array();
      var radioGroupBandwidth;
      var colours = ['%s','%s','%s','%s','%s','%s','%s'];
      function init() {
          var style = {"font-family":"Arial,Helvetica", "fill":"black", "font-size":12};
          var dist = 12;
          var yOffset = 4;

          //A checkBox for each relationship type dupe,parentchild,sibpair,halfsib,parents,unrel,unkn
          checkBoxes["dupe"] = new checkBox("dupe","checkboxes",20,40,"cbRect","cbCross",true,"Duplicate",style,dist,yOffset,undefined,hideShowLayer);
          checkBoxes["parentchild"] = new checkBox("parentchild","checkboxes",20,60,"cbRect","cbCross",true,"Parent-Child",style,dist,yOffset,undefined,hideShowLayer);
          checkBoxes["sibpairs"] = new checkBox("sibpairs","checkboxes",20,80,"cbRect","cbCross",true,"Sib-pairs",style,dist,yOffset,undefined,hideShowLayer);
          checkBoxes["halfsibs"] = new checkBox("halfsibs","checkboxes",20,100,"cbRect","cbCross",true,"Half-sibs",style,dist,yOffset,undefined,hideShowLayer);
          checkBoxes["parents"] = new checkBox("parents","checkboxes",20,120,"cbRect","cbCross",true,"Parents",style,dist,yOffset,undefined,hideShowLayer);
          checkBoxes["unrelated"] = new checkBox("unrelated","checkboxes",20,140,"cbRect","cbCross",true,"Unrelated",style,dist,yOffset,undefined,hideShowLayer);
          checkBoxes["unknown"] = new checkBox("unknown","checkboxes",20,160,"cbRect","cbCross",true,"Unknown",style,dist,yOffset,undefined,hideShowLayer);

      }

      function hideShowLayer(id, status, label) {
          var vis = "hidden";
          if (status) {
              vis = "visible";
          }
          document.getElementById(id).setAttributeNS(null, 'visibility', vis);
      }

      function showBTT(evt, rel, mm, dm, md, dd, n, mg, dg, lg, hg) {
    var x = parseInt(evt.pageX)-250;
    var y = parseInt(evt.pageY)-110;
        switch(rel) {
        case 0:
        fill = colours[rel];
        relt = "dupe";
        break;
        case 1:
        fill = colours[rel];
        relt = "parentchild";
        break;
        case 2:
        fill = colours[rel];
        relt = "sibpairs";
        break;
        case 3:
        fill = colours[rel];
        relt = "halfsibs";
        break;
        case 4:
        fill = colours[rel];
        relt = "parents";
        break;
        case 5:
        fill = colours[rel];
        relt = "unrelated";
        break;
        case 6:
        fill = colours[rel];
        relt = "unknown";
        break;
        default:
        fill = "cyan";
        relt = "ERROR_CODE: "+rel;
    }

    document.getElementById("btRel").textContent = "GROUP: "+relt;
    document.getElementById("btMean").textContent = "mean="+mm+" +/- "+dm;
        document.getElementById("btSdev").textContent = "sdev="+dm+" +/- "+dd;
        document.getElementById("btPair").textContent = "npairs="+n;
        document.getElementById("btGeno").textContent = "ngenos="+mg+" +/- "+dg+" (min="+lg+", max="+hg+")";
        document.getElementById("btHead").setAttribute('fill', fill);

        var tt = document.getElementById("btTip");
    tt.setAttribute("transform", "translate("+x+","+y+")");
    tt.setAttribute('visibility', 'visible');
      }

      function showOTT(evt, rel, s1, s2, mean, sdev, ngeno, rmean, rsdev) {
    var x = parseInt(evt.pageX)-150;
    var y = parseInt(evt.pageY)-180;

        switch(rel) {
        case 0:
        fill = colours[rel];
        relt = "dupe";
        break;
        case 1:
        fill = colours[rel];
        relt = "parentchild";
        break;
        case 2:
        fill = colours[rel];
        relt = "sibpairs";
        break;
        case 3:
        fill = colours[rel];
        relt = "halfsibs";
        break;
        case 4:
        fill = colours[rel];
        relt = "parents";
        break;
        case 5:
        fill = colours[rel];
        relt = "unrelated";
        break;
        case 6:
        fill = colours[rel];
        relt = "unknown";
        break;
        default:
        fill = "cyan";
        relt = "ERROR_CODE: "+rel;
    }

    document.getElementById("otRel").textContent = "PAIR: "+relt;
    document.getElementById("otS1").textContent = "s1="+s1;
    document.getElementById("otS2").textContent = "s2="+s2;
    document.getElementById("otMean").textContent = "mean="+mean;
        document.getElementById("otSdev").textContent = "sdev="+sdev;
        document.getElementById("otGeno").textContent = "ngenos="+ngeno;
        document.getElementById("otRmean").textContent = "relmean="+rmean;
        document.getElementById("otRsdev").textContent = "relsdev="+rsdev;
    document.getElementById("otHead").setAttribute('fill', fill);

        var tt = document.getElementById("otTip");
    tt.setAttribute("transform", "translate("+x+","+y+")");
    tt.setAttribute('visibility', 'visible');
      }

      function hideBTT(evt) {
        document.getElementById("btTip").setAttributeNS(null, 'visibility', 'hidden');
      }

      function hideOTT(evt) {
        document.getElementById("otTip").setAttributeNS(null, 'visibility', 'hidden');
      }

     ]]>
  </script>
  <defs>
    <!-- symbols for check boxes -->
    <symbol id="cbRect" overflow="visible">
        <rect x="-5" y="-5" width="10" height="10" fill="white" stroke="dimgray" stroke-width="1" cursor="pointer"/>
    </symbol>
    <symbol id="cbCross" overflow="visible">
        <g pointer-events="none" stroke="black" stroke-width="1">
            <line x1="-3" y1="-3" x2="3" y2="3"/>
            <line x1="3" y1="-3" x2="-3" y2="3"/>
        </g>
    </symbol>
  </defs>

<desc>Developer Works Dynamic Scatter Graph Scaling Example</desc>

<!-- Now Draw the main X and Y axis -->
<g style="stroke-width:1.0; stroke:black; shape-rendering:crispEdges">
   <!-- X Axis top and bottom -->
   <path d="M 100 100 L 1250 100 Z"/>
   <path d="M 100 700 L 1250 700 Z"/>

   <!-- Y Axis left and right -->
   <path d="M 100  100 L 100  700 Z"/>
   <path d="M 1250 100 L 1250 700 Z"/>
</g>

<g transform="translate(100,100)">

  <!-- Grid Lines -->
  <g style="fill:none; stroke:#dddddd; stroke-width:1; stroke-dasharray:2,2; text-anchor:end; shape-rendering:crispEdges">

    <!-- Vertical grid lines -->
    <line x1="125" y1="0" x2="115" y2="600" />
    <line x1="230" y1="0" x2="230" y2="600" />
    <line x1="345" y1="0" x2="345" y2="600" />
    <line x1="460" y1="0" x2="460" y2="600" />
    <line x1="575" y1="0" x2="575" y2="600" style="stroke-dasharray:none;" />
    <line x1="690" y1="0" x2="690" y2="600"   />
    <line x1="805" y1="0" x2="805" y2="600"   />
    <line x1="920" y1="0" x2="920" y2="600"   />
    <line x1="1035" y1="0" x2="1035" y2="600" />

    <!-- Horizontal grid lines -->
    <line x1="0" y1="60" x2="1150" y2="60"   />
    <line x1="0" y1="120" x2="1150" y2="120" />
    <line x1="0" y1="180" x2="1150" y2="180" />
    <line x1="0" y1="240" x2="1150" y2="240" />
    <line x1="0" y1="300" x2="1150" y2="300" style="stroke-dasharray:none;" />
    <line x1="0" y1="360" x2="1150" y2="360" />
    <line x1="0" y1="420" x2="1150" y2="420" />
    <line x1="0" y1="480" x2="1150" y2="480" />
    <line x1="0" y1="540" x2="1150" y2="540" />
  </g>

  <!-- Legend -->
  <g style="fill:black; stroke:none" font-size="12" font-family="Arial" transform="translate(25,25)">
    <rect width="160" height="270" style="fill:none; stroke:black; shape-rendering:crispEdges" />
    <text x="5" y="20" style="fill:black; stroke:none;" font-size="13" font-weight="bold">Given Pair Relationship</text>
    <rect x="120" y="35" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <rect x="120" y="55" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <rect x="120" y="75" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <rect x="120" y="95" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <rect x="120" y="115" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <rect x="120" y="135" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <rect x="120" y="155" width="10" height="10" fill="%s" stroke="%s" stroke-width="1" cursor="pointer"/>
    <text x="15"  y="195" style="fill:black; stroke:none" font-size="12" font-family="Arial" >Zscore gt 15</text>
    <circle cx="125" cy="192" r="6" style="stroke:red; fill:gold; fill-opacity:1.0; stroke-width:1;"/>
    <text x="15" y="215" style="fill:black; stroke:none" font-size="12" font-family="Arial" >Zscore 4 to 15</text>
    <circle cx="125" cy="212" r="3" style="stroke:gold; fill:gold; fill-opacity:1.0; stroke-width:1;"/>
    <text x="15" y="235" style="fill:black; stroke:none" font-size="12" font-family="Arial" >Zscore lt 4</text>
    <circle cx="125" cy="232" r="2" style="stroke:gold; fill:gold; fill-opacity:1.0; stroke-width:1;"/>
    <g id="checkboxes">
    </g>
  </g>


   <g style='fill:black; stroke:none' font-size="17" font-family="Arial">
    <!-- X Axis Labels -->
    <text x="480" y="660">Mean Alleles Shared</text>
    <text x="0"    y="630" >1.0</text>
    <text x="277"  y="630" >1.25</text>
    <text x="564"  y="630" >1.5</text>
    <text x="842" y="630" >1.75</text>
    <text x="1140" y="630" >2.0</text>
  </g>

  <g transform="rotate(270)" style="fill:black; stroke:none" font-size="17" font-family="Arial">
    <!-- Y Axis Labels -->
    <text x="-350" y="-40">SD Alleles Shared</text>
    <text x="-20" y="-10" >1.0</text>
    <text x="-165" y="-10" >0.75</text>
    <text x="-310" y="-10" >0.5</text>
    <text x="-455" y="-10" >0.25</text>
    <text x="-600" y="-10" >0.0</text>
  </g>

<!-- Plot Title -->
<g style="fill:black; stroke:none" font-size="18" font-family="Arial">
    <text x="425" y="-30">%s</text>
</g>

<!-- One group/layer of points for each relationship type -->
'''

SVG_FOOTER = '''
<!-- End of Data -->
</g>
<g id="btTip" visibility="hidden" style="stroke-width:1.0; fill:black; stroke:none;" font-size="10" font-family="Arial">
  <rect width="250" height="110" style="fill:silver" rx="2" ry="2"/>
  <rect id="btHead" width="250" height="20" rx="2" ry="2" />
  <text id="btRel" y="14" x="85">unrelated</text>
  <text id="btMean" y="40" x="4">mean=1.5 +/- 0.04</text>
  <text id="btSdev" y="60" x="4">sdev=0.7 +/- 0.03</text>
  <text id="btPair" y="80" x="4">npairs=1152</text>
  <text id="btGeno" y="100" x="4">ngenos=4783 +/- 24 (min=1000, max=5000)</text>
</g>

<g id="otTip" visibility="hidden" style="stroke-width:1.0; fill:black; stroke:none;" font-size="10" font-family="Arial">
  <rect width="150" height="180" style="fill:silver" rx="2" ry="2"/>
  <rect id="otHead" width="150" height="20" rx="2" ry="2" />
  <text id="otRel" y="14" x="40">sibpairs</text>
  <text id="otS1" y="40" x="4">s1=fid1,iid1</text>
  <text id="otS2" y="60" x="4">s2=fid2,iid2</text>
  <text id="otMean" y="80" x="4">mean=1.82</text>
  <text id="otSdev" y="100" x="4">sdev=0.7</text>
  <text id="otGeno" y="120" x="4">ngeno=4487</text>
  <text id="otRmean" y="140" x="4">relmean=1.85</text>
  <text id="otRsdev" y="160" x="4">relsdev=0.65</text>
</g>
</svg>
'''


DEFAULT_MAX_SAMPLE_SIZE = 5000

REF_COUNT_HOM1 = 3
REF_COUNT_HET  = 2
REF_COUNT_HOM2 = 1
MISSING        = 0

MARKER_PAIRS_PER_SECOND_SLOW = 15000000
MARKER_PAIRS_PER_SECOND_FAST = 70000000

POLYGONS = {
    REL_UNRELATED:   ((1.360, 0.655), (1.385, 0.730), (1.620, 0.575), (1.610, 0.505)),
    REL_HALFSIBS:    ((1.630, 0.500), (1.630, 0.550), (1.648, 0.540), (1.648, 0.490)),
    REL_SIBS:        ((1.660, 0.510), (1.665, 0.560), (1.820, 0.410), (1.820, 0.390)),
    REL_PARENTCHILD: ((1.650, 0.470), (1.650, 0.490), (1.750, 0.440), (1.750, 0.420)),
    REL_DUPE:        ((1.970, 0.000), (1.970, 0.150), (2.000, 0.150), (2.000, 0.000)),
    }

def distance(point1, point2):
    """ Calculate the distance between two points
    """
    (x1,y1) = [float(d) for d in point1]
    (x2,y2) = [float(d) for d in point2]
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    return math.sqrt(dx**2 + dy**2)

def point_inside_polygon(x, y, poly):
    """ Determine if a point (x,y) is inside a given polygon or not
        poly is a list of (x,y) pairs.

        Taken from: http://www.ariel.com.au/a/python-point-int-poly.html
    """

    n = len(poly)
    inside = False

    p1x,p1y = poly[0]
    for i in range(n+1):
        p2x,p2y = poly[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x,p1y = p2x,p2y
    return inside

def readMap(pedfile):
    """
    """
    mapfile = pedfile.replace('.ped', '.map')
    marker_list = []
    if os.path.exists(mapfile):
        print 'readMap: %s' % (mapfile)
        fh = file(mapfile, 'r')
    for line in fh:
        marker_list.append(line.strip().split())
    fh.close()
    print 'readMap: %s markers' % (len(marker_list))
    return marker_list

def calcMeanSD(useme):
    """
    A numerically stable algorithm is given below. It also computes the mean.
    This algorithm is due to Knuth,[1] who cites Welford.[2]
    n = 0
    mean = 0
    M2 = 0

    foreach x in data:
      n = n + 1
      delta = x - mean
      mean = mean + delta/n
      M2 = M2 + delta*(x - mean)      // This expression uses the new value of mean
    end for

    variance_n = M2/n
    variance = M2/(n - 1)
    """
    mean = 0.0
    M2 = 0.0
    sd = 0.0
    n = len(useme)
    if n > 1:
        for i,x in enumerate(useme):
            delta = x - mean
            mean = mean + delta/(i+1) # knuth uses n+=1 at start
            M2 = M2 + delta*(x - mean)      # This expression uses the new value of mean
        variance = M2/(n-1) # assume is sample so lose 1 DOF
        sd = pow(variance,0.5)
    return mean,sd


def doIBSpy(ped=None,basename='',outdir=None,logf=None,
            nrsSamples=10000,title='title',pdftoo=0,Zcutoff=2.0):
    #def doIBS(pedName, title, nrsSamples=None, pdftoo=False):
    """ started with snpmatrix but GRR uses actual IBS counts and sd's
    """
    repOut = [] # text strings to add to the html display
    refallele = {}
    tblf = '%s_table.xls' % (title)
    tbl = file(os.path.join(outdir,tblf), 'w')
    tbl.write(TABLE_HEADER)
    svgf = '%s.svg' % (title)
    svg = file(os.path.join(outdir,svgf), 'w')

    nMarkers = len(ped._markers)
    if nMarkers < 5:
        print sys.stderr, '### ERROR - %d is too few markers for reliable estimation in %s - terminating' % (nMarkers,PROGNAME)
        sys.exit(1)
    nSubjects = len(ped._subjects)
    nrsSamples = min(nMarkers, nrsSamples)
    if opts and opts.use_mito:
        markers = range(nMarkers)
        nrsSamples = min(len(markers), nrsSamples)
        sampleIndexes = sorted(random.sample(markers, nrsSamples))
    else:
        autosomals = ped.autosomal_indices()
        nrsSamples = min(len(autosomals), nrsSamples)
        sampleIndexes = sorted(random.sample(autosomals, nrsSamples))

    print ''
    print 'Getting random.sample of %s from %s total' % (nrsSamples, nMarkers)
    npairs = (nSubjects*(nSubjects-1))/2 # total rows in table
    newfiles=[svgf,tblf]
    explanations = ['rgGRR Plot (requires SVG)','Mean by SD alleles shared - %d rows' % npairs]
    # these go with the output file links in the html file
    s = 'Reading genotypes for %s subjects and %s markers\n' % (nSubjects, nrsSamples)
    logf.write(s)
    minUsegenos = nrsSamples/2 # must have half?
    nGenotypes = nSubjects*nrsSamples
    stime = time.time()
    emptyRows = set()
    genos = numpy.zeros((nSubjects, nrsSamples), dtype=int)
    for s in xrange(nSubjects):
        nValid = 0
        #getGenotypesByIndices(self, s, mlist, format)
        genos[s] = ped.getGenotypesByIndices(s, sampleIndexes, format='ref')
        nValid = sum([1 for g in genos[s] if g])
        if not nValid:
            emptyRows.add(s)
            sub = ped.getSubject(s)
            print 'All missing for row %d (%s)' % (s, sub)
            logf.write('All missing for row %d (%s)\n' % (s, sub))
    rtime = time.time() - stime
    if verbose:
        print '@@Read %s genotypes in %s seconds' % (nGenotypes, rtime)


    ### Now the expensive part.  For each pair of subjects, we get the mean number
    ### and standard deviation of shared alleles over all of the markers where both
    ### subjects have a known genotype.  Identical subjects should have mean shared
    ### alleles very close to 2.0 with a standard deviation very close to 0.0.
    tot = nSubjects*(nSubjects-1)/2
    nprog = tot/10
    nMarkerpairs = tot * nrsSamples
    estimatedTimeSlow = nMarkerpairs/MARKER_PAIRS_PER_SECOND_SLOW
    estimatedTimeFast = nMarkerpairs/MARKER_PAIRS_PER_SECOND_FAST

    pairs = []
    pair_data = {}
    means = []    ## Mean IBS for each pair
    ngenoL = []   ## Count of comparable genotypes for each pair
    sdevs = []    ## Standard dev for each pair
    rels  = []    ## A relationship code for each pair
    zmeans  = [0.0 for x in xrange(tot)]    ## zmean score for each pair for the relgroup
    zstds  = [0.0 for x in xrange(tot)]   ## zstd score for each pair for the relgrp
    skip = set()
    ndone = 0     ## How many have been done so far

    logf.write('Calculating %d pairs...\n' % (tot))
    logf.write('Estimated time is %2.2f to %2.2f seconds ...\n' % (estimatedTimeFast, estimatedTimeSlow))

    t1sum = 0
    t2sum = 0
    t3sum = 0
    now = time.time()
    scache = {}
    _founder_cache = {}
    C_CODE = """
    #include "math.h"
    int i;
    int sumibs = 0;
    int ssqibs = 0;
    int ngeno  = 0;
    float mean = 0;
    float M2 = 0;
    float delta = 0;
    float sdev=0;
    float variance=0;
    for (i=0; i<nrsSamples; i++) {
        int a1 = g1[i];
        int a2 = g2[i];
        if (a1 != 0 && a2 != 0) {
            ngeno += 1;
            int shared = 2-abs(a1-a2);
            delta = shared - mean;
            mean = mean + delta/ngeno;
            M2 += delta*(shared-mean);
            // yes that second time, the updated mean is used see calcmeansd above;
            //printf("%d %d %d %d %d %d\\n", i, a1, a2, ngeno, shared, squared);
            }
    }
    if (ngeno > 1) {
        variance = M2/(ngeno-1);
        sdev = sqrt(variance);
        //printf("OK: %d %3.2f %3.2f\\n", ngeno, mean, sdev);
    }
    //printf("%d %d %d %1.2f %1.2f\\n", ngeno, sumibs, ssqibs, mean, sdev);
    result[0] = ngeno;
    result[1] = mean;
    result[2] = sdev;
    return_val = ngeno;
    """
    started = time.time()
    for s1 in xrange(nSubjects):
        if s1 in emptyRows:
            continue
        (fid1,iid1,did1,mid1,sex1,phe1,iid1,d_sid1,m_sid1) = scache.setdefault(s1, ped.getSubject(s1))

        isFounder1 = _founder_cache.setdefault(s1, (did1==mid1))
        g1 = genos[s1]

        for s2 in xrange(s1+1, nSubjects):
            if s2 in emptyRows:
                continue
            t1s = time.time()

            (fid2,iid2,did2,mid2,sex2,phe2,iid2,d_sid2,m_sid2) = scache.setdefault(s2, ped.getSubject(s2))

            g2 = genos[s2]
            isFounder2 = _founder_cache.setdefault(s2, (did2==mid2))

            # Determine the relationship for this pair
            relcode = REL_UNKNOWN
            if (fid2 == fid1):
                if iid1 == iid2:
                    relcode = REL_DUPE
                elif (did2 == did1) and (mid2 == mid1) and did1 != mid1:
                    relcode = REL_SIBS
                elif (iid1 == mid2) or (iid1 == did2) or (iid2 == mid1) or (iid2 == did1):
                    relcode = REL_PARENTCHILD
                elif (str(did1) != '0' and (did2 == did1)) or (str(mid1) != '0' and (mid2 == mid1)):
                    relcode = REL_HALFSIBS
                else:
                    # People in the same family should be marked as some other
                    # form of related.  In general, these people will have a
                    # pretty random spread of similarity. This distinction is
                    # probably not very useful most of the time
                    relcode = REL_RELATED
            else:
                ### Different families
                relcode = REL_UNRELATED

            t1e = time.time()
            t1sum += t1e-t1s


            ### Calculate sum(2-abs(a1-a2)) and sum((2-abs(a1-a2))**2) and count
            ### the number of contributing genotypes.  These values are not actually
            ### calculated here, but instead are looked up in a table for speed.
            ### FIXME: This is still too slow ...
            result = [0.0, 0.0, 0.0]
            ngeno = weave.inline(C_CODE, ['g1', 'g2', 'nrsSamples', 'result'])
            if ngeno >= minUsegenos:
                _, mean, sdev = result
                means.append(mean)
                sdevs.append(sdev)
                ngenoL.append(ngeno)
                pairs.append((s1, s2))
                rels.append(relcode)
            else:
                skip.add(ndone) # signal no comparable genotypes for this pair
            ndone += 1
            t2e = time.time()
            t2sum += t2e-t1e
            t3e = time.time()
            t3sum += t3e-t2e

    logme = [ 'T1:  %s' % (t1sum), 'T2:  %s' % (t2sum), 'T3:  %s' % (t3sum),'TOT: %s' % (t3e-now),
             '%s pairs with no (or not enough) comparable genotypes (%3.1f%%)' % (len(skip),
                                                            float(len(skip))/float(tot)*100)]
    logf.write('%s\n' % '\t'.join(logme))
    ### Calculate mean and standard deviation of scores on a per relationship
    ### type basis, allowing us to flag outliers for each particular relationship
    ### type
    relstats = {}
    relCounts = {}
    outlierFiles = {}
    for relCode, relInfo in REL_LOOKUP.items():
        relName, relColor, relStyle = relInfo
        useme = [means[x] for x in xrange(len(means)) if rels[x] == relCode]
        relCounts[relCode] = len(useme)
        mm = scipy.mean(useme)
        ms = scipy.std(useme)
        useme = [sdevs[x] for x in xrange(len(sdevs)) if rels[x] == relCode]
        sm = scipy.mean(useme)
        ss = scipy.std(useme)
        relstats[relCode] = {'sd':(sm,ss), 'mean':(mm,ms)}
        s = 'Relstate %s (n=%d): mean(mean)=%3.2f sdev(mean)=%3.2f, mean(sdev)=%3.2f sdev(sdev)=%3.2f\n' % \
          (relName,relCounts[relCode], mm, ms, sm, ss)
        logf.write(s)

    ### now fake z scores for each subject like abecasis recommends max(|zmu|,|zsd|)
    ### within each group, for each pair, z=(groupmean-pairmean)/groupsd
    available = len(means)
    logf.write('%d pairs are available of %d\n' % (available, tot))
    ### s = '\nOutliers:\nrelationship\tzmean\tzsd\tped1\tped2\tmean\tsd\trmeanmean\trmeansd\trsdmean\trsdsd\n'
    ### logf.write(s)
    pairnum   = 0
    offset    = 0
    nOutliers = 0
    cexs      = []
    outlierRecords = dict([(r, []) for r in range(N_RELATIONSHIP_TYPES)])
    zsdmax = 0
    for s1 in range(nSubjects):
        if s1 in emptyRows:
            continue
        (fid1,iid1,did1,mid1,sex1,aff1,ok1,d_sid1,m_sid1) = scache[s1]
        for s2 in range(s1+1, nSubjects):
            if s2 in emptyRows:
                continue
            if pairnum not in skip:
                ### Get group stats for this relationship
                (fid2,iid2,did2,mid2,sex2,aff2,ok2,d_sid2,m_sid2) = scache[s2]
                try:
                    r = rels[offset]
                except IndexError:
                    logf.write('###OOPS offset %d available %d  pairnum %d  len(rels) %d', offset, available, pairnum, len(rels))
                notfound = ('?',('?','0','0'))
                relInfo = REL_LOOKUP.get(r,notfound)
                relName, relColor, relStyle = relInfo
                rmm,rmd = relstats[r]['mean'] # group mean, group meansd alleles shared
                rdm,rdd = relstats[r]['sd'] # group sdmean, group sdsd alleles shared

                try:
                    zsd = (sdevs[offset] - rdm)/rdd # distance from group mean in group sd units
                except:
                    zsd = 1
                if abs(zsd) > zsdmax:
                    zsdmax = zsd # keep for sort scaling
                try:
                    zmean = (means[offset] - rmm)/rmd # distance from group mean
                except:
                    zmean = 1
                zmeans[offset] = zmean
                zstds[offset] = zsd
                pid=(s1,s2)
                zrad = max(zsd,zmean)
                if zrad < 4:
                    zrad = 2
                elif 4 < zrad < 15:
                    zrad = 3 # to 9
                else: # > 15 6=24+
                    zrad=zrad/4
                    zrad = min(zrad,6) # scale limit
                zrad = max(2,max(zsd,zmean)) # as > 2, z grows
                pair_data[pid] = (zmean,zsd,r,zrad)
                if max(zsd,zmean) > Zcutoff: # is potentially interesting
                    mean = means[offset]
                    sdev = sdevs[offset]
                    outlierRecords[r].append((mean, sdev, zmean, zsd, fid1, iid1, fid2, iid2, rmm, rmd, rdm, rdd,did1,mid1,did2,mid2))
                    nOutliers += 1
                tbl.write('%s_%s\t%s_%s\t%f\t%f\t%f\t%f\t%d\t%s\t%s\t%s\t%s\t%s\n' % \
                          (fid1, iid1, fid2, iid2, mean, sdev, zmean,zsd, ngeno, relName, did1,mid1,did2,mid2))
                offset += 1
            pairnum += 1
    logf.write( 'Outliers: %s\n' % (nOutliers))

    ### Write outlier files for each relationship type
    repOut.append('<h2>Outliers in tab delimited files linked above are also listed below</h2>')
    lzsd = round(numpy.log10(zsdmax)) + 1
    scalefactor = 10**lzsd
    for relCode, relInfo in REL_LOOKUP.items():
        relName, _, _ = relInfo
        outliers = outlierRecords[relCode]
        if not outliers:
            continue
        outliers = [(scalefactor*int(abs(x[3]))+ int(abs(x[2])),x) for x in outliers] # decorate
        outliers.sort()
        outliers.reverse() # largest deviation first
        outliers = [x[1] for x in outliers] # undecorate
        nrows = len(outliers)
        truncated = 0
        if nrows > MAX_SHOW_ROWS:
            s = '<h3>%s outlying pairs (top %d of %d) from %s</h3><table border="0" cellpadding="3">' % \
               (relName,MAX_SHOW_ROWS,nrows,title)
            truncated = nrows - MAX_SHOW_ROWS
        else:
            s = '<h3>%s outlying pairs (n=%d) from %s</h3><table border="0" cellpadding="3">' % (relName,nrows,title)
        repOut.append(s)
        fhname = '%s_rgGRR_%s_outliers.xls' % (title, relName)
        fhpath = os.path.join(outdir,fhname)
        fh = open(fhpath, 'w')
        newfiles.append(fhname)
        explanations.append('%s Outlier Pairs %s, N=%d, Cutoff SD=%f' % (relName,title,len(outliers),Zcutoff))
        fh.write(OUTLIERS_HEADER)
        s = ''.join(['<th>%s</th>' % x for x in OUTLIERS_HEADER_list])
        repOut.append('<tr align="center">%s</tr>' % s)
        for n,rec in enumerate(outliers):
            #(mean, sdev, zmean, zsd, fid1, iid1, fid2, iid2, rmm, rmd, rdm, rdd) = rec
            s = '%f\t%f\t%f\t%f\t%s\t%s\t%s\t%s\t%f\t%f\t%f\t%f\t%s\t%s\t%s\t%s\t' % tuple(rec)
            fh.write('%s%s\n' % (s,relName))
            # (mean, sdev, zmean, zsd, fid1, iid1, fid2, iid2, rmm, rmd, rdm, rdd, did1,mid1,did2,mid2))
            s = '''<td>%f</td><td>%f</td><td>%f</td><td>%f</td><td>%s</td><td>%s</td>
            <td>%s</td><td>%s</td><td>%f</td><td>%f</td><td>%f</td><td>%f</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td>''' % tuple(rec)
            s = '%s<td>%s</td>' % (s,relName)
            if n < MAX_SHOW_ROWS:
                repOut.append('<tr align="center">%s</tr>' % s)
        if truncated > 0:
            repOut.append('<H2>WARNING: %d rows truncated - see outlier file for all %d rows</H2>' % (truncated,
                                                                                            nrows))
        fh.close()
        repOut.append('</table><p>')

    ### Now, draw the plot in jpeg and svg formats, and optionally in the PDF format
    ### if requested
    logf.write('Plotting ...')
    pointColors = [REL_COLORS[rel] for rel in rels]
    pointStyles = [REL_POINTS[rel] for rel in rels]

    mainTitle = '%s (%s subjects, %d snp)' % (title, nSubjects, nrsSamples)
    svg.write(SVG_HEADER % (SVG_COLORS[0],SVG_COLORS[1],SVG_COLORS[2],SVG_COLORS[3],SVG_COLORS[4],
        SVG_COLORS[5],SVG_COLORS[6],SVG_COLORS[0],SVG_COLORS[0],SVG_COLORS[1],SVG_COLORS[1],
        SVG_COLORS[2],SVG_COLORS[2],SVG_COLORS[3],SVG_COLORS[3],SVG_COLORS[4],SVG_COLORS[4],
        SVG_COLORS[5],SVG_COLORS[5],SVG_COLORS[6],SVG_COLORS[6],mainTitle))
    #rpy.r.jpeg(filename='%s.jpg' % (title), width=1600, height=1200, pointsize=12, quality=100, bg='white')
    #rpy.r.par(mai=(1,1,1,0.5))
    #rpy.r('par(xaxs="i",yaxs="i")')
    #rpy.r.plot(means, sdevs, main=mainTitle, ylab=Y_AXIS_LABEL, xlab=X_AXIS_LABEL, cex=cexs, col=pointColors, pch=pointStyles, xlim=(0,2), ylim=(0,2))
    #rpy.r.legend(LEGEND_ALIGN, legend=REL_STATES, pch=REL_POINTS, col=REL_COLORS, title=LEGEND_TITLE)
    #rpy.r.grid(nx=10, ny=10, col='lightgray', lty='dotted')
    #rpy.r.dev_off()

    ### We will now go through each relationship type to partition plot points
    ### into "bulk" and "outlier" groups.  Bulk points will represent common
    ### mean/sdev pairs and will cover the majority of the points in the plot --
    ### they will use generic tooltip informtion about all of the pairs
    ### represented by that point.  "Outlier" points will be uncommon pairs,
    ### with very specific information in their tooltips.  It would be nice to
    ### keep hte total number of plotted points in the SVG representation to
    ### ~10000 (certainly less than 100000?)
    pointMap = {}
    orderedRels = [y[1] for y in reversed(sorted([(relCounts.get(x, 0),x) for x in REL_LOOKUP.keys()]))]
    # do we really want this? I want out of zone points last and big
    for relCode in orderedRels:
        svgColor = SVG_COLORS[relCode]
        relName, relColor, relStyle = REL_LOOKUP[relCode]
        svg.write('<g id="%s" style="stroke:%s; fill:%s; fill-opacity:1.0; stroke-width:1;" cursor="pointer">\n' % (relName, svgColor, svgColor))
        pMap = pointMap.setdefault(relCode, {})
        nPoints = 0
        rpairs=[]
        rgenos=[]
        rmeans=[]
        rsdevs=[]
        rz = []
        for x,rel in enumerate(rels): # all pairs
            if rel == relCode:
                s1,s2 = pairs[x]
                pid=(s1,s2)
                zmean,zsd,r,zrad = pair_data[pid][:4]
                rpairs.append(pairs[x])
                rgenos.append(ngenoL[x])
                rmeans.append(means[x])
                rsdevs.append(sdevs[x])
                rz.append(zrad)
        ### Now add the svg point group for this relationship to the svg file
        for x in range(len(rmeans)):
            svgX = '%d' % ((rmeans[x] - 1.0) * PLOT_WIDTH) # changed so mean scale is 1-2
            svgY = '%d' % (PLOT_HEIGHT - (rsdevs[x] * PLOT_HEIGHT)) # changed so sd scale is 0-1
            s1, s2 = rpairs[x]
            (fid1,uid1,did1,mid1,sex1,phe1,iid1,d_sid1,m_sid1) = scache[s1]
            (fid2,uid2,did2,mid2,sex2,phe2,iid2,d_sid2,m_sid2) = scache[s2]
            ngenos = rgenos[x]
            nPoints += 1
            point = pMap.setdefault((svgX, svgY), [])
            point.append((rmeans[x], rsdevs[x], fid1, iid1, did1, mid1, fid2, iid2, did2, mid2, ngenos,rz[x]))
        for (svgX, svgY) in pMap:
            points = pMap[(svgX, svgY)]
            svgX = int(svgX)
            svgY = int(svgY)
            if len(points) > 1:
                mmean,dmean = calcMeanSD([p[0] for p in points])
                msdev,dsdev = calcMeanSD([p[1] for p in points])
                mgeno,dgeno = calcMeanSD([p[-1] for p in points])
                mingeno = min([p[-1] for p in points])
                maxgeno = max([p[-1] for p in points])
                svg.write("""<circle cx="%d" cy="%d" r="2"
                onmouseover="showBTT(evt, %d, %1.2f, %1.2f, %1.2f, %1.2f, %d, %d, %d, %d, %d)"
                onmouseout="hideBTT(evt)" />\n""" % (svgX, svgY, relCode, mmean, dmean, msdev, dsdev, len(points), mgeno, dgeno, mingeno, maxgeno))
            else:
                mean, sdev, fid1, iid1, did1, mid1, fid2, iid2, did2, mid2, ngenos, zrad = points[0][:12]
                rmean = float(relstats[relCode]['mean'][0])
                rsdev = float(relstats[relCode]['sd'][0])
                if zrad < 4:
                    zrad = 2
                elif 4 < zrad < 9:
                    zrad = 3 # to 9
                else: # > 9 5=15+
                    zrad=zrad/3
                    zrad = min(zrad,5) # scale limit
                if zrad <= 3:
                    svg.write('<circle cx="%d" cy="%d" r="%s" onmouseover="showOTT(evt, %d, \'%s,%s,%s,%s\', \'%s,%s,%s,%s\', %1.2f, %1.2f, %s, %1.2f, %1.2f)" onmouseout="hideOTT(evt)" />\n' % (svgX, svgY, zrad, relCode, fid1, iid1, did1, mid1, fid2, iid2, did2, mid2, mean, sdev, ngenos, rmean, rsdev))
                else: # highlight pairs a long way from expectation by outlining circle in red
                    svg.write("""<circle cx="%d" cy="%d" r="%s" style="stroke:red; fill:%s; fill-opacity:1.0; stroke-width:1;"
                    onmouseover="showOTT(evt, %d, \'%s,%s,%s,%s\', \'%s,%s,%s,%s\', %1.2f, %1.2f, %s, %1.2f, %1.2f)"
                    onmouseout="hideOTT(evt)" />\n""" % \
                    (svgX, svgY, zrad, svgColor, relCode, fid1, iid1, did1, mid1, fid2, iid2, did2, mid2, mean, sdev, ngenos, rmean, rsdev))
        svg.write('</g>\n')

    ### Create a pdf as well if indicated on the command line
    ### WARNING! for framingham share, with about 50M pairs, this is a 5.5GB pdf!
##    if pdftoo:
##        pdfname = '%s.pdf' % (title)
##        rpy.r.pdf(pdfname, 6, 6)
##        rpy.r.par(mai=(1,1,1,0.5))
##        rpy.r('par(xaxs="i",yaxs="i")')
##        rpy.r.plot(means, sdevs, main='%s, %d snp' % (title, nSamples), ylab=Y_AXIS_LABEL, xlab=X_AXIS_LABEL, cex=cexs, col=pointColors, pch=pointStyles, xlim=(0,2), ylim=(0,2))
##        rpy.r.legend(LEGEND_ALIGN, legend=REL_STATES, pch=REL_POINTS, col=REL_COLORS, title=LEGEND_TITLE)
##        rpy.r.grid(nx=10, ny=10, col='lightgray', lty='dotted')
##        rpy.r.dev_off()

    ### Draw polygons
    if showPolygons:
        svg.write('<g id="polygons" cursor="pointer">\n')
        for rel, poly in POLYGONS.items():
            points = ' '.join(['%s,%s' % ((p[0]-1.0)*float(PLOT_WIDTH), (PLOT_HEIGHT - p[1]*PLOT_HEIGHT)) for p in poly])
            svg.write('<polygon points="%s" fill="transparent" style="stroke:%s; stroke-width:1"/>\n' % (points, SVG_COLORS[rel]))
        svg.write('</g>\n')


    svg.write(SVG_FOOTER)
    svg.close()
    return newfiles,explanations,repOut

def doIBS(n=100):
    """parse parameters from galaxy
    expect 'input pbed path' 'basename' 'outpath' 'title' 'logpath' 'n'
    <command interpreter="python">
         rgGRR.py $i.extra_files_path/$i.metadata.base_name "$i.metadata.base_name"
        '$out_file1' '$out_file1.files_path' "$title1"  '$n' '$Z' 
    </command>

    """
    u="""<command interpreter="python">
         rgGRR.py $i.extra_files_path/$i.metadata.base_name "$i.metadata.base_name"
        '$out_file1' '$out_file1.files_path' "$title1"  '$n' '$Z'
         </command>
      """


    if len(sys.argv) < 7:
        print >> sys.stdout, 'Need pbed inpath, basename, out_htmlname, outpath, title, logpath, nSNP, Zcutoff on command line please'
        print >> sys.stdout, u
        sys.exit(1)
    ts = '%s%s' % (string.punctuation,string.whitespace)
    ptran =  string.maketrans(ts,'_'*len(ts))
    inpath = sys.argv[1]
    ldinpath = os.path.split(inpath)[0]
    basename = sys.argv[2]
    outhtml = sys.argv[3]
    newfilepath = sys.argv[4]
    title = sys.argv[5].translate(ptran)
    logfname = 'Log_%s.txt' % title
    logpath = os.path.join(newfilepath,logfname) # log was a child - make part of html extra_files_path zoo
    n = int(sys.argv[6])
    try:
        Zcutoff = float(sys.argv[7])
    except:
        Zcutoff = 2.0
    try:
        os.makedirs(newfilepath)
    except:
        pass
    logf = file(logpath,'w')
    efp,ibase_name = os.path.split(inpath) # need to use these for outputs in files_path
    ped = plinkbinJZ.BPed(inpath)
    ped.parse(quick=True)	
    if ped == None:
        print >> sys.stderr, '## doIBSpy problem - cannot open %s or %s - cannot run' % (ldreduced,basename)
        sys.exit(1)
    newfiles,explanations,repOut = doIBSpy(ped=ped,basename=basename,outdir=newfilepath,
                                    logf=logf,nrsSamples=n,title=title,pdftoo=0,Zcutoff=Zcutoff)
    logf.close()
    logfs = file(logpath,'r').readlines()
    lf = file(outhtml,'w')
    lf.write(galhtmlprefix % PROGNAME)
    # this is a mess. todo clean up - should each datatype have it's own directory? Yes
    # probably. Then titles are universal - but userId libraries are separate.
    s = '<div>Output from %s run at %s<br>\n' % (PROGNAME,timenow())
    lf.write('<h4>%s</h4>\n' % s)
    fixed = ["'%s'" % x for x in sys.argv] # add quotes just in case
    s = 'If you need to rerun this analysis, the command line was\n<pre>%s</pre>\n</div>' % (' '.join(fixed))
    lf.write(s)
    # various ways of displaying svg - experiments related to missing svg mimetype on test (!)
    #s = """<object data="%s" type="image/svg+xml"  width="%d" height="%d">
    #       <embed src="%s" type="image/svg+xml" width="%d" height="%d" />
    #       </object>""" % (newfiles[0],PLOT_WIDTH,PLOT_HEIGHT,newfiles[0],PLOT_WIDTH,PLOT_HEIGHT)
    s = """ <embed src="%s" type="image/svg+xml" width="%d" height="%d" />""" % (newfiles[0],PLOT_WIDTH,PLOT_HEIGHT)
    #s = """ <iframe src="%s" type="image/svg+xml" width="%d" height="%d" />""" % (newfiles[0],PLOT_WIDTH,PLOT_HEIGHT)
    lf.write(s)
    lf.write('<div><h4>Click the links below to save output files and plots</h4><br><ol>\n')
    for i in range(len(newfiles)):
       if i == 0:
            lf.write('<li><a href="%s" type="image/svg+xml" >%s</a></li>\n' % (newfiles[i],explanations[i]))
       else:
             lf.write('<li><a href="%s">%s</a></li>\n' % (newfiles[i],explanations[i]))
    flist = os.listdir(newfilepath)
    for fname in flist:
        if not fname in newfiles:
             lf.write('<li><a href="%s">%s</a></li>\n' % (fname,fname))
    lf.write('</ol></div>')
    lf.write('<div>%s</div>' % ('\n'.join(repOut))) # repOut is a list of tables
    lf.write('<div><hr><h3>Log from this job (also stored in %s)</h3><pre>%s</pre><hr></div>' % (logfname,''.join(logfs)))
    lf.write('</body></html>\n')
    lf.close()
    logf.close()

if __name__ == '__main__':
    doIBS()
