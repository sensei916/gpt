import bpy, sys
import os
sc = bpy.context.scene
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'; sh.color_type = 'SINGLE'; sh.single_color = (0.8, 0.8, 0.8)
sh.show_cavity = True; sh.cavity_type = 'BOTH'; sh.show_shadows = True
sc.render.resolution_x, sc.render.resolution_y = 1280, 720
sc.display.render_aa = '8'
shots = [('left', 'CamLeft', 121), ('right', 'CamWide', 121), ('close', 'CamClose', 150), ('hero', 'CamHero', 230)]
for n, c, f in shots:
    sc.timeline_markers.clear()
    sc.frame_set(f); sc.camera = bpy.data.objects[c]
    sc.render.filepath = os.environ.get('OUT','.')+f'/clay_{n}.png'
    bpy.ops.render.render(write_still=True)
    print('CLAY', n)
