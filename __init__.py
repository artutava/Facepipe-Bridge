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
import os
from bpy_extras.io_utils import ImportHelper
from bpy.types import Operator

def read_csv_file(filepath):
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        data = [row for row in reader]
    return data

def calculate_average_fps(filepath):
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        fps_values = []
        for row in reader:
            try:
                fps = float(row[-1])  # Assuming FPS values are in the last column
                fps_values.append(fps)
            except ValueError:
                continue
        
        if fps_values:
            average_fps = sum(fps_values) / len(fps_values)
            return average_fps
        else:
            return None

def get_csv_filename(filepath):
    """Extract the base name of the CSV file without its extension."""
    base = os.path.basename(filepath)
    return os.path.splitext(base)[0]

def format_fps(fps):
    """Format FPS as an integer if it's a whole number, otherwise as a float with 2 decimal places."""
    return f"{int(fps)}" if fps.is_integer() else f"{fps:.2f}"

def create_shape_keys(obj, shape_key_names):
    basis = obj.shape_key_add(name="Basis")
    for name in shape_key_names:
        if name in ["jawLeft", "jawRight", "mouthLeft", "mouthRight"]:
            obj.shape_key_add(name=name)
        else:
            modified_name = name.replace("Left", "_L").replace("Right", "_R")
            obj.shape_key_add(name=modified_name)

def create_shape_key_action(obj, frame_data, csv_filename, average_fps):
    shape_key_names = frame_data[0]
    modified_shape_key_names = []

    for name in shape_key_names:
        if name in ["jawLeft", "jawRight", "mouthLeft", "mouthRight"]:
            modified_shape_key_names.append(name)
        else:
            modified_name = name.replace("Left", "_L").replace("Right", "_R")
            modified_shape_key_names.append(modified_name)
    
    create_shape_keys(obj, modified_shape_key_names)

    if not obj.animation_data:
        obj.animation_data_create()

    action_name = f"{csv_filename}_{format_fps(average_fps)}"
    action = bpy.data.actions.new(name=action_name)
    action.use_fake_user = True
    obj.animation_data.action = action

    for i, modified_shape_key_name in enumerate(modified_shape_key_names):
        for j, row in enumerate(frame_data[1:]):
            frame = j + 1
            value = float(row[i])

            shape_key = obj.data.shape_keys.key_blocks[modified_shape_key_name]
            shape_key.value = value
            shape_key.keyframe_insert(data_path='value', frame=frame)

def bake_action_to_scene_fps(action, average_fps, scene_fps, csv_filename):
    action_baked = action.copy()
    action_baked.name = f"{csv_filename}_{format_fps(scene_fps)}"
    
    # The scale factor adjusts the frame index from the average FPS to the scene FPS
    scale_factor = scene_fps / average_fps
    
    for fcurve in action_baked.fcurves:
        for keyframe in fcurve.keyframe_points:
            # Correctly scale the keyframe's frame number to adjust to the new FPS
            keyframe.co.x = keyframe.co.x * scale_factor
            keyframe.handle_left.x = keyframe.handle_left.x * scale_factor
            keyframe.handle_right.x = keyframe.handle_right.x * scale_factor

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

    def execute(self, context):
        average_fps = calculate_average_fps(self.filepath)
        if average_fps is None:
            self.report({'ERROR'}, "No valid FPS values found in CSV.")
            return {'CANCELLED'}

        csv_filename = get_csv_filename(self.filepath)
        frame_data = read_csv_file(self.filepath)
        bpy.ops.mesh.primitive_cube_add()
        temp_cube = context.active_object
        temp_cube.name = "Temp_Cube"
        create_shape_key_action(temp_cube, frame_data, csv_filename, average_fps)

        scene_fps = context.scene.render.fps / context.scene.render.fps_base
        baked_action = bake_action_to_scene_fps(temp_cube.data.shape_keys.animation_data.action, average_fps, scene_fps, csv_filename)
        temp_cube.data.shape_keys.animation_data.action = baked_action

        bpy.ops.object.select_all(action='DESELECT')
        temp_cube.select_set(True)
        bpy.ops.object.delete()

        return {'FINISHED'}

def menu_func_import(self, context):
    self.layout.operator(CSV_IMPORT_OT_shape_key.bl_idname, text="Facepipe: Import CSV Shape Key Action (.csv)")

def register():
    bpy.utils.register_class(CSV_IMPORT_OT_shape_key)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(CSV_IMPORT_OT_shape_key)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
