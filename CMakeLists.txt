cmake_minimum_required(VERSION 2.8.9)

project(PathRecorder)

#-----------------------------------------------------------------------------
set(EXTENSION_NAME PathRecorder)
set(EXTENSION_HOMEPAGE "")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Alireza Mehrtash (BWH, SPL)")
set(EXTENSION_DESCRIPTION "This is a module to record the points from a tracker connected to Slicer with OpenIGTLink. It gets the positions of the points from the transform node and record them in the form of markup fiducials.")
set(EXTENSION_ICON_URL "")
set(EXTENSION_SCREENSHOT_URL "")

set(EXTENSION_MAJOR_VERSION "1" )
set(EXTENSION_MINOR_VERSION "0" )
set(EXTENSION_PATCH_VERSION "" )
set(EXTENSION_STATUS "Experimental")

#-----------------------------------------------------------------------------
if(NOT Slicer_SOURCE_DIR)
  find_package(Slicer REQUIRED)
  include(${Slicer_USE_FILE})
endif()

add_subdirectory(PathRecorder)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})