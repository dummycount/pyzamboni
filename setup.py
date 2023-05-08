from setuptools import Extension, setup
import sys

if sys.platform == "win32":
    EXTRA_COMPILE_ARGS = ["/std:c++20", "/O2"]
else:
    EXTRA_COMPILE_ARGS = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror"]

setup(
    ext_modules=[
        Extension(
            name="zamboni.floatage",
            sources=["zamboni/floatage.cpp"],
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
                "zamboni/ooz.cpp",
            ],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
        Extension(
            name="zamboni.prs",
            sources=["zamboni/prs.cpp"],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
    ]
)
