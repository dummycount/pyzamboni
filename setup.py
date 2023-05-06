from setuptools import Extension, setup
import sys

if sys.platform == "win32":
    EXTRA_COMPILE_ARGS = ["/std:c++20"]
else:
    EXTRA_COMPILE_ARGS = ["-std=c++20", "-Wall", "-Wextra", "-Werror"]

setup(
    ext_modules=[
        Extension(
            name="zamboni.floatage",
            sources=["zamboni/floatage.cpp"],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
        Extension(
            name="zamboni.prs",
            sources=["zamboni/prs.cpp"],
            extra_compile_args=EXTRA_COMPILE_ARGS,
        ),
    ]
)
