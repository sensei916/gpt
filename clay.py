import bpy, os
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.8, 0.8, 0.8)
sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.show_shadows = True
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.display.render_aa = '8'
import sys; sys.path.insert(0, os.getcwd()); from shots import SHOTS
sc.timeline_markers.clear()
for n, c, f in SHOTS:
    sc.frame_set(f); sc.camera = bpy.data.objects[c]
    sc.render.filepath = os.environ.get('OUT', '.') + f'/clay_{n}.png'
    bpy.ops.render.render(write_still=True)
    print('CLAY', n)
