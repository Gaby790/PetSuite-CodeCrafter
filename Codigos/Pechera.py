# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
from random import randint

import ssl
import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT
import analogio
import board
import adafruit_bme680

from adafruit_msa3xx import MSA311

### WiFi ###

# Add a secrets.py to your filesystem that has a dictionary called secrets with "ssid" and
# "password" keys with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.
# pylint: disable=no-name-in-module,wrong-import-order
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Set your Adafruit IO Username and Key in secrets.py
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = secrets["aio_username"]
aio_key = secrets["aio_key"]

print("Connecting to %s" % secrets["ssid"])
wifi.radio.connect(secrets["ssid"], secrets["password"])
print("Connected to %s!" % secrets["ssid"])

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("Connected to Adafruit IO!  Listening for commands changes...")
    # Subscribe to changes on a feed named commands.
    client.subscribe("temperatura")
    client.subscribe("gas")
    client.subscribe("humidity")
    client.subscribe("pressure")
    client.subscribe("altitude")
    client.subscribe("contadordepasos")

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))


def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))


# pylint: disable=unused-argument
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")


# pylint: disable=unused-argument
def message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    print("Feed {0} received new value: {1}".format(feed_id, payload))


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)

# Initialize a new MQTT Client object
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=secrets["aio_username"],
    password=secrets["aio_key"],
    socket_pool=pool,
    ssl_context=ssl.create_default_context(),
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Connect the callback methods defined above to Adafruit IO
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = message

# Connect to Adafruit IO
print("Connecting to Adafruit IO...")
io.connect()
# Configuración del pin del sensor de pulso
pulse_sensor_pin = board.IO35
pulse_sensor = analogio.AnalogIn(pulse_sensor_pin)

# Configuración del umbral de frecuencia cardíaca
threshold = 500 # Ajusta este valor según sea necesario

i2c = board.I2C()
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, debug=False)
msa = MSA311(i2c)

# Establecer la presión al nivel del mar para su ubicación esto para obtener la medida más
# precisa (recuerde que estos sensores solo pueden inferir la altitud en función de la presión
# y necesitan un punto de calibración establecido.)
sensor.sea_level_pressure = 1013.25 

# Se suele agregar una compensación para la temperatura del sensor. Puede variar.
temperature_offset = -5

umbral_pasos = 5.0  # Ajusta este valor según sea necesario
umbral_tiempo = 1.0  # Ajusta este valor según sea necesario
tiempo_anterior = time.monotonic()

contador_pasos = 0

last = 0

while True:
    
    # Read sensor data
    Temperature = sensor.temperature
    Gas = sensor.gas
    Humidity = sensor.humidity
    Pressure = sensor.pressure
    Altitude = sensor.altitude
    Acelerometre = msa.acceleration
    
    # Print sensor data
    print('Temperature: {} grados C'.format(Temperature))
    print('Gas: {} Ohms'.format(Gas))
    print('Humidity: {}%'.format(Humidity))
    print('Pressure: {}hPa'.format(Pressure))
    print("Altitude = %0.2f metros" % Altitude)
    print('-------------------------------------------------------')
    time.sleep(1)
    
    #**************************************************
    x, y, z = msa.acceleration

    # Calcula la magnitud de la aceleración en el eje Z (vertical)
    magnitud_z = abs(z)

    # Comprueba si se ha superado el umbral de cambio en el eje Z
    if magnitud_z > umbral_pasos:
        # Comprueba la orientación para reducir falsas detecciones
        if abs(x) < 2.0 and abs(y) < 2.0:
            # Comprueba si ha pasado suficiente tiempo desde el último paso
            tiempo_actual = time.monotonic()
            if tiempo_actual - tiempo_anterior > umbral_tiempo:
                contador_pasos += 1
                tiempo_anterior = tiempo_actual
                print("¡Paso detectado! Contador de pasos:", contador_pasos)
    time.sleep(0.80)
    
    if (time.monotonic() -last) >=60:
        print("Acabo de publicar...")
        io.publish("Temperature", Temperature)
        io.publish("Gas", Gas)
        io.publish("Humidity", Humidity)
        io.publish("Pressure", Pressure)
        io.publish("Altitude", Altitude)
        io.publish("ContadorDePasos", contador_pasos)
        last = time.monotonic()

