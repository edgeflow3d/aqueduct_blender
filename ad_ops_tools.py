import random

import bpy

from .ad_utils import *

from bpy.types import Operator

class AD_OT_material_quickapply(Operator):
    """ Pick and apply materials quickly """
    bl_idname = "ad.material_quickapply"
    bl_label = "Material QuickApply"
    bl_options = {'REGISTER', 'UNDO'}

    def __init__(self):
        self.material = None

    def execute(self, context):
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):

        # set pick cursor
        if self.material == None:
            context.window.cursor_set('EYEDROPPER')
            context.area.header_text_set("Pick a Material")
        else:
            options = "LMB: Apply Material | Shift+LMB: Apply to all Slots | Esc/RMB: Cancel"
            context.area.header_text_set("Applying Material: {} | {}".format(
                self.material.name,
                options
                ))
            context.window.cursor_set('PAINT_BRUSH')

        # allow navigation to happen
        # NOTHING is for 3D mouse passthrough
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NOTHING'}:
            return {'PASS_THROUGH'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # reset header area text
            context.area.header_text_set(None)
            context.window.cursor_set('DEFAULT')
            return {'CANCELLED'}

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':

            # pick mode
            if self.material == None:
                eval_obj, loc, norm, face_id = raycast_object(context, event)

                if eval_obj:
                    target = eval_obj.original
                    if len(target.material_slots) != 0:
                        matslot_index = get_matslot_from_faceid(eval_obj, face_id)
                        self.material = target.material_slots[matslot_index].material

                    return {'RUNNING_MODAL'}

            # apply mode
            else:
                eval_obj, loc, norm, face_id = raycast_object(context, event)
                # log("RAYCAST\nOBJ:{}\nLOC:{}\nN:{}\nFACE:{}\n".format(eval_obj, loc, norm, face_id))

                # if raycast was successful
                if eval_obj:
                    target = eval_obj.original

                    # deselect all / select target
                    for obj in context.selected_objects:
                        obj.select_set(False)

                    target.select_set(True)
                    context.view_layer.objects.active = target

                    # add matslot if there is none
                    if len(target.material_slots) == 0:
                        bpy.ops.object.material_slot_add()

                    # Case: Multiple material slots on the object
                    if len(target.material_slots) > 1:
                        # Case: apply to all slots
                        if event.shift:
                            for matslot in target.material_slots:
                                matslot.material = self.material

                        # Case: apply to slot to which the clicked face belongs
                        else:
                            matslot_index = get_matslot_from_faceid(eval_obj, face_id)
                            target.material_slots[matslot_index].material = self.material

                    # Case: One material slot on the object
                    if len(target.material_slots) == 1:
                        target.material_slots[0].material = self.material


                return {'RUNNING_MODAL'}

        return {'RUNNING_MODAL'}

class AD_OT_object_quickplace_old(Operator):
    bl_idname = "ad.object_quickplace"
    bl_label = "Object QuickPlace"
    bl_options = {'REGISTER', 'UNDO'}

    def get_offsets(self):
        self.pivot = get_center(self.ws_extents, self.axis_options[self.axis_index])

        self.object_offsets = []
        for i in range(len(self.start_locations)):
            self.object_offsets.append(self.start_locations[i] - self.pivot)

    def execute(self, context):
        self.objects = context.selected_objects

        self.axis_options = ['-Z', 'Z', '-Y', 'Y', '-X', 'X', 'CENTER']
        self.axis_index = 0

        if len(self.objects) != 0:

            self.start_locations = []
            self.start_rotations = []

            for obj in self.objects:
                self.start_locations.append(obj.location.copy())
                self.start_rotations.append(obj.rotation_euler.copy())

            self.ws_extents = get_ws_min_max(self.objects)

            # get offsets
            self.get_offsets()
            
            context.window_manager.modal_handler_add(self)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        else:
            return {'CANCELLED'}

    def modal(self, context, event):
        self.objects = context.selected_objects

        # allow navigation to happen
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE', 'NOTHING'}:
            return {'PASS_THROUGH'}

        if event.type in {'LEFT_CTRL', 'RIGHT_CTRL'} and event.value == 'RELEASE':
            for i, obj in enumerate(self.objects):
                obj.rotation_euler = self.start_rotations[i]

        if event.type == 'W' and event.value == 'PRESS':
            self.axis_index = (self.axis_index + 1) % 7
            self.get_offsets()

        if event.type in {'MOUSEMOVE', 'LEFT_CTRL', 'RIGHT_CTRL', 'W'}:
            self.objects = context.selected_objects
            eval_obj, loc, norm, face_id = raycast_object(context, event, excluded=self.objects)
            # log("RAYCAST\nOBJ:{}\nLOC:{}\nN:{}\nFACE:{}\n".format(eval_obj, loc, norm, face_id))

            location = Vector((0,0,0))
            normal = None
            if eval_obj:
                # object under cursor use hit location and surface normal
                location = loc
                # transform object space normal to worldspace
                normal = norm @ eval_obj.matrix_world.inverted()
            else:
                # no object under cursor, raycast onto plane at grid level
                loc_grid = raycast_plane(context, event)
                if loc_grid:
                    location = loc_grid

                # if event.ctrl:
                #     rotated_offsets = []
                #     rot = Vector((0,0,1)).rotation_difference(Vector((0,0,1)))
                #     for offset in self.object_offsets:
                #         rotated_offset = offset.copy()
                #         rotated_offset.rotate(rot)
                #         rotated_offsets.append(rotated_offset)


                #     for i, obj in enumerate(self.objects):
                #         obj.location = location + rotated_offsets[i]

                #     # set up vector of object to world z
                #     for i, obj in enumerate(self.objects):
                #         orient_to_vector(obj,
                #                 Vector((0,0,1)),
                #                 Vector((0,0,1)),
                #                 self.start_rotations[i]
                #                 )


            # if event.ctrl:
            #     if normal:
            #         # set location
            #         rotated_offsets = []
            #         rot = Vector((0,0,1)).rotation_difference(normal)
            #         for offset in self.object_offsets:
            #             rotated_offset = offset.copy()
            #             rotated_offset.rotate(rot)
            #             rotated_offsets.append(rotated_offset)


            #         for i, obj in enumerate(self.objects):
            #             obj.location = location + rotated_offsets[i]

            #     # set rotation
            #         for i, obj in enumerate(self.objects):
            #             orient_to_vector(obj,
            #                     normal,
            #                     Vector((0,0,1)),
            #                     self.start_rotations[i]
            #                     )
            # else:
            # set location
            for i, obj in enumerate(self.objects):
                obj.location = location + self.object_offsets[i]



        elif event.type == 'LEFTMOUSE':
            context.area.header_text_set(None)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            for i, obj in enumerate(self.objects):
                obj.location = self.start_locations[i]
                obj.rotation_euler = self.start_rotations[i]


            context.area.header_text_set(None)
            return {'CANCELLED'}

        context.area.header_text_set("QuickPlace | W: Change pivot position ({})".format(self.axis_options[self.axis_index]))


        return {'RUNNING_MODAL'}

class AD_OT_object_quickplace(Operator):
    """ Randomized object transform """
    bl_idname = "ad.object_quickplace"
    bl_label = "Object QuickPlace"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context ,event):
        self.axis = ('X', 'Y', 'Z')
        self.axis_index = 0
        self.start_mousepos = event.mouse_x
        self.trans_offset = 0
        self.randomness = 0

        if len(context.selected_objects) != 0:
            self.objects = context.selected_objects

            # get starting position for all objects
            # set random values for each object
            self.start_locations = []
            self.random_values = []
            for obj in self.objects:
                self.start_locations.append(obj.location.copy())
                self.random_values.append((random.random() - 0.5) * 2)

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}

    def modal(self, context, event):
        context.window.cursor_set('SCROLL_X')

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            for i, obj in enumerate(self.objects):
                obj.location = self.start_locations[i]
            context.window.cursor_set('DEFAULT')
            context.area.header_text_set(None)
            return {'CANCELLED'}

        elif event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
            if self.randomness != 10:
                self.randomness += 1
                self.transform_objects(context, event)

        elif event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
            if self.randomness != 0:
                self.randomness -= 1
                self.transform_objects(context, event)

        elif event.type == 'W' and event.value == 'PRESS':
            self.axis_index = (self.axis_index + 1) % 3
            for i, obj in enumerate(self.objects):
                obj.location = self.start_locations[i]

        elif event.type == 'MOUSEMOVE':
            self.transform_objects(context, event)

        elif event.type == 'LEFTMOUSE':
            context.window.cursor_set('DEFAULT')
            context.area.header_text_set(None)
            return {'FINISHED'}

        context.area.header_text_set("QuickPlace | Transform-Offset: {:.2f} | Randomness {:.1f} | E : Toggle Transform Axis ({})".format(
        self.trans_offset,
        self.randomness / 10,
        self.axis[self.axis_index]
        ))

        return {'RUNNING_MODAL'}

    def transform_objects(self, context, event):
        delta_x = event.mouse_x - self.start_mousepos
        self.trans_offset = delta_x * 0.01
        for i, obj in enumerate(self.objects):
            random_offset = lerp(1.0, self.random_values[i], self.randomness * 0.1)
            obj.location = self.start_locations[i]
            obj.location[self.axis_index] += self.trans_offset * random_offset

class AD_OT_object_quickrotate(Operator):
    """ Randomized object rotation """
    bl_idname = "ad.object_quickrotate"
    bl_label = "Object QuickRotate"
    bl_options = {'REGISTER', 'UNDO'}

    def invoke(self, context, event):
        self.axis = ('X', 'Y', 'Z')
        self.axis_index = 2
        self.start_mousepos = event.mouse_x
        self.rot_offset = 0
        self.randomness = 0

        if len(context.selected_objects) != 0:
            self.objects = context.selected_objects

            # get starting rotations for all objects
            # set random values for each object
            self.start_rotations = []
            self.random_values = []
            for obj in self.objects:
                self.start_rotations.append(obj.rotation_euler.copy())
                self.random_values.append((random.random() - 0.5) * 2)


            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}


    def modal(self, context, event):
        context.window.cursor_set('SCROLL_X')

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            for i, obj in enumerate(self.objects):
                obj.rotation_euler = self.start_rotations[i]
            context.window.cursor_set('DEFAULT')
            context.area.header_text_set(None)
            return {'CANCELLED'}

        elif event.type == 'WHEELUPMOUSE' and event.value == 'PRESS':
            if self.randomness != 10:
                self.randomness += 1
                self.rotate_objects(context, event)

        elif event.type == 'WHEELDOWNMOUSE' and event.value == 'PRESS':
            if self.randomness != 0:
                self.randomness -= 1
                self.rotate_objects(context, event)

        elif event.type == 'E' and event.value == 'PRESS':
            self.axis_index = (self.axis_index + 1) % 3
            for i, obj in enumerate(self.objects):
                obj.rotation_euler = self.start_rotations[i]


        elif event.type == 'MOUSEMOVE':
            self.rotate_objects(context, event)

        elif event.type == 'LEFTMOUSE':
            context.window.cursor_set('DEFAULT')
            context.area.header_text_set(None)
            return {'FINISHED'}

        context.area.header_text_set("QuickRotate | Rotation-Offset: {:.2f} | Randomness: {:.1f} | E: Toggle Rotation Axis ({})".format(
            math.degrees(self.rot_offset),
            self.randomness / 10,
            self.axis[self.axis_index]
            ))

        return {'RUNNING_MODAL'}

    def rotate_objects(self, context, event):
            delta_x = event.mouse_x - self.start_mousepos
            self.rot_offset = delta_x * 0.01
            for i, obj in enumerate(self.objects):
                random_offset = lerp(1.0, self.random_values[i], self.randomness * 0.1)
                obj.rotation_euler = self.start_rotations[i]
                obj.rotation_euler.rotate_axis(self.axis[self.axis_index], (self.rot_offset * random_offset))

                # if self.world:
                    # if self.axis[self.axis_index] == 'X':
                    #     obj.rotation_euler.x = self.start_rotations[i].x + (self.rot_offset * random_offset)
                    # if self.axis[self.axis_index] == 'Y':
                    #     obj.rotation_euler.y = self.start_rotations[i].y + (self.rot_offset * random_offset)
                    # if self.axis[self.axis_index] == 'Z':
                    #     obj.rotation_euler.z = self.start_rotations[i].z + (self.rot_offset * random_offset)

classes = (
    AD_OT_material_quickapply,
    AD_OT_object_quickplace,
    AD_OT_object_quickrotate,
        )

register, unregister = bpy.utils.register_classes_factory(classes)
