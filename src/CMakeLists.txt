add_executable(test test.cpp prs_comp.cpp prs_decomp.cpp)
target_link_libraries(test cxxopts ooz_static)