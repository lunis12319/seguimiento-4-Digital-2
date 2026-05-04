from machine import Pin, I2C, PWM, Timer
import framebuf, time

try:
    import urandom
except:
    import random as urandom

# OLED  
class OLED:
    def __init__(self, i2c, addr=0x3C):
        self.i2c = i2c
        self.addr = addr
        self.buffer = bytearray(128 * 64 // 8)
        self.fb = framebuf.FrameBuffer(self.buffer, 128, 64, framebuf.MONO_VLSB)

        for cmd in (
            0xAE,0x20,0x00,0x40,0xA1,0xC8,
            0xA8,0x3F,0xD3,0x00,0xD5,0x80,
            0xD9,0xF1,0xDA,0x12,0xDB,0x40,
            0x8D,0x14,0xAF):
            self.cmd(cmd)

    def cmd(self, c):
        self.i2c.writeto(self.addr, bytearray([0x80, c]))

    def show(self):
        self.cmd(0x21); self.cmd(0); self.cmd(127)
        self.cmd(0x22); self.cmd(0); self.cmd(7)
        self.i2c.writeto(self.addr, b'\x40' + self.buffer)

    def fill(self, c): self.fb.fill(c)
    def text(self, txt, x, y): self.fb.text(txt, x, y)
    def fill_rect(self, x, y, w, h, c): self.fb.fill_rect(x, y, w, h, c)
    def pixel(self, x, y, c): self.fb.pixel(x, y, c) #Dibuja un solo píxel (usado para la manzana detallad

# BOTONES 
class BotonSimple: #plantilla objeto POO
    def __init__(self, pin, reboteMs=50):
        self.pin = pin
        self.reboteMs = reboteMs
        self.ultimoEstado = True
        self.ultimoCambio = 0

    def estaPresionado(self):
        actual = self.pin.value()
        ahora = time.ticks_ms()
        if actual != self.ultimoEstado:
            if time.ticks_diff(ahora, self.ultimoCambio) > self.reboteMs:
                self.ultimoEstado = actual
                self.ultimoCambio = ahora
                return actual == 0
        return False

# HARDWARE 
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
oled = OLED(i2c)

botonArriba = BotonSimple(Pin(32, Pin.IN, Pin.PULL_UP))
botonAbajo = BotonSimple(Pin(33, Pin.IN, Pin.PULL_UP))
botonIzq = BotonSimple(Pin(27, Pin.IN, Pin.PULL_UP))
botonDer = BotonSimple(Pin(14, Pin.IN, Pin.PULL_UP))
botonStart = BotonSimple(Pin(25, Pin.IN, Pin.PULL_UP))
botonExtra = BotonSimple(Pin(26, Pin.IN, Pin.PULL_UP))

# BUZZER 
buzzer = PWM(Pin(13))
timer_buzzer = Timer(0)

def apagar_buzzer(t):
    buzzer.duty(0)

def tono(freq, dur):
    buzzer.freq(freq)
    buzzer.duty(200)
    timer_buzzer.init(mode=Timer.ONE_SHOT, period=dur, callback=apagar_buzzer)

def beep_menu(): tono(900,40)
def beep_ok(): tono(1200,60)
def beep_fail(): tono(400,200)

# ESTADOS 
ESTADO_MENU = 0
ESTADO_JUEGO = 1
ESTADO_PAUSA = 2
ESTADO_FIN = 3

estado = ESTADO_MENU
modo = 0

MAXX = 128
MAXY = 64
TAM = 4

# VARIABLES JUEGO 
serpiente = [(40,30),(36,30),(32,30)]
direccion = (4,0)
comida = (60,30)
obstaculos = []

puntaje = 0
ultimoMovimiento = time.ticks_ms()
intervaloVelocidad = 250

tiempo_inicio = 0
tiempo_limite = 30
manzanas_comidas = 0

# FUNCIONES 
def generarObstaculos():
    global obstaculos
    obstaculos = []
    cantidad = 4 + modo*2
    for _ in range(cantidad):
        obstaculos.append((urandom.randint(0,30)*4, urandom.randint(6,15)*4))

def generarComida():
    global comida
    while True:
        x = urandom.randint(0,30)*4
        y = urandom.randint(6,15)*4
        if (x,y) not in serpiente:
            comida = (x,y)
            break

def dibujar():
    for p in serpiente:
        oled.fill_rect(p[0], p[1], TAM, TAM, 1)

    x,y = comida

    if (time.ticks_ms() // 300) % 2 == 0:
        oled.pixel(x+1, y, 1)
        oled.pixel(x+2, y, 1)
        oled.pixel(x+3, y, 1)

        oled.pixel(x, y+1, 1)
        oled.pixel(x+1, y+1, 1)
        oled.pixel(x+2, y+1, 1)
        oled.pixel(x+3, y+1, 1)
        oled.pixel(x+4, y+1, 1)

        oled.pixel(x, y+2, 1)
        oled.pixel(x+1, y+2, 1)
        oled.pixel(x+2, y+2, 1)
        oled.pixel(x+3, y+2, 1)
        oled.pixel(x+4, y+2, 1)

        oled.pixel(x, y+3, 1)
        oled.pixel(x+1, y+3, 1)
        oled.pixel(x+2, y+3, 1)
        oled.pixel(x+3, y+3, 1)
        oled.pixel(x+4, y+3, 1)

        oled.pixel(x+1, y+4, 1)
        oled.pixel(x+2, y+4, 1)
        oled.pixel(x+3, y+4, 1)

        oled.pixel(x+2, y-1, 1)
        oled.pixel(x+3, y-1, 1)

    for o in obstaculos:
        oled.fill_rect(o[0], o[1], TAM, TAM, 1)

def mover():
    global puntaje, intervaloVelocidad, manzanas_comidas
    x,y = serpiente[0]
    dx,dy = direccion
    nueva = (x+dx, y+dy)

    if nueva[0]<0 or nueva[0]>=MAXX or nueva[1]<10 or nueva[1]>=MAXY:
        return False

    for o in obstaculos:
        if abs(nueva[0]-o[0])<TAM and abs(nueva[1]-o[1])<TAM:
            return False

    serpiente.insert(0,nueva)

    
    if abs(nueva[0]-comida[0])<TAM and abs(nueva[1]-comida[1])<TAM:
        puntaje += 10
        manzanas_comidas += 1
        tono(1200,50)
        generarComida()
        generarObstaculos()

        if modo == 2:
            intervaloVelocidad = max(50, intervaloVelocidad-5)
    else:
        serpiente.pop()

    return True

def reiniciar():
    global serpiente, direccion, puntaje, intervaloVelocidad
    global tiempo_inicio, manzanas_comidas

    serpiente = [(40,30),(36,30),(32,30)]
    direccion = (4,0)
    puntaje = 0
    intervaloVelocidad = 250
    manzanas_comidas = 0

    if modo == 1:
        intervaloVelocidad = 150
        tiempo_inicio = time.ticks_ms()
    elif modo == 2:
        intervaloVelocidad = 100

    generarObstaculos()
    generarComida()

# LOOP 
while True:
    oled.fill(0)

    if botonExtra.estaPresionado():
        estado = ESTADO_MENU

    if estado == ESTADO_MENU:
        opciones = ["Clasico","Tiempo","Hardcore"]
        oled.text("MENU",40,0)

        for i,n in enumerate(opciones):
            oled.text((">" if i==modo else " ")+n, 20, 20+i*10)

        if botonArriba.estaPresionado():
            modo=(modo-1)%3; beep_menu()
        if botonAbajo.estaPresionado():
            modo=(modo+1)%3; beep_menu()
        if botonStart.estaPresionado():
            estado=ESTADO_JUEGO
            reiniciar()

    elif estado == ESTADO_JUEGO:

        if botonStart.estaPresionado():
            estado = ESTADO_PAUSA
            beep_menu()

        if botonArriba.estaPresionado(): direccion=(0,-4)
        if botonAbajo.estaPresionado(): direccion=(0,4)
        if botonIzq.estaPresionado(): direccion=(-4,0)
        if botonDer.estaPresionado(): direccion=(4,0)

        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, ultimoMovimiento) > intervaloVelocidad:
            if not mover():
                beep_fail()
                estado = ESTADO_FIN
            ultimoMovimiento = ahora

        dibujar()
        oled.text("Pts:"+str(puntaje),0,0)

        if modo == 1:
            tiempo_actual = (time.ticks_ms() - tiempo_inicio)//1000
            restante = max(0, tiempo_limite - tiempo_actual)
            oled.text("T:"+str(restante),90,0)

            if restante <= 0:
                estado = ESTADO_FIN

    elif estado == ESTADO_PAUSA:
        oled.text("PAUSA",40,20)
        oled.text("Start=seguir",10,40)
        oled.text("Extra=menu",10,55)

        if botonStart.estaPresionado():
            estado = ESTADO_JUEGO
            beep_ok()

    elif estado == ESTADO_FIN:
        oled.text("FIN",50,20)
        oled.text("Pts:"+str(puntaje),30,40)
        oled.text("M:"+str(manzanas_comidas),30,50)

        if botonStart.estaPresionado():
            estado = ESTADO_MENU

    oled.show()
    time.sleep_ms(20)