from setuptools import Extension, setup
import os
import shlex
import sys

if sys.platform == "win32":
    EXTRA_COMPILE_ARGS = ["/std:c++20", "/O2"]
else:
    EXTRA_COMPILE_ARGS = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror"]

# CFLAGS/LDFLAGS are ignored when building extensions, so add those manually.
cflags = shlex.split(os.getenv("CFLAGS", ""))
ldflags = shlex.split(os.getenv("LDFLAGS", ""))

setup(
    ext_modules=[
        Extension(
            name="zamboni.crc",
            sources=["src/crc.cpp"],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
        Extension(
            name="zamboni.floatage",
            sources=["src/floatage.cpp"],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
        Extension(
            name="zamboni.ooz",
            sources=[
                "ooz/bitknit.cpp",
                "ooz/compr_entropy.cpp",
                "ooz/compr_kraken.cpp",
                "ooz/compr_leviathan.cpp",
                "ooz/compr_match_finder.cpp",
                "ooz/compr_mermaid.cpp",
                "ooz/compr_multiarray.cpp",
                "ooz/compr_tans.cpp",
                "ooz/compress.cpp",
                "ooz/kraken.cpp",
                "ooz/lzna.cpp",
                "ooz/stdafx.cpp",
                "src/ooz.cpp",
            ],
            include_dirs=["ooz"],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
        Extension(
            name="zamboni.prs",
            sources=[
                "src/prs.cpp",
                "src/prs_comp.cpp",
                "src/prs_decomp.cpp",
            ],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
    ]
)
