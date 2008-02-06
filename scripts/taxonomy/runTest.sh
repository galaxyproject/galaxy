PYTHONPATH="../../lib:../../eggs:../../eggs/`../check_python_ucs.py`"
export PYTHONPATH
rm -f /tmp/taxTest.db
python tax1_NodeParser.py tax1_test_argv1.txt > tax2_test_argv1.txt
python tax2_Node2Name.py tax2_test_argv1.txt tax2_test_argv2.txt /tmp/taxTest.db
python tax3_gi2tax.py /tmp/taxTest.db tax3_test_argv2.txt
python tax.py /tmp/taxTest.db tax3_test_argv2.txt tax_out.txt -c 1
diff tax_out.txt tax_result.txt
