import os
import sys

# insert *this* galaxy before all others on sys.path
sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)))

from galaxy.job_execution.container_monitor import main

if __name__ == "__main__":
    main()
