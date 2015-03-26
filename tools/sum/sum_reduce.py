#!/usr/bin/python
import sys;
import time;

if(len(sys.argv) < 3):
  sys.stderr.write("Needs 2 arguments : <input_vector_file> <output_filename>\n");
  sys.exit(-1);

fptrS=open(sys.argv[1], "r");
fptrO=open(sys.argv[2],"w");

if(len(sys.argv) >= 4):
  print("Num threads "+sys.argv[3]);
  if(len(sys.argv) >= 5):
    print("Hostname "+sys.argv[4]);

sum=0;
for line in fptrS:
  line = line.rstrip();
  val = int(line);
  sum += val;

fptrO.write("%d\n"%(sum));

time.sleep(20);


fptrO.close();
fptrS.close();

