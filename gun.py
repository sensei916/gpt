# Eye of Horus (Beretta 1301 Tactical, Hoshino livery) - procedural build
import os
# units: authored in mm, converted to m. Bore axis = X (muzzle +X), Z up, left side = +Y
import bpy, bmesh, math, sys
from mathutils import Vector

MODE = sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'build'
M = 0.001

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
col = sc.collection

def mat(name, base, rough=0.5, metal=0.0, coat=0.0, bumpscale=0.0, rvar=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Metallic'].default_value = metal
    b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = 0.25
    tc = nt.nodes.new('ShaderNodeTexCoord')
    if rvar:
        n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = 60; n.inputs['Detail'].default_value = 8
        nt.links.new(tc.outputs['Object'], n.inputs['Vector'])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = max(0.02, rough - rvar); mr.inputs['To Max'].default_value = min(1, rough + rvar)
        nt.links.new(n.outputs['Fac'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], b.inputs['Roughness'])
    if bumpscale:
        n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 2500; n2.inputs['Detail'].default_value = 4
        nt.links.new(tc.outputs['Object'], n2.inputs['Vector'])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bumpscale; bp.inputs['Distance'].default_value = 0.0002
        nt.links.new(n2.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    return m

MAT = {
 'white': mat('WhiteCerakote', (0.80, 0.80, 0.78), 0.45, 0, 0.15, 0.25, 0.12),
 'metal': mat('BlackParkerized', (0.035, 0.035, 0.038), 0.36, 0.9, 0, 0.15, 0.12),
 'poly':  mat('BlackPolymer', (0.025, 0.025, 0.027), 0.58, 0, 0, 0.35, 0.08),
 'pink':  mat('PinkAnodized', (0.95, 0.38, 0.55), 0.3, 0.7, 0, 0.05, 0.05),
 'chrome':mat('BoltChrome', (0.75, 0.75, 0.76), 0.16, 1.0, 0, 0, 0.05),
 'hull':  mat('ShellHull', (0.55, 0.04, 0.05), 0.35, 0, 0.3, 0, 0.05),
 'brass': mat('Brass', (0.88, 0.62, 0.30), 0.22, 1.0, 0, 0, 0.06),
 'rubber':mat('Rubber', (0.02, 0.02, 0.02), 0.85, 0, 0, 0.6, 0.05),
 'fiber': mat('FiberRed', (1.0, 0.05, 0.08), 0.2, 0, 0.5),
}

ROOT = bpy.data.objects.new('GunRoot', None); col.objects.link(ROOT)
BOLT = bpy.data.objects.new('BoltRig', None); col.objects.link(BOLT); BOLT.parent = ROOT

def finish(o, m, bevel=1.2, seg=3, parent=None):
    o.data.materials.append(MAT[m])
    if bevel:
        bm = o.modifiers.new('Bevel', 'BEVEL'); bm.width = bevel*M; bm.segments = seg
        bm.limit_method = 'ANGLE'; bm.angle_limit = math.radians(35)
        bm.harden_normals = False
    wn = o.modifiers.new('WN', 'WEIGHTED_NORMAL'); wn.keep_sharp = True
    for p in o.data.polygons: p.use_smooth = True
    o.parent = parent or ROOT
    return o

def prism(name, pts, width, m, y0=0.0, bevel=1.5, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    hw = width/2
    f = [bm.verts.new(((x)*M, (y0+hw)*M, z*M)) for x, z in pts]
    b = [bm.verts.new(((x)*M, (y0-hw)*M, z*M)) for x, z in pts]
    bm.faces.new(f); bm.faces.new(list(reversed(b)))
    n = len(pts)
    for i in range(n):
        j = (i+1) % n
        bm.faces.new([f[i], b[i], b[j], f[j]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); col.objects.link(o)
    return finish(o, m, bevel, 3, parent)

def box(name, x0, x1, y0, y1, z0, z1, m, bevel=0.8, parent=None):
    return prism(name, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], y1-y0, m, (y0+y1)/2, bevel, parent)

def cyl(name, axis, c, r, length, m, verts=48, bevel=0.6, parent=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r*M, depth=length*M, location=[v*M for v in c])
    o = bpy.context.active_object; o.name = name
    if axis == 'X': o.rotation_euler = (0, math.radians(90), 0)
    if axis == 'Y': o.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)
    return finish(o, m, bevel, 2, parent)

def xcyl(name, x0, x1, r, z=0, y=0, m='metal', **k):
    return cyl(name, 'X', ((x0+x1)/2, y, z), r, x1-x0, m, **k)

# ---------------- receiver ----------------
prism('Receiver', [(-40,-42),(190,-42),(190,20),(178,28),(-28,28),(-40,16)], 32, 'white', bevel=2.5)
box('TopRail', -12, 186, -10.5, 10.5, 28, 34, 'metal', 0.6)
for i in range(19):
    x = -6 + i*10
    box(f'RailRib{i}', x, x+5.2, -10.5, 10.5, 34, 38.5, 'metal', 0.5)
# ejection port (right side, -Y) + bolt
box('EjectPort', 70, 142, -16.6, -15.4, -6, 19, 'poly', 0.3)
box('BoltCarrier', 76, 136, -16.4, -8, -2, 15, 'chrome', 0.8, parent=BOLT)
cyl('ChargingHandle', 'Y', (118, -27, 7), 4.2, 22, 'chrome', 24, 0.4, parent=BOLT)
bpy.ops.mesh.primitive_uv_sphere_add(radius=6.5*M, location=(118*M, -39*M, 7*M), segments=32, ring_count=16)
k = bpy.context.active_object; k.name = 'HandleKnob'; k.scale = (1, 0.7, 1); bpy.ops.object.transform_apply(scale=True)
finish(k, 'pink', 0, parent=BOLT)
# controls
cyl('BoltRelease', 'Y', (62, -17, -24), 5.5, 4, 'pink', 24, 0.5)
cyl('SafetyBtn', 'Y', (102, 0, -50), 3.8, 38, 'pink', 24, 0.5)
# trigger group
box('TriggerHousing', 15, 125, -15, 15, -56, -42, 'poly', 1.5)
box('GuardBottom', 28, 112, -6, 6, -84, -78, 'poly', 2.0)
box('GuardFront', 106, 112, -6, 6, -84, -56, 'poly', 2.0)
prism('Trigger', [(76,-56),(82,-56),(78,-66),(72,-76),(68,-75),(74,-66)], 6, 'pink', bevel=1)
# pistol grip
prism('PistolGrip', [(-20,-42),(28,-48),(-12,-150),(-50,-155),(-60,-142)], 30, 'white', bevel=4)
for i in range(6):
    z = -70 - i*13
    x = 22 - (i*13+22)*0.42
    box(f'GripTex{i}', x-4, x+3, -15.5, 15.5, z-4, z, 'poly', 1)
# stock
prism('Stock', [(-40,24),(-40,-38),(-90,-44),(-160,-56),(-330,-90),(-346,-92),(-346,38),(-330,40),(-200,30),(-60,27)], 36, 'white', bevel=5)
prism('StockWristCut', [(-120,-20),(-250,-40),(-250,-60),(-150,-48)], 36.4, 'poly', bevel=1)
box('ButtPad', -370, -346, -20, 20, -94, 40, 'rubber', 4)
box('StockStripe', -300, -296, -18.6, 18.6, -80, 34, 'pink', 0.4)
cyl('AbydosEmblem', 'Y', (-230, 18.3, -6), 15, 1.2, 'pink', 64, 0.3)
cyl('AbydosEmblemIn', 'Y', (-230, 19.0, -6), 10.5, 0.6, 'white', 64, 0.2)
# ---------------- barrel / mag ----------------
xcyl('BarrelShoulder', 190, 214, 16)
xcyl('Barrel', 214, 662, 11.5)
box('VentRib', 214, 650, -4.5, 4.5, 16, 19.5, 'metal', 0.5)
for i in range(18):
    x = 222 + i*24
    box(f'RibPost{i}', x, x+6, -2.5, 2.5, 10.5, 16.2, 'metal', 0.3)
bpy.ops.mesh.primitive_uv_sphere_add(radius=2.2*M, location=(646*M, 0, 22*M))
s = bpy.context.active_object; s.name = 'FrontBead'; finish(s, 'fiber', 0)
xcyl('Choke', 662, 712, 14.5)
for i in range(5):
    x = 672 + i*8
    xcyl(f'ChokeGroove{i}', x, x+3, 15.1, m='poly', verts=48)
xcyl('MagTube', 190, 560, 13, z=-28)
xcyl('MagExtension', 560, 640, 13, z=-28)
xcyl('MagCap', 640, 656, 15.5, z=-28, m='pink')
box('BarrelClamp', 596, 618, -17, 17, -44, 13, 'metal', 2)
# forend
prism('Forend', [(200,-50),(428,-50),(442,-40),(442,-6),(428,0),(200,0)], 46, 'white', 0, bevel=5)
for i in range(7):
    x = 240 + i*24
    box(f'ForendGrip{i}', x, x+10, -23.6, 23.6, -38, -14, 'poly', 1)
box('ForendRing', 436, 444, -21, 21, -46, -4, 'pink', 1)
# side saddle (+Y left)
box('SaddlePlate', 40, 168, 16, 21, -34, 22, 'poly', 1.2)
box('SaddleBody', 44, 164, 21, 30, -30, 18, 'poly', 2)
for i in range(6):
    x = 54 + i*20
    cyl(f'SaddleShellHull{i}', 'Z', (x, 33, 4), 10.4, 54, 'hull', 32, 0.6)
    cyl(f'SaddleShellBrass{i}', 'Z', (x, 33, -27), 10.9, 8, 'brass', 32, 0.6)

# ejected shell (animated)
SHELL = bpy.data.objects.new('EjectShell', None); col.objects.link(SHELL); SHELL.parent = ROOT
cyl('EjectHull', 'X', (0,0,0), 10.4, 54, 'hull', 32, 0.6, parent=SHELL).location.x = 4*M
cyl('EjectBrass', 'X', (-27*M/M*0,0,0), 10.9, 8, 'brass', 32, 0.6, parent=SHELL).location.x = -27*M
SHELL.location = (106*M, -8*M, 6*M)

# ---------------- stage ----------------
w = bpy.data.worlds.new('World'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']
import os
hdr = '/workspace/assets/studio.hdr'
cands = [p for p in [] if os.path.exists(p)]
if not cands:
    for r, d, fs in os.walk(os.environ.get('ASSETS','assets')):
        for f_ in fs:
            if f_.endswith(('.hdr', '.exr')): cands.append(os.path.join(r, f_))
if cands:
    env = w.node_tree.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(cands[0])
    w.node_tree.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.35
else:
    bg.inputs['Color'].default_value = (0.02, 0.02, 0.022, 1); bg.inputs['Strength'].default_value = 1
# camera ray sees dark bg
lp = w.node_tree.nodes.new('ShaderNodeLightPath'); mix = w.node_tree.nodes.new('ShaderNodeMixShader')
bk = w.node_tree.nodes.new('ShaderNodeBackground'); bk.inputs['Color'].default_value = (0.012, 0.012, 0.014, 1)
out = w.node_tree.nodes['World Output']
w.node_tree.links.new(lp.outputs['Is Camera Ray'], mix.inputs['Fac'])
w.node_tree.links.new(bg.outputs['Background'], mix.inputs[1]); w.node_tree.links.new(bk.outputs['Background'], mix.inputs[2])
w.node_tree.links.new(mix.outputs['Shader'], out.inputs['Surface'])

# floor (dark concrete-ish)
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, -0.17))
fl = bpy.context.active_object; fl.name = 'Floor'
fm = mat('Floor', (0.03, 0.03, 0.032), 0.55, 0, 0, 0.4, 0.25); fl.data.materials.append(fm)

def area(name, loc, rot, size, energy, color=(1,1,1), shape='RECTANGLE', sy=None):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size; l.color = color
    if sy: l.shape = shape; l.size_y = sy
    o = bpy.data.objects.new(name, l); col.objects.link(o); o.location = loc
    tgt = Vector((0.15, 0, 0)); d = tgt - Vector(loc); o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return o
area('Key', (0.3, -1.2, 1.1), 0, 1.2, 260, (1, 0.97, 0.93), 'RECTANGLE', 0.5)
area('Fill', (-0.6, 1.3, 0.6), 0, 1.5, 70, (0.9, 0.93, 1.0))
area('RimPink', (-0.9, 0.2, 0.5), 0, 0.6, 140, (1.0, 0.55, 0.75), 'RECTANGLE', 1.4)
area('Top', (0.15, 0, 1.6), 0, 2.0, 90)

ROOT.location = (0, 0, 0)
ROOT.scale = (1, 1, 1)

def camera(name, loc, target, lens=50, fstop=None, focus=None):
    c = bpy.data.cameras.new(name); c.lens = lens; c.sensor_width = 36
    o = bpy.data.objects.new(name, c); col.objects.link(o); o.location = loc
    tr = o.constraints.new('TRACK_TO'); 
    t = bpy.data.objects.new(name+'_tgt', None); col.objects.link(t); t.location = target
    tr.target = t; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    if fstop:
        c.dof.use_dof = True; c.dof.aperture_fstop = fstop; c.dof.focus_object = focus or t
    return o, t

camWide, tWide = camera('CamWide', (0.17, -1.95, 0.30), (0.17, 0, -0.02), 50, 5.6)
camClose, tClose = camera('CamClose', (0.24, -0.42, 0.10), (0.10, -0.02, -0.01), 60, 2.8)
camHero, tHero = camera('CamHero', (1.15, -0.95, 0.26), (0.12, 0, -0.03), 70, 4.0)
camLeft, tLeft = camera('CamLeft', (0.17, 1.95, 0.25), (0.15, 0, -0.03), 50, 5.6)
sc.camera = camWide

# ---------------- animation ----------------
sc.frame_start, sc.frame_end = 1, 240
sc.render.fps = 24
def key(o, path, f, val, interp=None):
    setattr(o, path, val); o.keyframe_insert(path, frame=f)
# turntable 1-120 (pivot near center of mass)
ROOT.location = (0, 0, 0)
key(ROOT, 'rotation_euler', 1, (0, 0, math.radians(-25)))
key(ROOT, 'rotation_euler', 120, (0, 0, math.radians(-25+360)))
key(ROOT, 'rotation_euler', 121, (0, 0, 0))
key(ROOT, 'rotation_euler', 240, (0, 0, math.radians(8)))
# bolt cycle 135-165
key(BOLT, 'location', 1, (0, 0, 0)); key(BOLT, 'location', 134, (0, 0, 0))
key(BOLT, 'location', 146, (-0.068, 0, 0)); key(BOLT, 'location', 156, (-0.068, 0, 0))
key(BOLT, 'location', 159, (0, 0, 0))
# ejected shell 140-185
SHELL.hide_render = True
key(SHELL, 'hide_render', 1, True); key(SHELL, 'hide_render', 141, False); key(SHELL, 'hide_render', 200, True)
for ch in [SHELL]:
    key(ch, 'location', 141, (0.100, -0.010, 0.006)); key(ch, 'rotation_euler', 141, (0, 0, 0))
    key(ch, 'location', 152, (0.085, -0.140, 0.075)); key(ch, 'rotation_euler', 152, (math.radians(70), math.radians(40), math.radians(250)))
    key(ch, 'location', 170, (0.050, -0.330, -0.090)); key(ch, 'rotation_euler', 170, (math.radians(160), math.radians(90), math.radians(620)))
for o in [SHELL]:
    if o.animation_data and o.animation_data.action:
        pass
# camera hero push-in 201-240
key(camHero, 'location', 200, (1.15, -0.95, 0.26)); key(camHero, 'location', 240, (0.98, -0.80, 0.22))
# camera cuts
for f, c in [(1, camWide), (121, camClose), (201, camHero)]:
    mk = sc.timeline_markers.new(f'cut{f}', frame=f); mk.camera = c
# close cam slow drift
key(camClose, 'location', 121, (0.26, -0.43, 0.10)); key(camClose, 'location', 200, (0.20, -0.39, 0.09))

# render
r = sc.render; r.resolution_x, r.resolution_y = 1280, 720; r.resolution_percentage = 100
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = 48; sc.cycles.use_denoising = True; sc.cycles.adaptive_threshold = 0.03
sc.cycles.max_bounces = 6
r.image_settings.file_format = 'PNG'
bpy.ops.wm.save_as_mainfile(filepath=os.environ.get('OUT','.')+'/eye_of_horus.blend')
print('BUILD_OK', len(bpy.data.objects))
