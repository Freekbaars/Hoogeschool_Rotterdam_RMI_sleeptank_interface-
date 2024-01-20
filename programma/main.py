# author: Freek Baars
# date: 19-01-2024
# version: 1.1.0
# python 3.12.1

import eel                     # Importeert de eel module om de webserver te starten
import serial.tools.list_ports # Importeert de serial module om de seriële poorten op te halen
import serial                  # Importeert de serial module om de seriële poort te openen
import threading               # Importeert de threading module om de seriële data uit te lezen
from threading import Lock     # Importeert de threading module om de seriële data uit te lezen
import time                    # Importeert de time module om de tijd te meten
import csv                     # Importeert de csv module om de data op te slaan in een CSV bestand
import os                      # Importeert de os module om de map pad te bepalen


eel.init('programma/web') # Initialiseert de webserver

# Globale variabelen
latest_Force = None
latest_angle_x = None
latest_angle_y = None
serial_instance = None
is_test_running = False

# Globale variabelen voor de CSV 
csv_bestandsnaam = "default_bestandsnaam"
csv_writer = None
csv_file = None
write_lock = Lock()
opslag_pad = os.getcwd()

# Globale variabelen voor sensorinstellingen
sensor_scalar = 1232 # 2kg 
sensor_unit_factor = 0.000001
sensor_eenheid = "G"

# Globale variabelen voor starttijd
start_tijd = None


def read_serial_data(): # Functie om de seriële data uit te lezen
    global start_tijd, is_test_running, serial_instance, latest_Force, latest_angle_x, latest_angle_y
    while is_test_running and serial_instance and serial_instance.isOpen():
        if serial_instance.in_waiting > 0:
            data = serial_instance.readline().decode().strip()
            parts = data.split(',')
            if len(parts) == 3:
                weight, angle_x, angle_y = parts
                calibrated_Force = format_data(weight)

                latest_Force = calibrated_Force
                latest_angle_x = angle_x
                latest_angle_y = angle_y

                if start_tijd is not None:
                    verstreken_ms = int((time.time() * 1000) - start_tijd)
                    verstreken_sec = verstreken_ms // 1000
                    ms = verstreken_ms % 1000
                    verstreken_tijd_str = f"{verstreken_sec}:{ms:03d}"
                else:
                    verstreken_tijd_str = "0:000"

                with write_lock:
                    if csv_writer is not None:
                        csv_writer.writerow([verstreken_tijd_str, calibrated_Force, angle_x, angle_y])


def format_data(raw_data, precision=2): # Functie om de Force data te kalibreren en te formatteren
    global sensor_scalar, sensor_unit_factor
    try:
        value = float(raw_data)
        calibrated_value = value * sensor_scalar
        unit_converted_value = calibrated_value * sensor_unit_factor
        return round(unit_converted_value, precision)
    except ValueError:
        return None


def create_unique_filename(base_path, base_name): # Functie om een unieke bestandsnaam te genereren als de gebruiker geen bestandsnaam opgeeft die al gebruikt is
    counter = 1
    base_name_without_extension = os.path.splitext(base_name)[0]  # Verwijdert de extensie (indien aanwezig)
    unique_name = os.path.join(base_path, base_name_without_extension + '.csv')

    while os.path.exists(unique_name):
        unique_name = os.path.join(base_path, f"{base_name_without_extension}_{counter}.csv")
        counter += 1

    return unique_name


@eel.expose
def update_sensor_instellingen(scalar, eenheid): # Functie om de sensorinstellingen te updaten vanuit JS naar Python
    global sensor_scalar, sensor_unit_factor, sensor_eenheid
    print(f"update_sensor_instellingen aangeroepen met scalar: {scalar}, eenheid: {eenheid}")

    try:
        sensor_scalar = float(scalar)

        if eenheid == "gram":
            sensor_unit_factor = 0.000001
            sensor_eenheid = "G"
        elif eenheid == "newton":
            sensor_unit_factor = 0.00000981
            sensor_eenheid = "N"
        return True
    except Exception as e:
        print(f"Fout in update_sensor_instellingen: {e}")
        return False


@eel.expose
def set_map_pad(pad): # Functie om de map pad te updaten vanuit JS naar Python
    global opslag_pad
    opslag_pad = pad   


def format_data(raw_data, scalar=sensor_scalar, offset=0.0, unit_factor=sensor_unit_factor, precision=2): # Functie om de data te kalibreren en te formatteren
    """
    Kalibreert en formateert de ruwe data van de sensor.

    :param raw_data: De ruwe data van de sensor als een string.
    :param scalar: De kalibratiefactor voor de sensor.
    :param offset: De offsetwaarde voor nul kalibratie.
    :param unit_factor: De factor om de eenheid te converteren (bijv. van gram naar kilogram).
    :param precision: Het aantal decimalen voor afronding.
    :return: De gekalibreerde en geformatteerde waarde.
    """
    try:
        # Converteer de ruwe data naar een float
        value = float(raw_data)

        # Pas kalibratie toe
        calibrated_value = (value - offset) * scalar

        # Converteer naar de gewenste eenheid
        unit_converted_value = calibrated_value * unit_factor

        # Rond af tot de gewenste precisie
        return round(unit_converted_value, precision)
    except ValueError:
        return None


@eel.expose
def get_serial_ports(): # Functie om de seriële poorten op te halen
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]
print(get_serial_ports())


@eel.expose
def open_serial_port(portVar): # Functie om de seriële poort te openen
    global serial_instance, is_test_running
    try:
        serial_instance = serial.Serial(portVar, baudrate=9600, timeout=1)
        print("Seriële poort geopend:", portVar)
        if not is_test_running:
            threading.Thread(target=read_serial_data, daemon=True).start()
            print("Seriële lees thread gestart")
        return True
    except Exception as e:
        print(f"Fout bij het openen van de poort {portVar}: {str(e)}")
        return False


@eel.expose
def get_latest_force_reading(): # Functie om de laatste krachtmeting op te halen uit de globale variabele en naar JS te sturen
    global latest_force_reading
    return latest_force_reading

@eel.expose
def get_latest_weight(): # Functie om de laatste krachtmeting op te halen uit de globale variabele en naar JS te sturen
    global latest_Force
    return latest_Force

@eel.expose
def get_latest_angle_x(): # Functie om de laatste hoekmeting om X op te halen uit de globale variabele en naar JS te sturen
    global latest_angle_x
    return latest_angle_x

@eel.expose
def get_latest_angle_y(): # Functie om de laatste hoekmeting om Y op te halen uit de globale variabele en naar JS te sturen
    global latest_angle_y
    return latest_angle_y


@eel.expose
def set_csv_bestandsnaam(bestandsnaam): # Functie om de CSV bestandsnaam te updaten vanuit JS naar Python
    global csv_bestandsnaam, opslag_pad
    csv_bestandsnaam = create_unique_filename(opslag_pad, bestandsnaam)
    print("Bestandsnaam voor CSV is ingesteld op:", csv_bestandsnaam)


@eel.expose
def start_test(): # Functie om de test te starten
    global is_test_running, csv_bestandsnaam, csv_file, csv_writer, start_tijd, sensor_eenheid, opslag_pad
    if not is_test_running:
        # Als opslag_pad niet is ingesteld, gebruik de huidige werkmap
        if not opslag_pad:
            opslag_pad = os.getcwd()

        # Genereer een unieke bestandsnaam
        base_name = os.path.basename(csv_bestandsnaam) if csv_bestandsnaam else "default_bestandsnaam"
        unique_csv_bestandsnaam = create_unique_filename(opslag_pad, base_name)

        # Volledige pad voor het CSV-bestand
        volledige_pad = os.path.join(opslag_pad, unique_csv_bestandsnaam)
        csv_file = open(volledige_pad, mode='w', newline='', encoding='utf-8')
        csv_writer = csv.writer(csv_file)
        force_column_header = f"Force [{sensor_eenheid}]"
        csv_writer.writerow(['Time [S]', force_column_header, 'Angle X [deg]', 'Angle Y [deg]'])

        start_tijd = time.time() * 1000  # Tijd in milliseconden
        is_test_running = True
        threading.Thread(target=read_serial_data, daemon=True).start()
        print("Test gestart met bestandsnaam:", unique_csv_bestandsnaam)
    else:
        print("Test kan niet worden gestart. Is test running:", is_test_running, "Bestandsnaam:", csv_bestandsnaam)

@eel.expose
def stop_test(): # Functie om de test te stoppen
    global is_test_running, csv_file, latest_force_reading
    if is_test_running:
        is_test_running = False
        latest_force_reading = None  # Reset de laatste krachtmeting
        if csv_file:
            csv_file.close()
            csv_file = None  # Reset csv_file na sluiting
        print("Test gestopt en CSV-bestand gesloten")
    else:
        print("Geen actieve test om te stoppen")



def close_callback(route, websockets): # Functie om de websocket verbinding te sluiten
    if not websockets:
        print("Websocket verbinding gesloten")
        exit()


eel.start('index.html', close_callback=close_callback) # Start de webserver en opent de webpagina