import os
import json
import time
from flask import Flask, render_template, request, jsonify
import serial
import serial.tools.list_ports
import threading

app = Flask(__name__)

# Real Database of Specific Gravities (g/cm³)
# Source: Scientific tables for minerals and precious metals
MINERAL_DB = [
    {"name": "24K Pure Gold", "type": "Metal", "min_sg": 19.2, "max_sg": 19.4, "ref_sg": 19.32},
    {"name": "22K Gold", "type": "Metal", "min_sg": 17.5, "max_sg": 18.0, "ref_sg": 17.7},
    {"name": "18K Gold", "type": "Metal", "min_sg": 15.2, "max_sg": 15.9, "ref_sg": 15.6},
    {"name": "14K Gold", "type": "Metal", "min_sg": 12.9, "max_sg": 14.6, "ref_sg": 13.5},
    {"name": "Platinum", "type": "Metal", "min_sg": 21.0, "max_sg": 21.5, "ref_sg": 21.45},
    {"name": "Fine Silver (99.9%)", "type": "Metal", "min_sg": 10.4, "max_sg": 10.6, "ref_sg": 10.49},
    {"name": "Sterling Silver (92.5%)", "type": "Metal", "min_sg": 10.2, "max_sg": 10.4, "ref_sg": 10.36},
    {"name": "Copper", "type": "Metal", "min_sg": 8.8, "max_sg": 9.0, "ref_sg": 8.96},
    {"name": "Brass / Fake Gold", "type": "Metal", "min_sg": 8.4, "max_sg": 8.7, "ref_sg": 8.5},
    {"name": "Lead (Fake Gold core)", "type": "Metal", "min_sg": 11.2, "max_sg": 11.4, "ref_sg": 11.34},
    {"name": "Tungsten (Fake Gold core)", "type": "Metal", "min_sg": 19.0, "max_sg": 19.3, "ref_sg": 19.25}, # Very close to gold!
    {"name": "Diamond", "type": "Stone", "min_sg": 3.50, "max_sg": 3.53, "ref_sg": 3.52},
    {"name": "Cubic Zirconia (Fake Diamond)", "type": "Stone", "min_sg": 5.50, "max_sg": 6.00, "ref_sg": 5.80},
    {"name": "Ruby / Sapphire", "type": "Stone", "min_sg": 3.95, "max_sg": 4.03, "ref_sg": 4.00},
    {"name": "Emerald", "type": "Stone", "min_sg": 2.67, "max_sg": 2.78, "ref_sg": 2.72},
    {"name": "Quartz / Amethyst", "type": "Stone", "min_sg": 2.64, "max_sg": 2.66, "ref_sg": 2.65},
    {"name": "Glass (Fake Gem)", "type": "Stone", "min_sg": 2.40, "max_sg": 2.80, "ref_sg": 2.50},
    {"name": "Pyrite (Fool's Gold)", "type": "Stone", "min_sg": 4.95, "max_sg": 5.10, "ref_sg": 5.00}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/calculate_sg', methods=['POST'])
def calculate_sg():
    """
    Real Physics: Specific Gravity = Weight in Air / (Weight in Air - Weight in Water)
    This is the standard hydrostatic method used by jewelers.
    """
    try:
        data = request.json
        weight_air = float(data.get('weight_air', 0))
        weight_water = float(data.get('weight_water', 0))

        if weight_air <= 0 or weight_water <= 0:
            return jsonify({"error": "Miisaanka (Weight) waa inuu ka weyn yahay eber."})
        
        if weight_water >= weight_air:
            return jsonify({"error": "Miisaanka biyaha (Wet) waa inuu ka yaryahay miisaanka hawada (Dry)."})

        # Archimedes Principle Calculation
        volume = weight_air - weight_water
        sg = weight_air / volume

        # Find matching materials
        matches = []
        for mineral in MINERAL_DB:
            if mineral['min_sg'] <= sg <= mineral['max_sg']:
                matches.append(mineral)

        # Sort matches by how close they are to the reference SG
        matches.sort(key=lambda x: abs(x['ref_sg'] - sg))

        return jsonify({
            "specific_gravity": round(sg, 3),
            "volume_cm3": round(volume, 3),
            "matches": matches,
            "warning": "Tungsten waxay leedahay cufnaan (SG) la mid ah Dahabka. Fadlan isticmaal Acid Test ama XRF si aad u xaqiijiso." if 19.0 <= sg <= 19.4 else ""
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/scan_ports', methods=['GET'])
def scan_ports():
    """
    Real Hardware Integration: Scans for actual connected COM/Serial ports.
    """
    ports = serial.tools.list_ports.comports()
    port_list = []
    for port, desc, hwid in sorted(ports):
        port_list.append({"port": port, "description": desc})
    
    # If no real ports, provide a mock one for testing
    if not port_list:
        port_list.append({"port": "COM_MOCK", "description": "Virtual Test Port (No hardware found)"})
        
    return jsonify({"ports": port_list})

@app.route('/api/read_sensor', methods=['POST'])
def read_sensor():
    """
    Reads data from a connected serial device (like an electronic scale or XRF machine).
    """
    data = request.json
    port = data.get('port')
    baudrate = int(data.get('baudrate', 9600))
    
    if port == "COM_MOCK":
        # Simulate a scale output if no real hardware is attached
        import random
        simulated_weight = round(random.uniform(5.0, 50.0), 3)
        return jsonify({"status": "success", "raw_data": f"+{simulated_weight} g", "parsed_value": simulated_weight})

    try:
        # Real Serial Connection
        ser = serial.Serial(port, baudrate, timeout=2)
        # Give it a moment to connect
        time.sleep(0.5)
        # Read a line from the sensor
        raw_bytes = ser.readline()
        ser.close()
        
        if not raw_bytes:
             return jsonify({"error": "No data received from sensor. Is it turned on?"})
             
        raw_str = raw_bytes.decode('utf-8', errors='ignore').strip()
        
        return jsonify({
            "status": "success",
            "raw_data": raw_str
        })
    except Exception as e:
        return jsonify({"error": f"Serial Port Error: {str(e)}"})

if __name__ == '__main__':
    print("PreciousDetect Pro is starting on http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
