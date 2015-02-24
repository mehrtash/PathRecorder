set(MODULE_NAME PathRecorder)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
    PathRecorder.py
  )

set(MODULE_PYTHON_RESOURCES
    PathRecorder.png
  )

slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS "${MODULE_PYTHON_SCRIPTS}"
  RESOURCES "${MODULE_PYTHON_RESOURCES}"
)