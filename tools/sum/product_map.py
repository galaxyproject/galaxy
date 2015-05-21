#!/usr/bin/python
import sys;
import time;

if(len(sys.argv) < 4):
  sys.stderr.write("Needs 3 arguments : <input_vector_file1> <input_vector_file2> <output_filename>\n");
  sys.exit(-1);

fptrA=open(sys.argv[1], "r");
fptrB=open(sys.argv[2], "r");
fptrP=open(sys.argv[3],"w");

for line in fptrA:
  line = line.rstrip();
  val1 = int(line);
  line = fptrB.readline();
  if(line == ""):
    break;
  line = line.rstrip();
  val2 = int(line);
  fptrP.write("%d\n"%(val1*val2));

time.sleep(10);

fptrA.close();
fptrB.close();
fptrP.close();

