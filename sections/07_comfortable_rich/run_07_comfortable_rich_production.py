import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
ROOT_DIR = r"E:\image_to_animate"
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import run_07_production

if __name__ == "__main__":
    run_07_production.run()
