"""Draw.io style strings as constants.

Each constant is a semicolon-delimited style string that can be used
directly as the ``style`` attribute of an ``<mxCell>`` element.
"""

# -- Component diagram ------------------------------------------------
STYLE_MODULE_BOX = (
    "rounded=1;whiteSpace=wrap;html=1;"
    "fillColor=#dae8fc;strokeColor=#6c8ebf;fontStyle=1;"
)
STYLE_PACKAGE_BOUNDARY = (
    "swimlane;childLayout=stackLayout;horizontal=1;startSize=30;"
    "fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;"
)
STYLE_IMPORT_EDGE = (
    "endArrow=open;endFill=0;dashed=1;strokeColor=#999999;"
)
STYLE_DEPENDENCY_EDGE = (
    "endArrow=open;endFill=1;strokeColor=#333333;"
)

# -- State diagram -----------------------------------------------------
STYLE_STATE = (
    "rounded=1;whiteSpace=wrap;html=1;"
    "fillColor=#d5e8d4;strokeColor=#82b366;"
)
STYLE_STATE_INITIAL = (
    "ellipse;fillColor=#000000;strokeColor=#000000;"
)
STYLE_STATE_FINAL = (
    "ellipse;fillColor=#000000;strokeColor=#000000;"
    "shape=doubleCircle;"
)
STYLE_TRANSITION = (
    "endArrow=block;endFill=1;strokeColor=#333333;"
)
STYLE_TRANSITION_FAIL = (
    "endArrow=block;endFill=1;strokeColor=#b85450;dashed=1;"
)

# -- Use-case diagram --------------------------------------------------
STYLE_ACTOR = (
    "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;"
)
STYLE_USECASE = (
    "ellipse;whiteSpace=wrap;html=1;"
)
STYLE_SYSTEM_BOUNDARY = (
    "swimlane;childLayout=stackLayout;horizontal=1;startSize=30;"
    "fillColor=#ffffff;strokeColor=#000000;fontStyle=1;"
)
STYLE_ASSOCIATION = (
    "endArrow=none;"
)

# -- Root cells (required by Draw.io) -----------------------------------
STYLE_ROOT_CELL_0 = ""
STYLE_ROOT_CELL_1 = ""
