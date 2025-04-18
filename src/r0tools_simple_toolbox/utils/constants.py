# fmt: off
class CUSTOM_PROPERTIES_TYPES:
    OBJECT_DATA = "OBJECT DATA"
    MESH_DATA   = "MESH DATA"


class OBJECT_MODES:
    OBJECT        = "OBJECT"
    OBJECT_MODE   = "OBJECT_MODE"
    EDIT          = "EDIT"
    EDIT_MODE     = "EDIT_MODE"
    EDIT_MESH     = "EDIT_MESH"
    SCULPT        = "SCULPT"
    VERTEX_PAINT  = "VERTEX_PAINT"
    TEXTURE_PAINT = "TEXTURE_PAINT"
    WEIGHT_PAINT  = "WEIGHT_PAINT"


class OBJECT_TYPES:
    MESH         = "MESH"
    CURVE        = "CURVE"
    SURFACE      = "SURFACE"
    META         = "META"
    FONT         = "FONT"
    CURVES       = "CURVES"
    POINTCLOUD   = "POINTCLOUD"
    VOLUME       = "VOLUME"
    GPENCIL      = "GPENCIL"
    GREASEPENCIL = "GREASEPENCIL"
    ARMATURE     = "ARMATURE"
    LATTICE      = "LATTICE"
    EMPTY        = "EMPTY"
    LIGHT        = "LIGHT"
    LIGHT_PROBE  = "LIGHT_PROBE"
    CAMERA       = "CAMERA"
    SPEAKER      = "SPEAKER"


class AREA_TYPES:
    CLIP_EDITOR      = "CLIP_EDITOR"
    CONSOLE          = "CONSOLE"
    DOPESHEET_EDITOR = "DOPESHEET_EDITOR"
    FILE_BROWSER     = "FILE_BROWSER"
    GRAPH_EDITOR     = "GRAPH_EDITOR"
    IMAGE_EDITOR     = "IMAGE_EDITOR"
    INFO             = "INFO"
    NLA_EDITOR       = "NLA_EDITOR"
    NODE_EDITOR      = "NODE_EDITOR"
    OUTLINER         = "OUTLINER"
    PREFERENCES      = "PREFERENCES"
    PROPERTIES       = "PROPERTIES"
    SEQUENCE_EDITOR  = "SEQUENCE_EDITOR"
    SPREADSHEET      = "SPREADSHEET"
    TEXT_EDITOR      = "TEXT_EDITOR"
    TOPBAR           = "TOPBAR"
    VIEW_3D          = "VIEW_3D"


class DEPSGRAPH_ID_TYPES:
    ACTION          = "ACTION" 
    ARMATURE        = "ARMATURE" 
    BRUSH           = "BRUSH" 
    CACHEFILE       = "CACHEFILE"
    CAMERA          = "CAMERA" 
    COLLECTION      = "COLLECTION" 
    CURVE           = "CURVE" 
    CURVES          = "CURVES" 
    FONT            = "FONT" 
    GREASEPENCIL    = "GREASEPENCIL"
    GREASEPENCIL_V3 = "GREASEPENCIL_V3"
    IMAGE           = "IMAGE" 
    KEY             = "KEY" 
    LATTICE         = "LATTICE"
    LIBRARY         = "LIBRARY"
    LIGHT           = "LIGHT"
    LIGHT_PROBE     = "LIGHT_PROBE"
    LINESTYLE       = "LINESTYLE"
    MASK            = "MASK"
    MATERIAL        = "MATERIAL"
    MESH            = "MESH"
    META            = "META"
    MOVIECLIP       = "MOVIECLIP"
    NODETREE        = "NODETREE"
    OBJECT          = "OBJECT"
    PAINTCURVE      = "PAINTCURVE"
    PALETTE         = "PALETTE"
    PARTICLE        = "PARTICLE"
    POINTCLOUD      = "POINTCLOUD"
    SCENE           = "SCENE"
    SCREEN          = "SCREEN"
    SOUND           = "SOUND"
    SPEAKER         = "SPEAKER"
    TEXT            = "TEXT"
    TEXTURE         = "TEXTURE"
    VOLUME          = "VOLUME"
    WINDOWMANAGER   = "WINDOWMANAGER"
    WORKSPACE       = "WORKSPACE"
    WORLD           = "WORLD"


class COLLECTION_COLOURS:
    RED    = "COLOR_01"
    ORANGE = "COLOR_02"
    YELLOW = "COLOR_03"
    GREEN  = "COLOR_04"
    BLUE   = "COLOR_05"
    PURPLE = "COLOR_06"
    PINK   = "COLOR_07"
    BROWN  = "COLOR_08"

    @classmethod
    def values(cls):
        return [cls.RED, cls.ORANGE, cls.YELLOW, cls.GREEN, cls.BLUE, cls.PURPLE, cls.PINK, cls.BROWN]
# fmt: on
