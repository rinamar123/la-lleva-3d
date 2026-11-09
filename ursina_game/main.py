"""La Lleva 3D - edición de escritorio con Ursina.

Ejecutar desde la raíz: python -m ursina_game.main
"""
from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import math
import random
import time

app = Ursina(title="La Lleva 3D - Parque", borderless=False)
window.color = color.rgb(115, 205, 235)
window.exit_button.visible = False
window.fps_counter.enabled = True

DURATION = 180
WORLD = 90
state = {"screen": "welcome", "mode": "solo", "bots": 3, "difficulty": "normal",
         "remaining": DURATION, "it": 0, "players": [], "last_tag": 0.0}
ui = []
world_entities = []
player = None
bot_entities = []
timer_text = None
tag_text = None
minimap_bg = None
menu_root = Entity(parent=camera.ui)
welcome_root = Entity(parent=camera.ui)

def clear_ui():
    for e in ui:
        destroy(e)
    ui.clear()

def label(text, y, scale=1.3, parent=menu_root, col=color.white):
    e = Text(text=text, parent=parent, y=y, origin=(0, 0), scale=scale, color=col)
    ui.append(e)
    return e

def button(text, y, action, parent=menu_root, scale=1.2):
    e = Button(text=text, parent=parent, y=y, scale=(.34, .065), color=color.rgb(32, 105, 120),
               highlight_color=color.rgb(50, 150, 150), pressed_color=color.azure)
    e.text_entity.scale = 1.1
    e.on_click = action
    ui.append(e)
    return e

def make_kid(parent, x, y, shirt, phase=0):
    kid = Entity(parent=parent, position=(x, y, 0))
    torso = Entity(parent=kid, model="cube", color=shirt, scale=(.36,.58,.2), y=-.15)
    head = Entity(parent=kid, model="sphere", color=color.rgb(238,190,145), scale=.38, y=.32)
    Entity(parent=kid, model="sphere", color=color.rgb(65,42,25), scale=(.4,.16,.22), y=.48)
    for side in (-1,1):
        Entity(parent=kid, model="sphere", color=color.white, scale=.055, position=(side*.08,.34,-.105))
        Entity(parent=kid, model="sphere", color=color.black, scale=.025, position=(side*.08,.34,-.15))
        Entity(parent=kid, model="cube", color=shirt, scale=(.12,.42,.12), position=(side*.23,-.12,0), rotation_z=side*18)
        Entity(parent=kid, model="cube", color=color.rgb(45,55,80), scale=(.13,.38,.14), position=(side*.1,-.55,0))
    kid.animate_y(y+.08, duration=.55, curve=curve.in_out_sine, loop=True)
    return kid

def show_welcome():
    state["screen"] = "welcome"
    menu_root.enabled = False
    welcome_root.enabled = True
    Entity(parent=welcome_root, model="quad", scale=(2,1.15), color=color.rgb(90,190,225), z=1)
    Entity(parent=welcome_root, model="quad", scale=(2, .55), y=-.3, color=color.rgb(80,170,90), z=.9)
    for x,z in [(-.8,0),(.8,0)]:
        Entity(parent=welcome_root, model="sphere", color=color.rgb(30,130,55), scale=(.25,.45,.2), x=x, y=.15,z=z)
    make_kid(welcome_root,-.42,-.02,color.orange)
    make_kid(welcome_root,.05,.02,color.azure)
    make_kid(welcome_root,.5,-.03,color.magenta)
    title = Text("¡LA LLEVA!", parent=welcome_root, y=.34, origin=(0,0), scale=3, color=color.white)
    sub = Text("¡Corre, escapa y diviértete!", parent=welcome_root, y=-.48, origin=(0,0), scale=1.3)
    welcome_root.animate_scale(1, duration=.4)
    invoke(show_menu, delay=3.5)

def show_menu():
    # Destruir la bienvenida una sola vez. No cambiar enabled después de
    # destroy(): Panda3D ya no tiene un NodePath válido para ese Entity.
    if welcome_root and welcome_root.enabled:
        destroy(welcome_root)
    menu_root.enabled = True
    state["screen"] = "menu"
    clear_ui()
    label("LA LLEVA 3D", .38, 2.5, col=color.azure)
    label("¡Corre, escapa y atrapa!", .27, 1.1, col=color.yellow)
    button("JUGAR CONTRA LA IA", .10, lambda: show_setup("solo"))
    button("JUGAR CON AMIGOS", -.01, lambda: show_setup("online"))
    button("SALIR", -.25, application.quit)

def show_setup(mode):
    state["mode"] = mode
    state["screen"] = "setup"
    clear_ui()
    label("CONFIGURAR PARTIDA", .38, 1.8)
    label("Cantidad de rivales IA (1 a 8)", .20, 1.1)
    count = Text(str(state["bots"]), parent=menu_root, y=.08, origin=(0,0), scale=2)
    ui.append(count)
    def change(delta):
        state["bots"] = max(1,min(8,state["bots"]+delta))
        count.text = str(state["bots"])
    button("−", .08, lambda: change(-1), scale=.8).x = -.16
    button("+", .08, lambda: change(1), scale=.8).x = .16
    label("Dificultad: FÁCIL / NORMAL / DIFÍCIL", -.04, .85)
    diff = Text(state["difficulty"].upper(), parent=menu_root, y=-.13, origin=(0,0), scale=1.2, color=color.yellow)
    ui.append(diff)
    def cycle():
        options=["facil","normal","dificil"]
        state["difficulty"]=options[(options.index(state["difficulty"])+1)%3]
        diff.text=state["difficulty"].upper()
    button("CAMBIAR DIFICULTAD", -.22, cycle, scale=1)
    if mode == "online":
        label("El modo online con códigos privados aún requiere", -.34, .72, col=color.orange)
        label("la nueva API de salas en Render. No inicia una falsa partida.", -.40, .62, col=color.orange)
        button("VOLVER", -.52, show_menu, scale=1)
    else:
        button("COMENZAR PARTIDA", -.45, start_game)
        button("VOLVER", -.56, show_menu, scale=1)

def make_tree(x,z):
    trunk=Entity(model="cylinder", color=color.rgb(112,72,42), scale=(.65,3,.65), position=(x,1.5,z), collider="box")
    crown=Entity(model="sphere", color=random.choice([color.rgb(55,145,65),color.rgb(70,165,75),color.rgb(45,125,60)]), scale=(3.2,3,3.2), position=(x,3.5,z))
    world_entities.extend([trunk,crown])

def build_park():
    global player, bot_entities, timer_text, tag_text
    for e in world_entities: destroy(e)
    world_entities.clear()
    ground=Entity(model="plane", scale=(WORLD,1,WORLD), texture="white_cube", texture_scale=(45,45), color=color.rgb(82,165,83), collider="box")
    world_entities.append(ground)
    # Senderos de parque
    for pos,scale in [((0,.02,0),(10,.04,90)),((0,.03,0),(90,.04,8)),((22,.04,18),(18,.05,5))]:
        world_entities.append(Entity(model="cube",position=pos,scale=scale,color=color.rgb(205,185,140)))
    # Límites y decoración natural
    for x in range(-42,43,12):
        make_tree(x,-42); make_tree(x,42)
    for z in range(-30,31,14):
        make_tree(-42,z); make_tree(42,z)
    # Bancas y faroles
    for x,z in [(-12,8),(13,-10),(-22,-20),(24,22)]:
        world_entities.append(Entity(model="cube",position=(x,.7,z),scale=(4,.35,1),color=color.rgb(125,75,38)))
        world_entities.append(Entity(model="cube",position=(x,.35,z),scale=(.25,.7,.25),color=color.rgb(80,55,40)))
    for x,z in [(-7,16),(7,16),(-28,0),(28,0)]:
        world_entities.append(Entity(model="cylinder",position=(x,2,z),scale=(.18,4,.18),color=color.dark_gray))
        world_entities.append(Entity(model="sphere",position=(x,4.1,z),scale=.6,color=color.rgb(255,235,150),unlit=True))
    # Zona infantil
    world_entities.append(Entity(model="cube",position=(22,.25,-23),scale=(18,.5,12),color=color.rgb(215,175,90)))
    world_entities.append(Entity(model="cube",position=(22,2,-23),scale=(2,3,2),color=color.azure))
    world_entities.append(Entity(model="cube",position=(26,1,-23),scale=(7,.3,1),color=color.orange,rotation_z=-20))
    # Bordes
    for x,z,s in [(0,45,(90,3,1)),(0,-45,(90,3,1)),(45,0,(1,3,90)),(-45,0,(1,3,90))]:
        world_entities.append(Entity(model="cube",position=(x,1.5,z),scale=s,color=color.rgb(80,110,90),collider="box"))
    player=FirstPersonController(position=(0,2,0),speed=8, jump_height=1.5)
    player.cursor.visible=False
    player.gravity=0.7
    player.camera_pivot.y=1.5
    bot_entities=[]
    for i in range(state["bots"]):
        bot=Entity(model="capsule",color=[color.orange,color.magenta,color.azure,color.lime,color.violet,color.yellow,color.cyan,color.red][i%8],
                   scale=(.9,1.8,.9),position=(random.uniform(-25,25),1,random.uniform(-25,25)),collider="box")
        Entity(parent=bot,model="sphere",color=color.rgb(238,190,145),scale=.55,y=.7)
        bot_entities.append({"entity":bot,"phase":random.random()*5,"it":False})
    state["it"]=random.randrange(len(bot_entities)+1)
    timer_text=Text("03:00",parent=camera.ui,position=(-.85,.45),scale=1.5)
    tag_text=Text("LA LLEVA",parent=camera.ui,position=(.55,.45),scale=1.2,color=color.red)
    Text("WASD mover · Mouse mirar · ESPACIO saltar · ESC menú",parent=camera.ui,position=(-.85,-.47),scale=.8)

def start_game():
    clear_ui()
    menu_root.enabled=False
    state["screen"]="playing"
    state["remaining"]=DURATION
    build_park()
    mouse.locked=True

def back_to_menu():
    mouse.locked=False
    if player:
        destroy(player)
    for b in bot_entities: destroy(b["entity"])
    for e in world_entities:
        destroy(e)
    world_entities.clear()
    for e in list(scene.entities):
        if e is not camera and e not in [menu_root,welcome_root]:
            pass
    if timer_text: destroy(timer_text)
    if tag_text: destroy(tag_text)
    menu_root.enabled=True
    show_menu()

def update():
    if state["screen"]!="playing": return
    dt=time.dt
    state["remaining"]-=dt
    remaining=max(0,int(math.ceil(state["remaining"])))
    timer_text.text=f"{remaining//60:02d}:{remaining%60:02d}"
    # IA básica: persigue al jugador si es la lleva; de lo contrario, escapa.
    for i,b in enumerate(bot_entities):
        ent=b["entity"]
        dx=player.x-ent.x; dz=player.z-ent.z
        dist=max(.01,math.sqrt(dx*dx+dz*dz))
        direction=1 if (i==state["it"]) else -1
        speed={"facil":3.5,"normal":4.5,"dificil":5.5}[state["difficulty"]]
        ent.x += (dx/dist)*direction*speed*dt
        ent.z += (dz/dist)*direction*speed*dt
        ent.x=max(-40,min(40,ent.x)); ent.z=max(-40,min(40,ent.z))
    # Si la persona se acerca a la IA que tiene la lleva, se transfiere.
    if state["it"] < len(bot_entities):
        target=bot_entities[state["it"]]["entity"]
        if distance(player.position,target.position)<2.1 and time.time()-state["last_tag"]>1.2:
            state["it"]=-1
            state["last_tag"]=time.time()
            tag_text.text="¡AHORA LA LLEVAS TÚ!"
            tag_text.color=color.red
    elif state["it"]==-1:
        for i,b in enumerate(bot_entities):
            if distance(player.position,b["entity"].position)<2.1 and time.time()-state["last_tag"]>1.2:
                state["it"]=i; state["last_tag"]=time.time()
                tag_text.text="LA LLEVA: IA "+str(i+1); tag_text.color=color.orange
                break
    if state["remaining"]<=0:
        state["screen"]="finished"
        mouse.locked=False
        clear_ui()
        menu_root.enabled=True
        label("¡TIEMPO TERMINADO!",.2,2)
        label("La ronda duró 3 minutos",.05,1.2)
        button("VOLVER AL MENÚ",-.15,back_to_menu)

def input(key):
    if key=="escape":
        if state["screen"]=="playing":
            back_to_menu()
        elif state["screen"] in ("menu","setup"):
            application.quit()

show_welcome()
app.run()
