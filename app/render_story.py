"""Procedural stylized 3D short renderer. Run by Blender, not regular Python.
Usage: blender --background --python app/render_story.py -- plan.json visual.mp4
"""
import bpy, json, math, os, random, sys
from mathutils import Vector

SUPPORTED = {"cloud","rocket","planet","phone","brain","heart","flower","robot","book","lightbulb","atom","plant","star","camera","water_drop","gear","magnet","globe","cube","sphere","cone","cylinder","torus"}
PALETTE = {
 "curious": (0.12,0.68,0.95,1), "happy": (1.0,0.48,0.12,1), "worried": (0.55,0.40,0.95,1),
 "surprised": (0.95,0.22,0.42,1), "determined": (0.10,0.78,0.55,1), "relieved": (0.35,0.82,0.75,1)
}

def mat(name, color, metallic=0.08, roughness=0.28, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = color
    m.use_nodes = True
    bs = m.node_tree.nodes.get("Principled BSDF")
    if bs:
        bs.inputs["Base Color"].default_value = color
        bs.inputs["Metallic"].default_value = metallic
        bs.inputs["Roughness"].default_value = roughness
        if "Coat Weight" in bs.inputs: bs.inputs["Coat Weight"].default_value = 0.25
        if "Emission Color" in bs.inputs: bs.inputs["Emission Color"].default_value = color
        if "Emission Strength" in bs.inputs: bs.inputs["Emission Strength"].default_value = emission
    return m

def component(op, name, parent, loc, scale, material, rotation=(0,0,0), **kwargs):
    op(**kwargs)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = loc
    obj.scale = scale
    obj.rotation_euler = rotation
    if obj.type == "MESH":
        for p in obj.data.polygons: p.use_smooth = True
        obj.data.materials.append(material)
    return obj

def sphere(name, root, loc, scale, material):
    return component(bpy.ops.mesh.primitive_uv_sphere_add, name, root, loc, scale, material, segments=24, ring_count=16)
def cube(name, root, loc, scale, material, bevel=0.15):
    o=component(bpy.ops.mesh.primitive_cube_add,name,root,loc,scale,material)
    if bevel:
        mod=o.modifiers.new("Soft rounded edges","BEVEL"); mod.width=bevel; mod.segments=3
        o.modifiers.new("Weighted corner normals","WEIGHTED_NORMAL")
    return o
def cyl(name, root, loc, scale, material, vertices=32, rotation=(0,0,0)):
    o=component(bpy.ops.mesh.primitive_cylinder_add,name,root,loc,scale,material,rotation=rotation,vertices=vertices)
    return o
def cone(name, root, loc, scale, material, rotation=(0,0,0)):
    return component(bpy.ops.mesh.primitive_cone_add,name,root,loc,scale,material,rotation=rotation,vertices=32)
def torus(name, root, loc, scale, material, rotation=(0,0,0)):
    return component(bpy.ops.mesh.primitive_torus_add,name,root,loc,scale,material,rotation=rotation,major_segments=48,minor_segments=12)

def make_root(name, loc):
    obj=bpy.data.objects.new(name,None); bpy.context.collection.objects.link(obj); obj.location=loc; obj.empty_display_type="SPHERE"; obj.empty_display_size=.25
    return obj

def add_face(root, dark, white, scale=1.0):
    # The front of every friendly object faces the camera (negative Y).
    for x in (-0.28,0.28):
        sphere("Eye white",root,(x,-0.57,0.18),(0.115,0.055,0.14),white)
        sphere("Eye pupil",root,(x,-0.625,0.18),(0.055,0.028,0.075),dark)
    # A curved-smile stand-in that stays legible at mobile size.
    torus("Friendly smile",root,(0,-0.61,-0.16),(0.20,0.035,0.105),dark,(math.pi/2,0,0))

def make_prop(kind, root, body, accent, dark, white):
    kind=kind if kind in SUPPORTED else "sphere"
    if kind=="cloud":
        for i,(x,z,r) in enumerate([(-.48,0,.52),(-.12,.28,.62),(.34,.06,.54),(.65,-.08,.37)]): sphere("Cloud puff",root,(x,0,z),(r,r*.62,r),body)
    elif kind=="rocket":
        cyl("Rocket body",root,(0,0,0),(0.37,0.38,.86),body)
        cone("Rocket nose",root,(0,0,.92),(.38,.38,.42),accent)
        for x in (-.37,.37): cone("Rocket fin",root,(x,.03,-.48),(.22,.16,.34),accent,(0,(-.45 if x<0 else .45),0))
        cone("Rocket flame",root,(0,.02,-1.05),(.18,.15,.33),mat("Flame",(1,.35,.04,1),emission=.5))
        add_face(root,dark,white)
    elif kind in ("planet","globe"):
        sphere("Planet",root,(0,0,0),(.8,.8,.8),body); torus("Orbit",root,(0,0,0),(1.08,.07,1.08),accent,(math.radians(22),math.radians(18),math.radians(-20)))
        add_face(root,dark,white)
    elif kind=="phone":
        cube("Phone body",root,(0,0,0),(.65,.20,1.03),body,.18)
        cube("Phone screen",root,(0,-.215,.03),(.53,.035,.80),accent,.07)
        sphere("Phone camera",root,(0,-.255,.82),(.045,.02,.045),dark)
        add_face(root,dark,white,.8)
    elif kind=="brain":
        for x,z,r in [(-.4,.08,.43),(-.1,.25,.47),(.25,.12,.45),(.43,-.15,.32),(-.22,-.24,.35)]: sphere("Brain lobe",root,(x,0,z),(r,r*.72,r),body)
        add_face(root,dark,white)
    elif kind=="heart":
        sphere("Heart lobe L",root,(-.25,0,.15),(.48,.35,.48),body); sphere("Heart lobe R",root,(.25,0,.15),(.48,.35,.48),body)
        cone("Heart point",root,(0,0,-.35),(.63,.33,.70),body,(0,math.pi,0)); add_face(root,dark,white,.8)
    elif kind=="flower":
        cyl("Flower stem",root,(0,.12,-.62),(.10,.10,.66),accent)
        for ang in range(0,360,60):
            a=math.radians(ang); sphere("Petal",root,(math.sin(a)*.48,0,math.cos(a)*.48),(.32,.22,.42),body)
        sphere("Flower center",root,(0,-.08,0),(.34,.25,.34),accent); add_face(root,dark,white,.7)
    elif kind=="robot":
        cube("Robot torso",root,(0,0,-.20),(.62,.40,.58),body,.18)
        sphere("Robot head",root,(0,-.01,.50),(.65,.48,.56),accent)
        for x in (-.72,.72): cyl("Robot ear",root,(x,0,.54),(.13,.14,.20),body,vertices=20)
        add_face(root,dark,white)
    elif kind=="book":
        cube("Book cover",root,(0,0,0),(.76,.22,.95),body,.06)
        cube("Book pages",root,(0,-.16,0),(.67,.05,.84),white,.03)
        cube("Book spine",root,(-.59,-.02,0),(.13,.25,.96),accent,.03)
        sphere("Book eye L",root,(-.18,-.24,.12),(.085,.03,.10),dark); sphere("Book eye R",root,(.18,-.24,.12),(.085,.03,.10),dark)
    elif kind=="lightbulb":
        sphere("Bulb glass",root,(0,0,.22),(.62,.58,.70),body)
        cyl("Bulb base",root,(0,0,-.45),(.30,.30,.20),accent)
        for z in (-.55,-.62): torus("Bulb screw",root,(0,0,z),(.29,.05,.29),dark)
        add_face(root,dark,white,.75)
    elif kind=="atom":
        sphere("Atom nucleus",root,(0,0,0),(.27,.27,.27),accent)
        for rot in [(0,0,0),(math.pi/2,.45,0),(.7,math.pi/2,.4)]: torus("Electron orbit",root,(0,0,0),(.98,.045,.98),body,rot)
    elif kind=="plant":
        cyl("Plant stalk",root,(0,0,-.35),(.10,.10,.60),accent)
        for x,z,ang in [(-.4,-.1,-.5),(.4,.02,.5),(-.28,.33,-.7),(.25,.45,.7)]: sphere("Plant leaf",root,(x,0,z),(.34,.12,.18),body,(0,ang,ang))
        sphere("Plant face",root,(0,-.08,.55),(.25,.18,.25),accent); add_face(root,dark,white,.55)
    elif kind=="star":
        # A friendly five-point star created from alternating-radius points.
        verts=[]
        for i in range(10):
            a=math.pi/2+i*math.pi/5; r=1.0 if i%2==0 else .48; verts.append((math.cos(a)*r,0,math.sin(a)*r))
        mesh=bpy.data.meshes.new("Star mesh"); mesh.from_pydata(verts,[],[list(range(10))]); mesh.update()
        ob=bpy.data.objects.new("Star",mesh); bpy.context.collection.objects.link(ob); ob.parent=root; ob.location=(0,0,0); ob.data.materials.append(body)
        sphere("Star eyes L",root,(-.22,-.1,.08),(.07,.04,.08),dark); sphere("Star eyes R",root,(.22,-.1,.08),(.07,.04,.08),dark)
    elif kind=="camera":
        cube("Camera body",root,(0,0,0),(.75,.36,.52),body,.12); cyl("Lens",root,(0,-.40,.02),(.32,.16,.32),accent,rotation=(math.pi/2,0,0)); add_face(root,dark,white,.65)
    elif kind=="water_drop":
        sphere("Drop round body",root,(0,0,-.12),(.53,.40,.60),body)
        cone("Drop tip",root,(0,0,.52),(.40,.38,.55),body); add_face(root,dark,white,.7)
    elif kind=="gear":
        torus("Gear outer",root,(0,0,0),(.78,.18,.78),body); cyl("Gear hub",root,(0,0,0),(.30,.20,.30),accent)
        for a in range(0,360,45):
            t=math.radians(a); cube("Gear tooth",root,(math.sin(t)*.82,0,math.cos(t)*.82),(.16,.16,.22),body, .04)
        add_face(root,dark,white,.65)
    elif kind=="magnet":
        # A recognisable U magnet: two uprights and a rounded lower bridge.
        cyl("Magnet left",root,(-.42,0,.15),(.22,.22,.65),body); cyl("Magnet right",root,(.42,0,.15),(.22,.22,.65),accent)
        torus("Magnet bridge",root,(0,0,-.40),(.43,.22,.27),body,(math.pi/2,0,0))
    elif kind=="cube": cube("Hero cube",root,(0,0,0),(.72,.72,.72),body,.16); add_face(root,dark,white,.7)
    elif kind=="cone": cone("Hero cone",root,(0,0,0),(.8,.72,1.0),body); add_face(root,dark,white,.65)
    elif kind=="cylinder": cyl("Hero cylinder",root,(0,0,0),(.6,.6,.8),body); add_face(root,dark,white,.65)
    elif kind=="torus": torus("Hero torus",root,(0,0,0),(.7,.18,.7),body); add_face(root,dark,white,.65)
    else: sphere("Hero sphere",root,(0,0,0),(.76,.76,.76),body); add_face(root,dark,white,.7)

def create_text(text, name, loc, size, material, align="CENTER"):
    bpy.ops.object.text_add(location=loc, rotation=(math.pi/2,0,0))
    obj=bpy.context.object; obj.name=name; obj.data.body=str(text); obj.data.size=size; obj.data.align_x=align
    obj.data.extrude=.002; obj.data.bevel_depth=.001; obj.data.materials.append(material)
    return obj

def key_visibility(obj, start, end, actual_scale=None, hide_after=True):
    if actual_scale is None: actual_scale=tuple(obj.scale)
    obj.scale=(0,0,0); obj.keyframe_insert(data_path="scale",frame=max(1,start-1))
    obj.scale=actual_scale; obj.keyframe_insert(data_path="scale",frame=start)
    obj.scale=actual_scale; obj.keyframe_insert(data_path="scale",frame=end)
    if hide_after:
        obj.scale=(0,0,0); obj.keyframe_insert(data_path="scale",frame=min(bpy.context.scene.frame_end,end+1))

def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(argv)<2: raise SystemExit("Usage: render_story.py -- plan.json output.mp4")
    plan_path, output_path=argv[0],argv[1]
    plan=json.load(open(plan_path,encoding="utf-8"))
    scenes=plan.get("scenes",[])
    if not 5 <= len(scenes) <= 8: raise RuntimeError("Expected 5-8 scenes")
    for s in scenes:
        if s.get("visual") not in SUPPORTED or s.get("companion") not in SUPPORTED: raise RuntimeError("Unsupported visual in plan")
    random.seed(42)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes,bpy.data.curves,bpy.data.materials,bpy.data.cameras,bpy.data.lights):
        # Keep built-in collections valid; removed objects do not require aggressive datablock deletion.
        pass
    scene=bpy.context.scene
    width,height,fps=720,1280,24
    duration=max(20,min(55,int(plan.get("duration_seconds",36))))
    frames=duration*fps
    scene.frame_start=1; scene.frame_end=frames; scene.render.fps=fps
    scene.render.resolution_x=width; scene.render.resolution_y=height; scene.render.resolution_percentage=100
    try:
        scene.render.engine="BLENDER_EEVEE_NEXT"
    except Exception:
        scene.render.engine="BLENDER_EEVEE"
    scene.render.image_settings.file_format="FFMPEG"; scene.render.ffmpeg.format="MPEG4"; scene.render.ffmpeg.codec="H264"
    scene.render.ffmpeg.constant_rate_factor="MEDIUM"; scene.render.ffmpeg.ffmpeg_preset="GOOD"
    scene.render.filepath=os.path.abspath(output_path); scene.render.use_file_extension=True
    scene.render.image_settings.color_mode="RGB"
    scene.render.film_transparent=False
    try:
        scene.view_settings.view_transform="AgX"
    except Exception:
        scene.view_settings.view_transform="Standard"
    scene.render.resolution_percentage=100
    world=bpy.data.worlds.new("Broskyee midnight gradient") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world=world; world.use_nodes=True; world.node_tree.nodes["Background"].inputs["Color"].default_value=(.018,.035,.09,1); world.node_tree.nodes["Background"].inputs["Strength"].default_value=.45
    navy=mat("Backdrop navy",(.018,.035,.09,1),roughness=.7); floor_mat=mat("Stage indigo",(.045,.09,.18,1),roughness=.45); white=mat("Eye white",(.95,.98,1,1),roughness=.22); dark=mat("Ink",(.012,.02,.045,1),roughness=.3); panel=mat("Caption card",(.025,.055,.12,1),roughness=.45,emission=.02); textmat=mat("Caption white",(1,1,1,1),roughness=.3,emission=.12); accentmat=mat("Accent cyan",(.05,.75,1,1),metallic=.22,roughness=.22,emission=.04)
    floor=cube("Stage floor",None,(0,2,-.55),(10,10,.18),floor_mat,.05)
    bpy.ops.object.camera_add(location=(0,-22,4.5)); cam=bpy.context.object; cam.name="Portrait camera"; cam.data.type="ORTHO"; cam.data.ortho_scale=10.8
    direction=Vector((0,0,4.15))-cam.location; cam.rotation_euler=direction.to_track_quat("-Z","Y").to_euler(); scene.camera=cam
    def area(name, loc, energy, color, size):
        bpy.ops.object.light_add(type="AREA",location=loc); light=bpy.context.object; light.name=name; light.data.energy=energy; light.data.color=color; light.data.shape="DISK"; light.data.size=size; light.rotation_euler=(Vector((0,0,4))-light.location).to_track_quat("-Z","Y").to_euler()
    area("Key softbox",(1,-8,10),1250,(.65,.83,1),7); area("Warm fill",(-6,-3,5),800,(1,.48,.22),5); area("Rim light",(4,3,8),1500,(.12,.55,1),4)
    # Decorative floating spheres stay subtle and are not random across runs.
    particle_mat=mat("Floating particle",(.18,.55,.85,1),roughness=.25,emission=.08)
    for i in range(18):
        x=random.uniform(-3.0,3.0); z=random.uniform(2.0,8.6); y=random.uniform(.8,2.8); r=random.uniform(.025,.065)
        o=sphere("Ambient particle",None,(x,y,z),(r,r,r),particle_mat)
        o.keyframe_insert(data_path="location",frame=1); o.location.x+=random.uniform(-.25,.25); o.location.z+=random.uniform(-.2,.2); o.keyframe_insert(data_path="location",frame=frames)
    title=create_text(plan.get("title","AI-Broskyee Original Short").upper(),"Intro title",(0,-4.65,8.6),.32,textmat)
    key_visibility(title,1,min(frames,2*fps),(1,1,1))
    scene_frames=frames//len(scenes)
    for i,s in enumerate(scenes):
        start=1+i*scene_frames; end=(frames if i==len(scenes)-1 else (i+1)*scene_frames)
        emo=s.get("emotion","curious"); color=PALETTE.get(emo,PALETTE["curious"])
        hero_mat=mat(f"Scene {i+1} hero",color,metallic=.12,roughness=.25,emission=.015)
        companion_col=(.95,.42,.12,1) if i%2==0 else (.28,.45,1,1)
        comp_mat=mat(f"Scene {i+1} companion",companion_col,metallic=.1,roughness=.27,emission=.01)
        root=make_root(f"Scene {i+1} hero root",(-.55,0,4.15))
        make_prop(s["visual"],root,hero_mat,accentmat,dark,white)
        key_visibility(root,start,end,(.9,.9,.9))
        root.location=(-.65,-.15,4.1); root.keyframe_insert(data_path="location",frame=start)
        root.rotation_euler=(0,0,math.radians(-5 if i%2==0 else 5)); root.keyframe_insert(data_path="rotation_euler",frame=start)
        root.location=(-.45,-.1,4.45); root.rotation_euler=(math.radians(3 if i%2==0 else -3),0,math.radians(5 if i%2==0 else -5)); root.keyframe_insert(data_path="location",frame=start+(end-start)//2); root.keyframe_insert(data_path="rotation_euler",frame=start+(end-start)//2)
        root.location=(-.65,0,4.12); root.rotation_euler=(0,0,0); root.keyframe_insert(data_path="location",frame=end); root.keyframe_insert(data_path="rotation_euler",frame=end)
        other=make_root(f"Scene {i+1} companion root",(1.45,.1,3.25))
        make_prop(s["companion"],other,comp_mat,hero_mat,dark,white)
        key_visibility(other,start,end,(.42,.42,.42))
        other.location=(1.55,.1,3.15); other.keyframe_insert(data_path="location",frame=start)
        other.location=(1.35,.1,3.45); other.keyframe_insert(data_path="location",frame=start+(end-start)//2)
        other.location=(1.55,.1,3.15); other.keyframe_insert(data_path="location",frame=end)
        # Camera subtly reframes each story beat; keep every prop within portrait-safe bounds.
        cam.location=(.06*math.sin(i),-22,4.5+.08*math.sin(i)); cam.keyframe_insert(data_path="location",frame=start)
        cap_text=create_text(str(s.get("caption","")),f"Caption {i+1}",(0,-4.85,1.38),.37,textmat)
        card=cube(f"Caption backing {i+1}",None,(0,-4.55,1.42),(3.05,.075,.43),panel,.14)
        key_visibility(card,start,end); key_visibility(cap_text,start,end,(1,1,1))
        # Small progress accent changes per scene.
        prog=cube(f"Progress bar {i+1}",None,(-2.45,-4.58,.55),(max(.04,2.45*(i+1)/len(scenes)),.035,.045),accentmat,.02)
        key_visibility(prog,start,end)
    # Smooth animation curves without scale overshoot.
    for obj in bpy.data.objects:
        ad=obj.animation_data
        if ad and ad.action:
            for fc in getattr(ad.action,"fcurves",[]):
                for point in fc.keyframe_points:
                    point.interpolation="BEZIER"
                    try: point.handle_left_type="AUTO_CLAMPED"; point.handle_right_type="AUTO_CLAMPED"
                    except Exception: pass
    os.makedirs(os.path.dirname(os.path.abspath(output_path)),exist_ok=True)
    print(f"Rendering {duration}s, {len(scenes)} scenes, {width}x{height}@{fps} to {output_path}",flush=True)
    bpy.ops.render.render(animation=True)
    print("BLENDER_RENDER_COMPLETE",flush=True)

if __name__=="__main__": main()
