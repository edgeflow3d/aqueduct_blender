import os
import json

import bpy

from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, CollectionProperty, EnumProperty

from bpy_extras.io_utils import ExportHelper

from .ad_utils import *
from .ad_ops_utility import AD_TYPE_Resource

class Save_Resource_BaseClass:
    filename_ext = ".blend"
    filter_glob : StringProperty(
            default='*.blend',
            options={'HIDDEN'},
            maxlen=255
            )

    resource_list : CollectionProperty(type=AD_TYPE_Resource)
    render_thumbnail : BoolProperty(default=False)
    package_images: BoolProperty(default=False)
    split_into_files : BoolProperty(default=False)
    pivot_placement : EnumProperty(name="Pivot Placement",
            items=[
                ('-Z', "-Z", "bbox negative Z"),
                ('Z', "Z", "bbox positive Z"),
                ('-Y', "-Y", "bbox negative Y"),
                ('Y', "Y", "bbox positive Y"),
                ('-X', "-X", "bbox negative X"),
                ('X', "X", "bbox positive X"),
                ('CENTER', "Center", "bbox average center"),
                ])

    def draw(self, context):
        """ Draws the resource selection GUI """
        layout = self.layout
        row = layout.row()
        row.label(text="Resources to export:")
        box = layout.box()
        col = box.column(align=True)
        for entry in self.resource_list:
            row = col.row()
            row.prop(entry, 'selected', text=entry.name)

        row = layout.row()
        row.prop(self, 'render_thumbnail', text="Render thumbnail")
        row = layout.row()
        row.prop(self, 'package_images', text="Package and relink textures")
        row = layout.row()
        row.prop(self, 'split_into_files', text="Each asset in its own file")
        row = layout.row()
        row.label(text="Pivot Placement:")
        row = layout.row()
        row.prop(self, 'pivot_placement', text="")

class AD_OT_save_col_filedialog(Operator, ExportHelper, Save_Resource_BaseClass):
    """ Saves Collection to blendfile """
    bl_idname = "ad.save_collection_filedialog"
    bl_label = "Save Collection"

    def invoke(self, context, event):
        # GUARD CLAUSES

        # Case: No active object
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "No selected objects, please select objects")
            return {'CANCELLED'}

        # get collections from selected objects
        self.collections = []
        for obj in context.selected_objects:
            for col in obj.users_collection:
                if col.name not in self.collections and col.name != "Master Collection":
                    self.collections.append(col.name)

        # Case: Objects are not in any collection except the Master Collection
        if len(self.collections) == 0:
            self.report({'ERROR'}, "None of the selected objects are part of a collection")
            return {'CANCELLED'}

        # clear and populate the resource_list
        self.resource_list.clear()
        for col in self.collections:
            entry = self.resource_list.add()
            entry.name = col
            entry.selected = True

        # Set the default folder of the filebrowser dialog
        colname = self.resource_list[0].name.replace(".", "_")
        prefs = context.preferences.addons[__package__].preferences
        if prefs.AD_export_path == "":
            bpy.ops.wm.save_userpref()

            if prefs.AD_library_path == "":
                self.filepath = os.path.join(os.path.dirname(bpy.data.filepath), colname + ".blend")
            else:
                self.filepath = os.path.join(prefs.AD_library_path, colname + ".blend")
        else:
            self.filepath = os.path.join(prefs.AD_export_path, colname + ".blend")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        # Case: Output path doesn't exist
        self.filepath = os.path.abspath(self.filepath)
        output_folder = os.path.dirname(self.filepath)
        if os.path.exists(output_folder) == False:
            self.report({'ERROR'}, "The given output filepath doesn't exist")
            return {'CANCELLED'}

        # Set the current path as export path for further exports
        prefs = context.preferences.addons[__package__].preferences
        prefs.AD_export_path = output_folder

        # get the selected datablocks
        data_blocks = []
        for entry in self.resource_list:
            if entry.selected:
                data_blocks.append(entry.name)

        # Case: No datablocks selected
        if len(data_blocks) == 0:
            self.report({'ERROR'}, "No resources chosen for export")
            return {'CANCELLED'}

        if self.split_into_files:
            for block in data_blocks:
                # construct filepaths for asset
                filepath = os.path.join(os.path.dirname(self.filepath), block + ".blend")

                # construct single data_block 
                asset = [block,]

                # save out datablocks
                bpy.ops.ad.export_resource(
                        filepath=filepath,
                        mode='COLLECTION',
                        blocknames=json.dumps(asset),
                        pivot=self.pivot_placement,
                        package_images=self.package_images
                        )

                # render thumbnail
                if self.render_thumbnail:
                    bpy.ops.ad.render_thumbnail(filepath=filepath, mode='OBJECT')
                else:
                    _list = prefs.AD_batchrender_list
                    entry = _list.add()
                    entry.mode = 'OBJECT'
                    entry.filepath = filepath
        else:
            # Write out the selected resources to a library file in tmp folder
            bpy.ops.ad.export_resource(
                    filepath=self.filepath,
                    mode='COLLECTION',
                    blocknames=json.dumps(data_blocks),
                    pivot=self.pivot_placement,
                    package_images=self.package_images
                    )
            log("{} collection/s exported".format(len(data_blocks)))

            # Render thumbnail
            if self.render_thumbnail:
                bpy.ops.ad.render_thumbnail(filepath=self.filepath, mode='OBJECT')
            else:
                # add it to the batch render list
                _list = prefs.AD_batchrender_list
                entry = _list.add()
                entry.mode = 'OBJECT'
                entry.filepath = self.filepath

        return {'FINISHED'}

class AD_OT_save_obj_filedialog(Operator, ExportHelper, Save_Resource_BaseClass):
    """ Saves Object to blendfile """
    bl_idname = "ad.save_object_filedialog"
    bl_label = "Save Object"

    def invoke(self, context, event):
        # GUARD CLAUSES

        # Case: No active object
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "No selected objects, please select objects")
            return {'CANCELLED'}

        self.objects = context.selected_objects

        # clear and populate the resource_list
        self.resource_list.clear()
        for obj in self.objects:
            entry = self.resource_list.add()
            entry.name = obj.name
            entry.selected = True

        # Set the default folder of the filebrowser dialog
        objname = self.resource_list[0].name.replace(".", "_")
        prefs = context.preferences.addons[__package__].preferences
        if prefs.AD_export_path == "":
            bpy.ops.wm.save_userpref()

            if prefs.AD_library_path == "":
                self.filepath = os.path.join(os.path.dirname(bpy.data.filepath), objname + ".blend")
            else:
                self.filepath = os.path.join(prefs.AD_library_path, objname + ".blend")
        else:
            self.filepath = os.path.join(prefs.AD_export_path, objname + ".blend")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        # Case: Output path doesn't exist
        self.filepath = os.path.abspath(self.filepath)
        output_folder = os.path.dirname(self.filepath)
        if os.path.exists(output_folder) == False:
            self.report({'ERROR'}, "The given output filepath doesn't exist")
            return {'CANCELLED'}

        # Set the current path as export path for further exports
        prefs = context.preferences.addons[__package__].preferences
        prefs.AD_export_path = output_folder

        # get selected data datablocks
        data_blocks = []
        for entry in self.resource_list:
            if entry.selected:
                data_blocks.append(entry.name)

        # Case: No datablocks selected
        if len(data_blocks) == 0:
            self.report({'ERROR'}, "No resources chosen for export")
            return {'CANCELLED'}

        if self.split_into_files:
            for block in data_blocks:
                # construct filepaths for asset
                filepath = os.path.join(os.path.dirname(self.filepath), block + ".blend")

                # construct single data_block 
                asset = [block,]

                # save out datablocks
                bpy.ops.ad.export_resource(
                        filepath=filepath,
                        mode='OBJECT',
                        blocknames=json.dumps(asset),
                        pivot=self.pivot_placement,
                        package_images=self.package_images
                        )

                # render thumbnail
                if self.render_thumbnail:
                    bpy.ops.ad.render_thumbnail(filepath=filepath, mode='OBJECT')
                else:
                    _list = prefs.AD_batchrender_list
                    entry = _list.add()
                    entry.mode = 'OBJECT'
                    entry.filepath = filepath
        else:
            # Write out the selected resources to a library file in tmp folder
            bpy.ops.ad.export_resource(
                    filepath=self.filepath,
                    mode='OBJECT',
                    blocknames=json.dumps(data_blocks),
                    pivot=self.pivot_placement,
                    package_images=self.package_images
                    )

            log("{} object/s exported".format(len(data_blocks)))

            # Render Thumbnail
            if self.render_thumbnail:
                bpy.ops.ad.render_thumbnail(filepath=self.filepath, mode='OBJECT')
            else:
                # add it to the batch render list
                _list = prefs.AD_batchrender_list
                entry = _list.add()
                entry.mode = 'OBJECT'
                entry.filepath = self.filepath


        return {'FINISHED'}

class AD_OT_save_mat_filedialog(Operator, ExportHelper, Save_Resource_BaseClass):
    """ Saves Material to blendfile """
    bl_idname = "ad.save_material_filedialog"
    bl_label = "Save Material"

    def invoke(self, context, event):

        # GUARD CLAUSES

        # Case: No selected objects
        if len(context.selected_objects) == 0:
            self.report({'ERROR'}, "No selected objects, please select objects")
            return {'CANCELLED'}

        self.objects = context.selected_objects

        # clear and populate the resource_list
        self.resource_list.clear()
        for obj in self.objects:
            if len(obj.material_slots) != 0:
                for slot in obj.material_slots:
                    if slot.material:
                        if slot.material.name not in self.resource_list.keys():
                            entry = self.resource_list.add()
                            entry.name = slot.material.name
                            entry.selected = True


        # Case: No materials assigned
        if len(self.resource_list) == 0:
            self.report({'INFO'}, "The active object has no materials assigned")
            return {'CANCELLED'}

        # Set the default folder of the filebrowser dialog
        matname = self.resource_list[0].name.replace(".", "_")
        prefs = context.preferences.addons[__package__].preferences
        if prefs.AD_export_path == "":
            bpy.ops.wm.save_userpref() 

            if prefs.AD_library_path == "":
                self.filepath = os.path.join(os.path.dirname(bpy.data.filepath), matname + ".blend")
            else:
                self.filepath = os.path.join(prefs.AD_library_path, matname + ".blend")
        else:
            self.filepath = os.path.join(prefs.AD_export_path, matname + ".blend")

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        # Case: Output path doesn't exist
        self.filepath = os.path.abspath(self.filepath)
        output_folder = os.path.dirname(self.filepath)
        if os.path.exists(output_folder) == False:
            self.report({'ERROR'}, "The given output filepath doesn't exist")
            return {'CANCELLED'}

        # Set the current path as export path for further exports
        prefs = context.preferences.addons[__package__].preferences
        prefs.AD_export_path = output_folder

        # get selected data datablocks
        data_blocks = []
        for entry in self.resource_list:
            if entry.selected:
                data_blocks.append(entry.name)

        # Case: No datablocks selected
        if len(data_blocks) == 0:
            self.report({'ERROR'}, "No resources chosen for export")
            return {'CANCELLED'}

        if self.split_into_files:
            for block in data_blocks:
                # construct filepaths for asset
                filepath = os.path.join(os.path.dirname(self.filepath), block + ".blend")

                # construct single data_block 
                asset = [block,]

                # save out datablocks
                bpy.ops.ad.export_resource(
                        filepath=filepath,
                        mode='MATERIAL',
                        blocknames=json.dumps(asset),
                        package_images=self.package_images
                        )

                # render thumbnail
                if self.render_thumbnail:
                    bpy.ops.ad.render_thumbnail(filepath=filepath, mode='MATERIAL')
                else:
                    _list = prefs.AD_batchrender_list
                    entry = _list.add()
                    entry.mode = 'MATERIAL'
                    entry.filepath = filepath

        else:
            # # Write out the selected resources to a library file in tmp folder
            bpy.ops.ad.export_resource(
                    filepath=self.filepath,
                    mode='MATERIAL',
                    blocknames=json.dumps(data_blocks),
                    package_images=self.package_images
                    )
            log("{} material/s exported".format(len(data_blocks)))

            # render thumbnail
            if self.render_thumbnail:
                bpy.ops.ad.render_thumbnail(filepath=self.filepath, mode='MATERIAL')
            else:
                # add it to the batch render list
                _list = prefs.AD_batchrender_list
                entry = _list.add()
                entry.mode = 'MATERIAL'
                entry.filepath = self.filepath

        return {'FINISHED'}

    def draw(self, context):
        """ Draws the resource selection GUI """
        layout = self.layout
        row = layout.row()
        row.label(text="Resources to export:")
        box = layout.box()
        col = box.column(align=True)
        for entry in self.resource_list:
            row = col.row()
            row.prop(entry, 'selected', text=entry.name)

        row = layout.row()
        row.prop(self, 'render_thumbnail', text="Render thumbnail")
        row = layout.row()
        row.prop(self, 'package_images', text="Package and relink textures")
        row = layout.row()
        row.prop(self, 'split_into_files', text="Each asset in its own file")

classes = (
        AD_OT_save_obj_filedialog,
        AD_OT_save_col_filedialog,
        AD_OT_save_mat_filedialog
        )

register, unregister = bpy.utils.register_classes_factory(classes)
