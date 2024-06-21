#!/usr/bin/env python3

from flask import Flask, request, jsonify
import json
import os
import logging
from logging.handlers import RotatingFileHandler
from dynamic_streamer import DynamicStreamer
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import JWT_SECRET_KEY
import multiprocessing
import psutil
import time
from signal import signal, SIGINT, SIGTERM, SIGKILL
from sys import exit

host = os.environ.get("Host", "0.0.0.0")
port = os.environ.get("PORT", 5000)
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
jwt = JWTManager(app)

# Move utility functions to the top to ensure they are defined before use
def load_state(filename="stream_state.json"):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_state(pids, filename="stream_state.json"):
    try:
        with open(filename, 'w') as f:
            json.dump(list(pids), f)
            print(f'save state: {pids}')
    except FileNotFoundError:
        print(f'file not found: {pids}')
        return("No file found")


# pids_to_monitor = []
def setup_monitoring_logging():
    log_dir = 'home/ubuntu/logs/pipelines/mem_consumption'
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'memory_monitor.log')
    handler = RotatingFileHandler(log_file, maxBytes=20*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')
    handler.setFormatter(formatter)
    monitoring_logger = logging.getLogger('monitoring_logger')
    monitoring_logger.setLevel(logging.INFO)
    monitoring_logger.addHandler(handler)
    return monitoring_logger

monitoring_logger = setup_monitoring_logging()

def monitor_processes(pids, interval=5, logger=None):
    while True:
        if pids != None:
            for item in list(pids):
                pid, port_send, port_receive = item
                try:
                    process = psutil.Process(pid)
                    memory_usage = process.memory_info().rss / (1024 * 1024)
                    if logger:
                        logger.info(f"PID {pid} [Send: {port_send}, Receive: {port_receive}]: {memory_usage:.2f} MB")
                except psutil.NoSuchProcess:
                    if logger:
                        logger.info(f"Process {pid} terminated. Removing from monitoring list.")
                    pids.remove(item)
            time.sleep(interval)
    pass

def start_monitor():
    monitor_process = multiprocessing.Process(target=monitor_processes, args=(None, 5, monitoring_logger))
    monitor_process.start()
    return monitor_process


def shutdown_handler(signal_received, frame):
    # save_state(pids_to_monitor)
    try:
        os.remove("stream_state.json")
        print('SIGINT or CTRL-C detected. Exiting gracefully')
        exit(0)
    except FileNotFoundError:
        print('SIGINT or CTRL-C detected. Exiting gracefully')
        exit(0)

def start_dynamic_streamer(srt_source_uri, srt_sink_uri, srt_sink_uri_web):
    streamer = DynamicStreamer(srt_source_uri, srt_sink_uri, srt_sink_uri_web)
    streamer.start_streaming()

# signal(SIGKILL, shutdown_handler)

@app.route("/login", methods=['POST'])
def login():
    if not request.is_json:
        print(request)
        return jsonify({"msg": "Missing JSON in request"}), 400
    
    json_data = request.data
    data = json.loads(json_data)
    username = data['username']
    password = data['password']
    if username != 'admin' or password != 'password':
        return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200

@app.route("/start_stream", methods=['POST'])
@jwt_required()
def new_stream():
    pids = load_state()
    print(f'new_stream: {pids}')
    json_data = request.data
    data = json.loads(json_data)
    # print(f'data: {data}')
    port_transmit = data['port_transmit']
    port_receive = data['port_receive']
    port_receive_web = str(int(port_receive) + 2000)
    streamid = data['streamid']
    input_uri_auth = f"srt://:{port_transmit}"
    # output_uri_auth = f"srt://:{port_receive}"
    output_uri_auth = f"srt://:{port_receive}?streamid={streamid}"
    output_uri_auth_web = f"srt://:{port_receive_web}?streamid={streamid}"
    print(output_uri_auth_web)
    # print(f'port_transmit: {port_transmit}')
    # print(f'port_receive: {port_receive}')
    # print(f'streamid: {streamid}')
    for item in list(pids):
        pid, port_to_send, port_to_receive, port_to_receive_web = item
        if port_to_send == port_transmit and port_to_receive == port_receive and port_to_receive_web == port_receive_web:
                return jsonify(message="Pipeline already exists"),200 
    p = multiprocessing.Process(target=start_dynamic_streamer, args=(input_uri_auth, output_uri_auth, output_uri_auth_web))
    p.start()
    new_pid = [p.pid, port_transmit, port_receive, port_receive_web]
    pids_to_monitor.append(new_pid)
    # print(f'p.pid: {p.pid}')
    save_state(pids_to_monitor)
    return jsonify(message="Streaming started."), 200

@app.route("/stop_stream", methods=['POST'])
@jwt_required()
def stop_stream():
    pids = load_state()
    # print(f'stop_stream: {pids}')
    json_data = request.data
    data = json.loads(json_data)
    port_transmit = data['port_transmit']
    port_receive = data['port_receive']
    print(f'stop stream -> port transmit: {port_transmit}')
    print(f'stop stream -> port receive: {port_receive}')
    i = 0
    for item in list(pids):
        pid, port_to_send, port_to_receive, port_to_receive_web = item
        # print(pid, port_to_send, port_to_receive)
        # print(port_to_send == port_transmit)
        # print(port_transmit)
        # print(port_to_receive == port_receive)
        # print(port_receive)
        if port_to_send == port_transmit and port_to_receive == port_receive:
            try:
                process = psutil.Process(pid)
                # print(f'pids_to_monitor antes do p.terminate: {pids_to_monitor}')
                # print(f'item: {item}')
                # process.terminate()
                os.kill(pid, SIGKILL)
                pids_to_monitor.pop(i)
                print('stop_stream pids_to_monitor: {pids_to_monitor}')
                save_state(pids_to_monitor)
                # print(f'pids depois p.terminate: {pids_to_monitor}')
                return jsonify(message="Streaming stop."), 200
            except psutil.NoSuchProcess:
                pids_to_monitor.pop(i)
                save_state(pids_to_monitor)
                return jsonify(message="Couldn't find PID"), 400
        i += 1
    
    return jsonify(message="No pipeline running"), 200 


if __name__ == "__main__":
    try:
        os.remove("stream_state.json")
    except FileNotFoundError: 
        pass
    manager = multiprocessing.Manager()
    pids_to_monitor = manager.list(load_state())
    monitor_process = start_monitor() 
    app.run(host=host, port=port, debug=True)
