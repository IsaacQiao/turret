cmake_minimum_required(VERSION 2.8)
project(facial_rec)
SET(COMPILE_DEFINITIONS -Werror)
#OPENCV
find_package( OpenCV REQUIRED )
ocv_include_directories(/home/pi/opencv-3.1.0/include)
ocv_include_modules_recurse(${OPENCV_CPP_SAMPLES_REQUIRED_DEPS})
add_executable( facial_rec facial_rec.cpp)
target_link_libraries( facial_rec ${OpenCV_LIBS} )