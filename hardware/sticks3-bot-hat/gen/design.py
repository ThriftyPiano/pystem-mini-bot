# Single source of truth for the StickS3 Bot HAT v2: every component, its
# footprint, and its pad-to-net connectivity. gen_pcb.py and gen_sch.py both
# consume this table, so schematic and board cannot disagree.
#
# v3 = 46x39mm: right-angle HAT2 header (stick lies flat), servo/sensor
# headers in two rows, 5.5x2.1 barrel jack for the battery box (which has
# its own switch, so no power switch on board). Keeps the 6V->5V buck (the StickS3's 5V_IN
# must never see the raw 6V pack: its internal power chips are 5V parts and
# fresh alkalines sit at 6.4V). Drops v1's I2C pull-ups (the GY-521 IMU
# module carries its own), the Grove port, and the boot button (the stick
# has its own buttons). design_v1_buck.py preserves the full v1.
#
# v5: J1 rows swapped (see the HAT2 note below); routing around J1 redone
# by gen/tools/rework_v5_j1rows.py, nothing else moved.
#
# v4: sensor headers follow the LM393 sensor modules' pin order (VCC GND D0
# A0) so a straight Dupont cable works: ENC = V G D0, COLOR = V G - A0
# (4 pins, D0 position unused). COLOR B became DIST: a 4-pin HC-SR04 header
# (5V TRIG ECHO GND) fed from the buck's 5 V, ECHO through a 1k/2k divider
# (R4/R5) so the 5 V echo pulse lands at 3.3 V on G8. TRIG uses G2, which
# was free. M2.5 mounting holes became M3. The power LED moved right of the
# DIST header. Board size unchanged.
#
# HAT2 socket as it meets J1 (verified on hardware, 2026-09-19; the first
# batch had the rows swapped). Stick lies flat, screen up, socket end on the
# header. J1's odd pads (square pad 1, the row farther from the board edge)
# feed the header's UPPER pins, which land on the stick's GPIO row; the even
# pads (row nearest the edge) feed the LOWER pins = the stick's power row.
# Columns run from the pin-1 end:
#   J1 odd  (upper pins): 1 G5  | 3 G4     | 5 G6   | 7 G7  | 9 G43 | 11 G44 | 13 G2  | 15 G3
#   J1 even (lower pins): 2 GND | 4 EXT_5V | 6 BOOT | 8 G1  | 10 G8 | 12 BAT | 14 3V3 | 16 5V_IN
# (M5Stack's own table numbers the socket the other way round: their odd
# pins are the power row. Do not copy it into J1 without this mapping.)
#
# Signal plan (GPIO roles chosen so header pin order matches connector order,
# which keeps the fan-out crossing-free; COLOR needs ADC1 = GPIO1..10):
#   G5=SERVO_A (left wheel)   G4=SERVO_B (right wheel)
#   G6=HEAD_PAN               G7=HEAD_TILT
#   G43=ENC_A                 G44=ENC_B
#   G1=COLOR (ADC1_CH0)       G8=ECHO (HC-SR04, via divider)   G2=TRIG
#   IMU/I2C dropped — the stick has a BMI270 inside

BOARD_L = 50.0   # left edge, mm (KiCad page coords)
BOARD_T = 50.0   # top edge
BOARD_W = 48.0
BOARD_H = 33.0

NETS = [
    "GND", "VSERVO", "+5V", "+3V3",
    "SW_NODE", "BST", "LED_K",
    "SERVO_A", "SERVO_B", "PAN", "TILT",
    "ENC_A", "ENC_B", "COLOR",
    "TRIG", "ECHO_5V", "ECHO",   # HC-SR04: ECHO_5V is the sensor side of the divider
]

STD_FP = "std"      # KiCad bundled library
LOCAL_FP = "local"  # ../sticks3-bot-hat.pretty

# ref: (symbol_lib, symbol_name, value, fp_lib_kind, fp_lib, fp_name,
#       (x, y, rot), {pad: net}, silk_label or None)
COMPONENTS = {
    # --- StickS3 socket (stick body overhangs the top board edge) ------
    "J1": ("Connector_Generic", "Conn_02x08_Odd_Even", "HAT2_StickS3",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_2x08_P2.54mm_Horizontal",
           (57.5, 55.5, 90),
           {"1": "SERVO_A", "2": "GND", "3": "SERVO_B", "4": None,
            "5": "PAN", "6": None, "7": "TILT", "8": "COLOR",
            "9": "ENC_A", "10": "ECHO", "11": "ENC_B", "12": None,
            "13": "TRIG", "14": "+3V3", "15": None, "16": "+5V"},
           "StickS3"),

    # --- Servo headers (S | V+ | G), 6 V battery rail ------------------
    "J2": ("Connector_Generic", "Conn_01x03", "SERVO_A",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
           (57.3, 76.2, 90),
           {"1": "SERVO_A", "2": "VSERVO", "3": "GND"}, "WHEEL A"),
    "J3": ("Connector_Generic", "Conn_01x03", "SERVO_B",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
           (66.1, 76.2, 90),
           {"1": "SERVO_B", "2": "VSERVO", "3": "GND"}, "WHEEL B"),
    "J4": ("Connector_Generic", "Conn_01x03", "HEAD_PAN",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
           (74.9, 76.2, 90),
           {"1": "PAN", "2": "VSERVO", "3": "GND"}, "PAN"),
    "J5": ("Connector_Generic", "Conn_01x03", "HEAD_TILT",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
           (83.7, 76.2, 90),
           {"1": "TILT", "2": "VSERVO", "3": "GND"}, "TILT"),

    # --- Sensor headers, pin order = LM393 module order (VCC GND D0 A0) ---
    # ENC/COLOR are 3V3 only (S3 pins not 5V-tolerant). DIST is the HC-SR04
    # (VCC TRIG ECHO GND), 5 V from the buck, ECHO divided down by R4/R5.
    "J6": ("Connector_Generic", "Conn_01x03", "ENC_A",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
           (57.3, 71.0, 90),
           {"1": "+3V3", "2": "GND", "3": "ENC_A"}, "ENC A"),
    "J7": ("Connector_Generic", "Conn_01x03", "ENC_B",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical",
           (66.1, 71.0, 90),
           {"1": "+3V3", "2": "GND", "3": "ENC_B"}, "ENC B"),
    "J8": ("Connector_Generic", "Conn_01x04", "COLOR",
           STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical",
           (74.9, 71.0, 90),
           {"1": "+3V3", "2": "GND", "3": None, "4": "COLOR"}, "COLOR"),
    "J10": ("Connector_Generic", "Conn_01x04", "DIST",
            STD_FP, "Connector_PinHeader_2.54mm", "PinHeader_1x04_P2.54mm_Vertical",
            (86.24, 71.0, 90),
            {"1": "+5V", "2": "TRIG", "3": "ECHO_5V", "4": "GND"}, "DIST"),
    # HC-SR04 ECHO level shift: 5 V * 2k / (1k + 2k) = 3.3 V at G8
    "R4": ("Device", "R", "1k",
           STD_FP, "Resistor_SMD", "R_0603_1608Metric",
           (91.5, 74.4, 270), {"1": "ECHO_5V", "2": "ECHO"}, None),
    "R5": ("Device", "R", "2k",
           STD_FP, "Resistor_SMD", "R_0603_1608Metric",
           (93.86, 74.4, 270), {"1": "ECHO", "2": "GND"}, None),

    # --- Power input: 4xAA box (own switch) with 5.5x2.1 barrel plug ----
    "J11": ("Connector", "Barrel_Jack", "DC_6V_5525",
            STD_FP, "Connector_BarrelJack", "BarrelJack_Horizontal",
            (86.0, 64.0, 270),
            {"1": "VSERVO", "2": "GND", "3": None}, "6V IN"),

    # --- Buck: 6 V -> 5.0 V into the stick's 5V_IN ---------------------
    "U1": ("Regulator_Switching", "AP63205WU", "AP63205",
           STD_FP, "Package_TO_SOT_SMD", "TSOT-23-6",
           (56.6, 61.8, 180),
           {"1": "+5V",      # FB tied to VOUT (fixed 5 V version)
            "2": "VSERVO",   # EN = VIN
            "3": "VSERVO",   # VIN
            "4": "GND",
            "5": "SW_NODE",
            "6": "BST"}, None),
    "L1": ("Device", "L", "6.8uH",
           STD_FP, "Inductor_SMD", "L_Bourns_SRN6045TA",
           (63.7, 65.3, 0),
           {"1": "SW_NODE", "2": "+5V"}, None),
    "C1": ("Device", "C", "10uF/25V",
           STD_FP, "Capacitor_SMD", "C_0805_2012Metric",
           (53.6, 65.6, 0), {"1": "VSERVO", "2": "GND"}, None),
    "C3": ("Device", "C", "100nF",
           STD_FP, "Capacitor_SMD", "C_0603_1608Metric",
           (61.5, 60.4, 0), {"1": "BST", "2": "SW_NODE"}, None),
    "C4": ("Device", "C", "22uF/25V",
           STD_FP, "Capacitor_SMD", "C_1206_3216Metric",
           (68.6, 66.0, 90), {"1": "+5V", "2": "GND"}, None),
    "C5": ("Device", "C", "22uF/25V",
           STD_FP, "Capacitor_SMD", "C_1206_3216Metric",
           (81.8, 67.7, 0), {"1": "+5V", "2": "GND"}, None),
    # Bulk for servo stalls, right on the 6 V rail
    "C7": ("Device", "C_Polarized", "470uF/16V",
           STD_FP, "Capacitor_THT", "CP_Radial_D8.0mm_P3.50mm",
           (72.7, 63.2, 0), {"1": "VSERVO", "2": "GND"}, None),

    # --- Power LED -------------------------------------------------------
    "R3": ("Device", "R", "22k",
           STD_FP, "Resistor_SMD", "R_0603_1608Metric",
           (96.6, 71.3, 270), {"1": "+5V", "2": "LED_K"}, None),
    # R3 = 22k keeps the LED at ~0.14 mA: a faint power indicator, not a
    # searchlight. 1k (~3 mA) was far too bright on the first JLCPCB batch.
    "D1": ("Device", "LED", "GREEN",
           STD_FP, "LED_SMD", "LED_0603_1608Metric",
           (96.6, 74.4, 90), {"1": "GND", "2": "LED_K"}, None),

    # --- Mounting holes -------------------------------------------------
    "H1": ("Mechanical", "MountingHole", "M3",
           STD_FP, "MountingHole", "MountingHole_3.2mm_M3", (52.7, 52.7, 0), {}, None),
    "H2": ("Mechanical", "MountingHole", "M3",
           STD_FP, "MountingHole", "MountingHole_3.2mm_M3", (95.3, 52.7, 0), {}, None),
    "H3": ("Mechanical", "MountingHole", "M3",
           STD_FP, "MountingHole", "MountingHole_3.2mm_M3", (52.7, 79.5, 0), {}, None),
    "H4": ("Mechanical", "MountingHole", "M3",
           STD_FP, "MountingHole", "MountingHole_3.2mm_M3", (95.3, 79.5, 0), {}, None),
}

# BOM for JLCPCB assembly (refs grouped by orderable part).
# LCSC numbers: U1/L1 verified; passives are JLC "basic" classics — have
# JLCPCB's BOM matcher confirm them at order time. THT connectors/switches
# are generic; pick in-stock equivalents in the JLC parts library.
BOM = [
    ("U1",  "AP63205WU-7", "Diodes Inc", "TSOT-23-6", "C2071056", "3.8-32V in, 5V/2A sync buck"),
    ("L1",  "SWPA6045S6R8MT", "Sunlord", "6045", "C57254", "6.8uH 3A power inductor"),
    ("C1",  "CL21A106KAYNNNE", "Samsung", "0805", "C15850", "10uF 25V X5R"),
    ("C3",  "CL10B104KB8NNNC", "Samsung", "0603", "C1591", "100nF 50V X7R"),
    ("C4,C5", "CL31A226KAHNNNE", "Samsung", "1206", "C12891", "22uF 25V X5R"),
    ("C7",  "470uF 16V radial D8xH11.5 P3.5", "generic", "THT", "", "bulk for servo stalls"),
    ("R3",  "0603WAF2202T5E", "UniOhm", "0603", "C4190", "22k 1% (~0.14 mA: dim power LED)"),
    ("R4",  "0603WAF1001T5E", "UniOhm", "0603", "C21190", "1k 1% (HC-SR04 ECHO divider, series)"),
    ("R5",  "0603WAF2001T5E", "UniOhm", "0603", "C4109", "2k 1% (HC-SR04 ECHO divider, to GND)"),
    ("D1",  "0603 green LED", "generic", "0603", "", "power indicator"),
    ("J1",  "2x8 pin header 2.54mm male RIGHT-ANGLE (90 deg)", "generic", "THT", "", "plugs into StickS3 HAT2 socket, stick lies flat"),
    ("J2,J3,J4,J5,J6,J7", "1x3 pin header 2.54mm male vertical", "generic", "THT", "", "servo / encoder headers"),
    ("J8,J10", "1x4 pin header 2.54mm male vertical", "generic", "THT", "", "COLOR (V G - A0) / DIST (HC-SR04) headers"),
    ("J11", "DC barrel jack 5.5x2.1 horizontal (PJ-102A type)", "generic", "THT", "", "battery box plugs in, center = +6V"),
]
