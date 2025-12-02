from machine import Pin
import time
import ajnlte
import network
import requests
from picographics import PicoGraphics, DISPLAY_PICO_DISPLAY_2, PEN_P4
from pimoroni import RGBLED

display = PicoGraphics(display=DISPLAY_PICO_DISPLAY_2, pen_type=PEN_P4, rotate=0)

display.set_backlight(0.5)
display.set_font("bitmap8")

button_a = Pin(12, Pin.IN, Pin.PULL_UP)
button_b = Pin(13, Pin.IN, Pin.PULL_UP)
button_x = Pin(14, Pin.IN, Pin.PULL_UP)
button_y = Pin(15, Pin.IN, Pin.PULL_UP)

led = RGBLED(28, 27, 26)
led.set_rgb(0, 0, 0)

WHITE = display.create_pen(255, 255, 255)
BLACK = display.create_pen(0, 0, 0)
CYAN = display.create_pen(0, 255, 255)
MAGENTA = display.create_pen(255, 0, 255)
YELLOW = display.create_pen(255, 255, 0)
RED = display.create_pen(255, 0, 0)
GREEN = display.create_pen(0, 255, 0)
BLUE = display.create_pen(0, 0, 255)

# sets up a handy function we can call to clear the screen
def clear():
    display.set_pen(BLACK)
    led.set_rgb(0, 0, 0)
    display.clear()
    display.update()

clear()

display.set_pen(YELLOW)

lte_text = f'LTE: connecting'
width = display.measure_text(lte_text, 1)
display.text(lte_text, 10, 10, 240, 1)
wifi_text = f'Wifi: connecting'
width = display.measure_text(wifi_text, 1)
display.text(wifi_text, 310 - width, 10, 240, 1)
display.update()

MOBILE_APN = "data.lycamobile.co.uk"

def test_inet():
    req = requests.get("https://jsonplaceholder.typicode.com/todos/1")
    print(req.json())

con = ajnlte.LTE(MOBILE_APN, verbose=False)
con.connect()

clear()
display.set_pen(GREEN)
lte_text = f'LTE: {con.operator}'
width = display.measure_text(lte_text, 1)
display.text(lte_text, 10, 10, 240, 1)
wifi_text = f'Wifi: connecting'
width = display.measure_text(wifi_text, 1)
display.set_pen(YELLOW)
display.text(wifi_text, 310 - width, 10, 240, 1)
display.update()

wlan = network.WLAN(network.STA_IF, pin_on=32, pin_out=35, pin_in=35, pin_wake=35, pin_clock=34, pin_cs=33)

# connect to wifi
wlan.active(True)
wlan.connect("Brian", "Hh2fxurgwj!")
while wlan.isconnected() is False:
    print('Waiting for connection...')
    time.sleep(1)

clear()
display.set_pen(GREEN)
lte_text = f'LTE: {con.operator}'
width = display.measure_text(lte_text, 1)
display.text(lte_text, 10, 10, 240, 1)
wifi_text = f'Wifi: {wlan.config('ssid')}'
width = display.measure_text(wifi_text, 1)
display.text(wifi_text, 310 - width, 10, 240, 1)
display.update()

while True:
    msgs = con.get_messages()
    clear()
    display.set_pen(WHITE)
    sender = msgs[0]['sender']
    timestamp = msgs[0]['timestamp'][:-3]
    message = msgs[0]['formatted_message']
    display.text(sender, 10, 50, 300, 1)
    width = display.measure_text(timestamp, 1)
    display.text(f'{timestamp}', 310 - width, 50, 300, 1)
    display.text(message, 10, 80, 300, 1)
    display.set_pen(GREEN)
    lte_text = f'LTE: {con.operator}'
    width = display.measure_text(lte_text, 1)
    display.text(lte_text, 10, 10, 240, 1)
    wifi_text = f'Wifi: {wlan.config('ssid')}'
    width = display.measure_text(wifi_text, 1)
    display.text(wifi_text, 310 - width, 10, 240, 1)
    display.update()
    time.sleep(10)
