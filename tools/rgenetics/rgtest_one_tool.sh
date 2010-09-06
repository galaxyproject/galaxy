#!/bin/sh
# script to generate all functional test outputs for each rgenetics tool
# could be run at installation to ensure all dependencies are in place?
case $# in 0) echo "USAGE: ${0##*/} TooltoTest galaxyRoot outRoot"; exit 1;;
           [1-2]*) echo "Need ToolToTest and paths for galaxyRoot outRoot as parameters"; exit 2;;
           [5-10]*) echo "Too many arguments - ToolToTest and paths for galaxyRoot outRoot as parameters"; exit 2;;
           *)
esac
GALAXYROOT=$2
OUTROOT=$3
echo "using $GALAXYROOT"
# change this as needed for your local install
INPATH="${GALAXYROOT}/test-data"
JARPATH="${GALAXYROOT}/tool-data/shared/jars"
TOOLPATH="${GALAXYROOT}/tools/rgenetics"
OROOT="${OUTROOT}/test-data/rgtestouts"
NORMALOROOT="${OUTROOT}/test-data"
case "$1" in
'rgManQQ')

TOOL="rgManQQ"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
CL="python $TOOLPATH/$TOOL.py "$INPATH/smallwgaP.xls" $NPRE ${OUTPATH}/${NPRE}.html $OUTPATH 1 2 7 0"
# rgManQQ.py '$input_file' "$name" '$out_html' '$out_html.files_path' '$chrom_col' '$offset_col' 
# '$pval_col'
#python /opt/galaxy/tools/rgenetics/rgManQQ.py /opt/galaxy/test-data/smallwgaP.xls rgManQQtest1 
#/opt/galaxy/test-data/rgtestouts/rgManQQ/rgManQQtest1.html /opt/galaxy/test-data/rgtestouts/rgManQQ 1 2 5,7 
echo "Testing $TOOL using $CL"
python $TOOLPATH/$TOOL.py "$INPATH/smallwgaP.xls" $NPRE ${OUTPATH}/${NPRE}.html $OUTPATH 1 2 7 0
;;

'rgfakePhe')
TOOL="rgfakePhe"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
PSSCRIPT="$OUTPATH/script_file"
echo "{'pN':'normtest','pT':'rnorm','pP':\"{'Mean':'100', 'SD':'10'}\"}" > $PSSCRIPT
echo "{'pN':'cattest','pT':'cat','pP':\"{'values':'red,green,blue'}\"}" >> $PSSCRIPT
echo "{'pN':'uniftest','pT':'$f.series.phetype','pP':\"{'low':'1','hi':'100'}\"}" >> $PSSCRIPT
echo "{'pN':'gammatest','pT':'rgamma','pP':\"{'Alpha':'1', 'Beta':'0.1'}\"}" >> $PSSCRIPT
echo "{'pN':'poissontest','pT':'poisson','pP':\"{'lamb':'1.0',}\"}" >> $PSSCRIPT
echo "{'pN':'exptest','pT':'exponential','pP':\"{'Mean':'100.0',}\"}" >> $PSSCRIPT
echo "{'pN':'weibtest','pT':'weibull','pP':\"{'Alpha':'1.0', 'Beta':'0.1'}\"}" >> $PSSCRIPT
echo "now doing $TOOL"
python $TOOLPATH/$TOOL.py ${INPATH}/tinywga $NPRE $NPRE.pphe $OUTPATH $PSSCRIPT
#   <command interpreter="python">rgfakePhe.py '$infile1.extra_files_path/$infile1.metadata.base_name'
#   "$title1" '$ppheout' '$ppheout.files_path' '$script_file'
#
;;
'rgQC')

TOOL="rgQC"
NPRE=${TOOL}test1
echo "now doing $TOOL"
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
CMD="python $TOOLPATH/$TOOL.py -i $INPATH/tinywga -o $NPRE -s ${OUTPATH}/${NPRE}.html -p $OUTPATH"
echo "doing $CMD"
$CMD
# rgQC.py -i '$input_file.extra_files_path/$input_file.metadata.base_name' -o "$out_prefix" 
# -s '$html_file' -p '$html_file.files_path' 
#
;;

'rgGRR')
TOOL="rgGRR"
NPRE=${TOOL}test1
echo "now doing $TOOL"
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
cmd="$TOOLPATH/$TOOL.py "$INPATH/tinywga" "tinywga" $OUTPATH/${NPRE}.html $OUTPATH "$NPRE" '100' '6' 'true'"
echo "Doing $cmd"
python $TOOLPATH/$TOOL.py "$INPATH/tinywga" "tinywga" $OUTPATH/${NPRE}.html $OUTPATH "$NPRE" '100' '6' 
# rgGRR.py $i.extra_files_path/$i.metadata.base_name "$i.metadata.base_name"
#'$out_file1' '$out_file1.files_path' "$title"  '$n' '$Z' 
;;
'rgLDIndep')
TOOL="rgLDIndep"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
python $TOOLPATH/$TOOL.py "$INPATH" "tinywga" "$NPRE" 1 1 0 0 1 1 $OUTPATH/${NPRE}.pbed $OUTPATH 10000 5000 0.1 
#rgLDIndep.py '$input_file.extra_files_path' '$input_file.metadata.base_name' '$title' '$mind'
# '$geno' '$hwe' '$maf' '$mef' '$mei' '$out_file1'
#'$out_file1.files_path'  '$window' '$step' '$r2' 
;;

'rgPedSub')
TOOL="rgPedSub"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
PSSCRIPT="$OUTPATH/pedsub.script"
echo "title~~~~$NPRE" > $PSSCRIPT
echo "output1~~~~${OUTPATH}/${NPRE}.lped" >> $PSSCRIPT
echo "outformat~~~~lped" >> $PSSCRIPT
echo "basename~~~~tinywga" >> $PSSCRIPT
echo "inped~~~~$INPATH/tinywga" >> $PSSCRIPT
echo "outdir~~~~$OUTPATH" >> $PSSCRIPT
echo "region~~~~" >> $PSSCRIPT
echo "relfilter~~~~all" >> $PSSCRIPT
echo "rslist~~~~rs2283802Xrs2267000Xrs16997606Xrs4820537Xrs3788347Xrs756632Xrs4820539Xrs2283804Xrs2267006Xrs4822363X" >> $PSSCRIPT
echo "now doing $TOOL"
python $TOOLPATH/$TOOL.py $PSSCRIPT
rm -rf $PSSCRIPT
;;

'rgfakePhe')

TOOL="rgfakePhe"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
PSSCRIPT="$OUTPATH/script_file"
echo "{'pN':'normtest','pT':'rnorm','pP':\"{'Mean':'100', 'SD':'10'}\"}" > $PSSCRIPT
echo "{'pN':'cattest','pT':'cat','pP':\"{'values':'red,green,blue'}\"}" >> $PSSCRIPT
echo "{'pN':'uniftest','pT':'$f.series.phetype','pP':\"{'low':'1','hi':'100'}\"}" >> $PSSCRIPT
echo "{'pN':'gammatest','pT':'rgamma','pP':\"{'Alpha':'1', 'Beta':'0.1'}\"}" >> $PSSCRIPT
echo "{'pN':'poissontest','pT':'poisson','pP':\"{'lamb':'1.0',}\"}" >> $PSSCRIPT
echo "{'pN':'exptest','pT':'exponential','pP':\"{'Mean':'100.0',}\"}" >> $PSSCRIPT
echo "{'pN':'weibtest','pT':'weibull','pP':\"{'Alpha':'1.0', 'Beta':'0.1'}\"}" >> $PSSCRIPT
echo "now doing $TOOL"
python $TOOLPATH/$TOOL.py $PSSCRIPT
;;

'rgClean')
TOOL="rgClean"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
python $TOOLPATH/$TOOL.py $INPATH "tinywga" "$NPRE" 1 1 0 0 1 1 $OUTPATH/${NPRE}.pbed $OUTPATH 0 0 0 0
# rgClean.py '$input_file.extra_files_path' '$input_file.metadata.base_name' '$title' '$mind'
#        '$geno' '$hwe' '$maf' '$mef' '$mei' '$out_file1' '$out_file1.files_path'
#        '${GALAXY_DATA_INDEX_DIR}/rg/bin/plink' '$relfilter' '$afffilter' '$sexfilter' '$fixaff'
#
;;

'rgEigPCA')

TOOL="rgEigPCA"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
python $TOOLPATH/$TOOL.py "$INPATH/tinywga" "$NPRE" ${OUTPATH}/${NPRE}.html $OUTPATH 4 2 2 2 $OUTPATH/rgEigPCAtest1.txt
#    rgEigPCA.py "$i.extra_files_path/$i.metadata.base_name" "$title" "$out_file1"
#    "$out_file1.files_path" "$k" "$m" "$t" "$s" "$pca" 
#
;;

'rgfakePed')
TOOL="rgfakePed"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
echo "now doing $TOOL"
python $TOOLPATH/$TOOL.py --title "$NPRE" -o $OUTPATH/${NPRE}.lped -p $OUTPATH -c "20" -n "40" -s "10" -w "0" -v "0" -l "pbed" -d "T" -m "0" -M "0"
#rgfakePed.py --title '$title1' 
#  -o '$out_file1' -p '$out_file1.extra_files_path' -c '$ncases' -n '$ntotal'
#  -s '$nsnp'  -w '$lowmaf' -v '$missingValue' -l '$outFormat'
#  -d '$mafdist' -m '$missingRate' -M '$mendelRate'
;;

'rgHaploView')

TOOL="rgHaploView"
NPRE=${TOOL}test1
OUTPATH="$OROOT/$TOOL"
rm -rf $OUTPATH/*
CL="python $TOOLPATH/$TOOL.py ''  'rs2283802 rs2267000 rs16997606 rs4820537 rs3788347 rs756632 rs4820539 rs2283804 rs2267006 rs4822363' '$NPRE' $OUTPATH/${NPRE}.html  '$INPATH' 'tinywga' 0.0 200000 'RSQ' 'lo' '2048' '$OUTPATH' 'noinfo' '0.8' 'YRI' $JARPATH/haploview.jar"
echo "Testing $TOOL using $CL"
python $TOOLPATH/$TOOL.py ""  "rs2283802 rs2267000 rs16997606 rs4820537 rs3788347 rs756632 rs4820539 rs2283804 rs2267006 rs4822363" \
"$NPRE" $OUTPATH/${NPRE}.html  "$INPATH" "tinywga" 0.0 200000 "RSQ" "lo" "2048" "$OUTPATH" "noinfo" "0.8" "YRI" $JARPATH/haploview.jar
#  rgHaploView.py "$ucsc_region" "$rslist" "$title" "$output1"  
#  "$lhistIn.extra_files_path" "$lhistIn.metadata.base_name"
#  "$minmaf" "$maxdist" "$ldtype" "$hires" "$memsize" "$output1.files_path" 
#  "$infoTrack" "$tagr2" "$hmpanel" ${GALAXY_DATA_INDEX_DIR}/rg/bin/haploview.jar
# note these statistical tools do NOT generate composite outputs
;;

'rgGLM')
TOOL="rgGLM"
NPRE=${TOOL}test1
OUTPATH=$NORMALOROOT
python $TOOLPATH/$TOOL.py "$INPATH/tinywga" $INPATH/tinywga "$NPRE" "c1" "" $OUTPATH/${NPRE}_GLM.xls \
$OUTPATH/${NPRE}_GLM_log.txt "tinywga" "" "" "" 1 1 0 0 $OUTPATH/${NPRE}_GLM_topTable.gff 
##        rgGLM.py '$i.extra_files_path/$i.metadata.base_name' '$phef.extra_files_path/$phef.metadata.base_name'
##        "$title1" '$predvar' '$covar' '$out_file1' '$logf' '$dbkey' '$i.metadata.base_name'
##        '$inter' '$cond' '$gender' '$mind' '$geno' '$maf' '$logistic' '$gffout'
;;

'rgTDT')
TOOL="rgTDT"
NPRE=${TOOL}test1
OUTPATH=$NORMALOROOT
python $TOOLPATH/$TOOL.py -i "$INPATH/tinywga"  -o "$NPRE" -r $OUTPATH/${NPRE}_TDT.xls \
-l $OUTPATH/${NPRE}_TDT_log.txt -g $OUTPATH/${NPRE}_TDT_topTable.gff
##        rgTDT.py -i '$infile.extra_files_path/$infile.metadata.base_name' -o '$title'
##        -r '$out_file1' -l '$logf' -x '${GALAXY_DATA_INDEX_DIR}/rg/bin/plink'
##        -g '$gffout'
;;

'rgCaCo')
TOOL="rgCaCo"
NPRE=${TOOL}test1
OUTPATH=$NORMALOROOT
echo "now doing $TOOL"
python $TOOLPATH/rgCaCo.py $INPATH/tinywga "$NPRE" $OUTPATH/${NPRE}_CaCo.xls $OUTPATH/${NPRE}_CaCo_log.txt $OUTPATH $OUTPATH/${NPRE}_CaCo_topTable.gff
# rgCaCo.py '$i.extra_files_path/$i.metadata.base_name' "$name"  '$out_file1' '$logf' '$logf.files_path' '$gffout'
;;

'rgQQ')
TOOL="rgQQ"
echo "now doing $TOOL"
NPRE=${TOOL}test1
OUTPATH=$NORMALOROOT
CL="python $TOOLPATH/$TOOL.py "$INPATH/tinywga.pphe" "$NPRE" 1 3 $OUTPATH/$NPRE.pdf 8 10 "false" 1 $OUTPATH"
echo "running $TOOL using $CL"
python $TOOLPATH/$TOOL.py "$INPATH/tinywga.pphe" "$NPRE" 1 3 $OUTPATH/$NPRE.pdf 8 10 "false" 1 $OUTPATH
# rgQQ.py "$input1" "$name" $sample "$cols" $allqq $height $width $log $allqq.id $__new_file_path__ 
;;
esac
