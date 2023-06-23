"""
Module entry point
"""

import cProfile
import pstats
from .cli import main


if __name__ == "__main__":
    with cProfile.Profile() as pr:
        main()

        ps = pstats.Stats(pr).sort_stats(pstats.SortKey.CUMULATIVE)
        ps.print_stats(20)
