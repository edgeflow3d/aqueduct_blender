import os
import subprocess
import time
import math

import bpy
from bpy_extras import view3d_utils
import bmesh

from mathutils import Vector
from mathutils import Matrix
import mathutils

def log(msg):
    t = time.localtime()
    current_time = time.strftime("%H:%M", t)
    print("<Aqueduct Addon {}> {}".format(current_time, (msg)))

def lerp(start, end, t):
    return start * (1 - t) + end * t

def raycast_object(context, event, excluded=[]):
    """Run this function on left mouse, execute the ray cast"""
    # get the context arguments
    scene = context.scene
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y

    # is none if we somehow are not getting view3d as region
    # just fail the raycast
    if rv3d == None:
        return None, None, None, None

    # get the ray from the viewport and mouse
    view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    ray_target = ray_origin + view_vector

    def visible_objects_and_duplis():
        """Loop over (object, matrix) pairs (mesh only)"""

        depsgraph = context.evaluated_depsgraph_get()

        # get the evaluated object for each excluded object
        excluded_eval_objs = []
        for obj in excluded:
            excluded_eval_objs.append(obj.evaluated_get(depsgraph))

        for dup in depsgraph.object_instances:
            if dup.is_instance:  # Real dupli instance
                obj = dup.instance_object
                yield (obj, dup.matrix_world.copy())
            else:  # Usual object
                obj = dup.object
                if obj not in excluded_eval_objs:
                    yield (obj, obj.matrix_world.copy())



    def obj_ray_cast(obj, matrix):
        """Wrapper for ray casting that moves the ray into object space"""

        # get the ray relative to the object
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv @ ray_origin
        ray_target_obj = matrix_inv @ ray_target
        ray_direction_obj = ray_target_obj - ray_origin_obj

        # cast the ray
        success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

        if success:
            return location, normal, face_index
        else:
            return None, None, None

    # cast rays and find the closest object
    best_length_squared = -1.0
    best_obj = None
    world_loc = (0, 0, 0)
    hit_normal = (0, 0, 0)
    face_id = None

    for obj, matrix in visible_objects_and_duplis():
        if obj.type == 'MESH':
            hit, normal, face_index = obj_ray_cast(obj, matrix)
            if hit is not None:
                hit_world = matrix @ hit
                length_squared = (hit_world - ray_origin).length_squared
                if best_obj is None or length_squared < best_length_squared:
                    best_length_squared = length_squared
                    best_obj = obj
                    world_loc = hit_world
                    hit_normal = normal
                    face_id = face_index

    return best_obj, world_loc, hit_normal, face_id
    # now we have the object under the mouse cursor,
    # we could do lots of stuff but for the example just select.
    # if best_obj is not None:
        # for selection etc. we need the original object,
        # evaluated objects are not in viewlayer
        # best_original = best_obj.original
        # best_original.select_set(True)
        # context.view_layer.objects.active = best_original

def raycast_plane(context, event):
    viewport_region = context.region
    viewport_region_data = context.space_data.region_3d
    viewport_matrix = viewport_region_data.view_matrix.inverted()

    # Shooting a ray from the camera, through the mouse cursor towards the grid with length 100000
    # if the camera is more than 10000 units away from the grid it won't detect a hit
    ray_start = viewport_matrix.to_translation()
    ray_depth = viewport_matrix @ Vector((0,0,-10000))

    # Get the 3D vector position of the mouse
    ray_end = view3d_utils.region_2d_to_location_3d(
            viewport_region,
            viewport_region_data,
            (event.mouse_region_x, event.mouse_region_y),
            ray_depth
            )

    # 3 Points to build a plane from
    point_1 = Vector((0,0,0))
    point_2 = Vector((0,1,0))
    point_3 = Vector((1,0,0))

    # Create a 3D position on the grid under the mouse using the grid plane points
    # and the ray cast from the camera
    position_on_grid = mathutils.geometry.intersect_ray_tri(
            point_1,
            point_2,
            point_3,
            ray_end,
            ray_start,
            False)

    return position_on_grid

def get_matslot_from_faceid(obj, face_id):
    # create empty bmesh
    bm = bmesh.new()
    # populate with meshdata
    bm.from_mesh(obj.data)
    # update face indices lookuptable
    bm.faces.ensure_lookup_table()
    # get matslot
    matslot_index = bm.faces[face_id].material_index
    # delete bmesh
    bm.free()

    return matslot_index

def orient_to_vector(obj, vector, axis, rotation_offset):
    # axis inverted
    # axis_inv = axis.copy()
    # axis_inv.negate()
    # vector_inv = vector.copy()
    # vector_inv.negate()

    # quaternion rotation difference for axis and inverted axis
    # quat_diff_pos = axis.rotation_difference(vector)
    # quat_diff_neg = axis.rotation_difference(vector_inv)
    # try negating components of quaternion to flip the object
    # log(quat_diff_neg)
    # quat_diff_neg.w *= -1
    # quat_diff_neg.x *= -1
    # quat_diff_neg.y *= -1
    # log(quat_diff_neg)

    # if vector.z > 0:
    #     rot_difference = quat_diff_pos
    # else:
    #     rot_difference = quat_diff_neg


    # Quaternion rotation difference
    # between the vector and the objects up axis
    rot_difference = axis.rotation_difference(vector)

    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rot_difference
    obj.rotation_mode = 'XYZ'

    # if vector.z < 0:
    #     obj.rotation_euler.rotate_axis('Y', math.radians(180))
    #     obj.rotation_euler.rotate_axis('Z', math.radians(180))

def orient_to_vector_track(obj, vector, track, up):
    rot_difference = vector.to_track_quat(track, up)

    obj.rotation_euler = rot_difference.to_euler()

def get_ws_extents(obj):
    """ calculates bounding box in worldspace
        returns a tuple of mathutils.Vectors

        point order in bound box X|Y|Z|Corner
        Left/Right | Front/Back | Top/Bottom | Corner

        LeftFrontBottomCorner   => LFBC
        LeftFrontTopCorner      => LFTC
        LeftBackTopCorner       => LBTC
        LeftBackBottomCorner    => LBBC
        RightFrontBottomCorner  => RFBC
        RightFrontTopCorner     => RFTC
        RightBackTopCorner      => RBTC
        RightBackBottomCorner   => RBBC
    """

    ws_extents = []
    for coords in obj.bound_box:
        ws_extents.append(obj.matrix_world @ Vector(coords))

    return tuple(ws_extents)

def get_ws_min_max(objects):
    """ gets the min and max bounds of a group of objects
        in worldspace
        returns a tuple of 2 mathutils.Vector
    """

    # get all ws bounding boxes
    ws_extents = []
    for obj in objects:
        ws_extents.append(get_ws_extents(obj))

    # get min and maximum
    ws_min = ws_extents[0][0].copy()
    ws_max = ws_extents[0][1].copy()
    for extents in ws_extents:
        for vec in extents:
            for i, val in enumerate(vec):
                if val < ws_min[i]:
                    ws_min[i] = val

            for i, val in enumerate(vec):
                if val > ws_max[i]:
                    ws_max[i] = val

    return (ws_min, ws_max)

def get_center(extents, axis):
    """ calculates the center of the chosen bounding box side
        return the location in worldspace as mathutils.Vector
    """

    ws_min, ws_max = extents

    # Left/Right|Front/Back|Top/Bottom Corner
    LFBC = ws_min
    LFTC = Vector((ws_min[0], ws_min[1], ws_max[2])) 
    LBTC = Vector((ws_min[0], ws_max[1], ws_max[2]))
    LBBC = Vector((ws_min[0], ws_max[1], ws_min[2]))
    RFBC = Vector((ws_max[0], ws_min[1], ws_min[2]))
    RFTC = Vector((ws_max[0], ws_min[1], ws_max[2]))
    RBTC = ws_max
    RBBC = Vector((ws_max[0], ws_max[1], ws_min[2]))

    if axis == '-X':
        x_min = LFBC - (LFBC - LBTC)/2
        return x_min
    if axis == 'X':
        x_max   = RFBC - (RFBC - RBTC)/2
        return x_max
    if axis == '-Y':
        y_min   = LFBC - (LFBC - RFTC)/2
        return y_min
    if axis == 'Y':
        y_max   = LBBC - (LBBC - RBTC)/2
        return y_max
    if axis == '-Z':
        z_min   = LFBC - (LFBC - RBBC)/2
        return z_min
    if axis == 'Z':
        z_max   = LFTC - (LFTC - RBTC)/2
        return z_max
    if axis == 'CENTER':
        center  = LFBC - (LFBC - RBTC)/2
        return center

    return False

def background_worker(scriptpath, filepath=""):
    """ starts a headless blender instance

        filepath: blendfile to open
        scriptpath: pythonscript to pass to the instance
    """
    import shlex


    if filepath != "":
        command = '"{}" "{}" -b -P "{}" --addons {}'.format(
                bpy.app.binary_path,
                filepath,
                scriptpath,
                __package__
                )

    else:
        command = '"{}" -b -P "{}" --addons {}'.format(
                bpy.app.binary_path,
                scriptpath,
                __package__
                )

    command = shlex.split(command)

    log("=============== Background Worker ===============")
    # subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    subprocess.call(command)
    log("=============== Background Worker ===============")
