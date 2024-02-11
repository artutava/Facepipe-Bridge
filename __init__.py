bl_info = {
    "name": "Facepipe Bridge: Import CSV as Shape Key Action",
    "blender": (2, 93, 0),
    "category": "Import-Export",
    "author": "Artur Tavares",
    "description": "Imports Facepipe CSV files as shape key animations for mesh objects",
    "warning": "Should be used with Facepipe, as csv structure differs from ARKIT, ARKIT support is planned in the future",
    "doc_url": "https://facepipe.sircrux.com",
}

import bpy
import csv
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

def read_csv_file(filepath):
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        data = [row for row in reader]
    return data

def create_shape_keys(obj, shape_key_names):
    # Adds a Basis shape key first, which is needed as a base for other shape keys
    basis = obj.shape_key_add(name="Basis")

    # Modify each shape key name according to the specified rules
    for name in shape_key_names:
        # Check for exceptions where replacements should not occur
        if name in ["jawLeft", "jawRight", "mouthLeft", "mouthRight"]:
            obj.shape_key_add(name=name)
        else:
            # Replace "Left" with "_L" and "Right" with "_R" for other names
            modified_name = name.replace("Left", "_L").replace("Right", "_R")
            obj.shape_key_add(name=modified_name)

def create_shape_key_action(obj, frame_data):
    shape_key_names = frame_data[0]
    create_shape_keys(obj, shape_key_names)

    if not obj.animation_data:
        obj.animation_data_create()

    action = bpy.data.actions.new(name="CSV_Shape_Key_Action")
    action.use_fake_user = True
    obj.animation_data.action = action

    for i, shape_key_name in enumerate(shape_key_names):
        for j, row in enumerate(frame_data[1:]):
            frame = j + 1
            value = float(row[i])

            shape_key = obj.data.shape_keys.key_blocks[shape_key_name]
            shape_key.value = value
            shape_key.keyframe_insert(data_path='value', frame=frame)

def bake_action_to_scene_fps(action, original_fps, scene_fps):
    action_baked = action.copy()
    action_baked.name = action.name + "_baked"
    
    for fcurve in action_baked.fcurves:
        keyframe_points = fcurve.keyframe_points
        for keyframe in keyframe_points:
            keyframe.co.x = keyframe.co.x * (scene_fps / original_fps)
            keyframe.handle_left.x = keyframe.handle_left.x * (scene_fps / original_fps)
            keyframe.handle_right.x = keyframe.handle_right.x * (scene_fps / original_fps)

    action_baked.use_fake_user = True
    return action_baked

class CSV_IMPORT_OT_shape_key(Operator, ImportHelper):
    bl_idname = "import_scene.csv_shape_key_action"
    bl_label = "Import CSV as Shape Key Action"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: bpy.props.StringProperty(
        default="*.csv",
        options={'HIDDEN'},
        maxlen=255,
    )

    scene_fps: bpy.props.BoolProperty(
        name="Scene FPS",
        description="Bake action to the current scene FPS",
        default=False,
    )

    original_fps: bpy.props.IntProperty(
        name="Original FPS",
        description="FPS of the original animation",
        default=50,
        min=1,
        max=240
    )

    def execute(self, context):
        # Create a temporary cube and set it as the active object
        bpy.ops.mesh.primitive_cube_add()
        temp_cube = context.active_object
        temp_cube.name = "Temp_Cube"

        frame_data = read_csv_file(self.filepath)
        create_shape_key_action(temp_cube, frame_data)

        # Bake action to scene FPS if the "Scene FPS" checkbox is checked
        if self.scene_fps:
            scene_fps = context.scene.render.fps / context.scene.render.fps_base
            baked_action = bake_action_to_scene_fps(temp_cube.data.shape_keys.animation_data.action, self.original_fps, scene_fps)
            temp_cube.data.shape_keys.animation_data.action = baked_action

        # Delete the temporary cube
        bpy.ops.object.select_all(action='DESELECT')
        temp_cube.select_set(True)
        bpy.ops.object.delete()

        return {'FINISHED'}
        
def menu_func_import(self, context):
    self.layout.operator(CSV_IMPORT_OT_shape_key.bl_idname, text="Facepipe CSV Shape Key Import (.csv)")

def register():
    bpy.utils.register_class(CSV_IMPORT_OT_shape_key)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(CSV_IMPORT_OT_shape_key)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
