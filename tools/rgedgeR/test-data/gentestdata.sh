#!/bin/bash
# generate test data for rgGSEA
# ross lazarus June 2013 
# adjust gseajar_path !
GSEAJAR_PATH=/home/rlazarus/galaxy-central/tool_dependency_dir/gsea_jar/2.0.12/fubar/rg_gsea_test/8e291f464aa0/jars/gsea2-2.0.12.jar
python ../rgGSEA.py --input_tab "gsea_test_DGE.xls"  --adjpvalcol "5" --signcol "2" --idcol "1" --outhtml "gseatestout.html" --input_name "gsea_test" --setMax "500" --setMin "15" --nPerm "10" --plotTop "20" --gsea_jar "$GSEAJAR_PATH" --output_dir "gseatestout" --mode "Max_probe" 
--title "GSEA test" --builtin_gmt "gseatestdata.gmt"


