import os
import shutil

from .ad_utils import log

import bpy

from bpy.types import Operator, PropertyGroup, OperatorFileListElement
from bpy.props import CollectionProperty, StringProperty, EnumProperty

from bpy_extras.io_utils import ExportHelper

class AD_OT_Filelist_Add(Operator, ExportHelper):
    """ Adds selected files to the Filelist """
    bl_idname = "ad.filelist_add"
    bl_label = "Adds the selected files to the list"

    files : CollectionProperty(type=OperatorFileListElement)
    directory : StringProperty(subtype='DIR_PATH')

    filename_ext = ".blend"
    filter_glob : StringProperty(
            default='*.blend',
            options={'HIDDEN'},
            maxlen=255
            )

    mode : EnumProperty(name="Mode",
            items=[
                ('OBJECT', "Object", 'OBJECT_DATA', 0),
                ('MATERIAL', "Material", 'MATERIAL', 1)
                ])

    def invoke(self, context, event):
        prefs = context.preferences.addons[__package__].preferences
        if prefs.AD_library_path != "":
            self.filepath = prefs.AD_library_path + os.sep

        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        _list = prefs.AD_batchrender_list

        for file_elem in self.files:
            filepath = os.path.join(self.directory, file_elem.name)
            if os.path.isfile(filepath):
                entry = _list.add()
                entry.mode = self.mode
                entry.filepath = filepath

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.prop(self, 'mode', text="File content")

class AD_OT_Filelist_Render(Operator):
    """ Renders the batch render filelist """
    bl_idname = "ad.filelist_render"
    bl_label = "Render the Batch render list"

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.AD_batchrender_list

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        _list = prefs.AD_batchrender_list

        # render each file
        for entry in _list:
            # check if the file still exists
            if os.path.exists(entry.filepath):
                bpy.ops.ad.render_thumbnail(filepath=entry.filepath, mode=entry.mode)

        # clear the list
        # _list.clear()

        return {'FINISHED'}

class AD_OT_Filelist_Package(Operator):
    """ Package the batch render filelist """
    bl_idname = "ad.filelist_package"
    bl_label = "Package the Batch render list"

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.AD_batchrender_list

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        _list = prefs.AD_batchrender_list

        context.window.cursor_set('WAIT')
        # render each file
        for entry in _list:
            # check if the file still exists
            if os.path.exists(entry.filepath):
                bpy.ops.ad.package_images_batch(filepath=entry.filepath)


        context.window.cursor_set('DEFAULT')
        return {'FINISHED'}

class AD_OT_Filelist_Relocate(Operator):
    """ Moves the files in the list to a new location on disk """
    bl_idname = "ad.filelist_relocate"
    bl_label = "Move the files in the list to a new location on disk"

    filepath : StringProperty(name="Filepath", subtype='DIR_PATH')

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.AD_batchrender_list

    def invoke(self, context, event):
        prefs = context.preferences.addons[__package__].preferences
        self.filepath = prefs.AD_library_path + os.sep
        wm = context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        _list = prefs.AD_batchrender_list

        context.window.cursor_set('WAIT')
        # move/resave each file
        for entry in _list:
            source = entry.filepath
            destination = os.path.join(
                    self.filepath,
                    os.path.basename(source))

            if os.path.exists(source):
                bpy.ops.ad.relocate_file(source=source, destination=destination)

            # proceed only if relocation of file was successfull
            if os.path.exists(destination):
                # delete old file
                if os.path.exists(source):
                    os.remove(source)

                # move existing thumbnails to the new location
                extensions = [".jpg", ".png", ".JPG", ".PNG"]
                for extension in extensions:
                    thumbnail_sourcepath = os.path.splitext(source)[0] + extension
                    
                    if os.path.exists(thumbnail_sourcepath):
                        thumbnail_destinationpath = os.path.splitext(destination)[0] + extension
                        shutil.move(thumbnail_sourcepath, thumbnail_destinationpath)

        context.window.cursor_set('DEFAULT')
        return {'FINISHED'}

class AD_OT_Filelist_Clear(Operator):
    """ Empties the batch render filelist """
    bl_idname = "ad.filelist_clear"
    bl_label = "Clear the Batch render list"

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.AD_batchrender_list

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        _list = prefs.AD_batchrender_list
        _list.clear()
        bpy.ops.wm.save_userpref()

        return {'FINISHED'}

class AD_OT_Filelist_Remove(Operator):
    """ Removes an item from the filelist """

    bl_idname = "ad.filelist_remove"
    bl_label = "Remove item from the Batch render list"

    @classmethod
    def poll(cls, context):
        return context.preferences.addons[__package__].preferences.AD_batchrender_list

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        index = prefs.AD_batchrender_list_index
        _list = prefs.AD_batchrender_list
        _list.remove(index)
        prefs.AD_batchrender_list_index = min(max(0, index - 1), len(_list) - 1)
        bpy.ops.wm.save_userpref()

        return {'FINISHED'}

classes = (
        AD_OT_Filelist_Add,
        AD_OT_Filelist_Remove,
        AD_OT_Filelist_Relocate,
        AD_OT_Filelist_Render,
        AD_OT_Filelist_Package,
        AD_OT_Filelist_Clear,
        )

register, unregister = bpy.utils.register_classes_factory(classes)
