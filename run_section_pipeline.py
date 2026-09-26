"""
Universal Whiteboard Video Production Pipeline CLI
Run any documentary section end-to-end dynamically with a single command:
python run_section_pipeline.py --section sections/03_working_poor
"""
import sys
from production_engine.universal_section_pipeline import main

if __name__ == "__main__":
    main()
