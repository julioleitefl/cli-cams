import subprocess
import requests
import json
import time
import customtkinter as ctk

URL_API = "https://spyskytech.net/"
WORKING_DIRECTORY = "C:\\gstreamer\\1.0\\msvc_x86_64\\bin"


def execute_pipeline(data):
    gstreamer_pipeline_generate = f"gst-launch-1.0 rtspsrc latency=0 tcp-timeout=200000 drop-on-latency=true location=rtsp://{data['username']}:{data['password']}@{data['ip_camera']} ! decodebin ! videoconvert ! mfh265enc low-latency=true ! mpegtsmux ! srtsink uri=srt://{data['ip_transmit']}:{data['port_transmit']}"
    # Execute pipeline on cmd
    subprocess.Popen(
        ["cmd", "/c", gstreamer_pipeline_generate],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        cwd=WORKING_DIRECTORY,
    )
    # process.wait()  # Espera o subprocesso terminar antes de continuar
    json_data = {"id_device": data["id_device"], "lat": 0.0, "long": 0.0}
    response = requests.post(f"{URL_API}/api/start_stream", json=json_data)
    print(response)


def login(user_data):
    try:
        email = user_data["email"]
        password = user_data["password"]
        access = {"email": email, "password": password, "device_type": "web"}
        response = requests.post(f"{URL_API}/api/login", json=access)
        print(response)
        return response
    except Exception as e:
        print(f"Error to login: {str(e)}")
        return f"Error to login: {str(e)}"


def start_stream_cameras():
    user_data = {"email": email_entry.get(), "password": password_entry.get()}
    data = login(user_data).json()
    response = login(user_data)
    devices = data["devices"]

    if response.status_code == 200:
        login_windown.destroy()
        for record in devices:
            if str(record["device_type"]) == "cam":
                cam_infos = {
                    "ip_camera": record["ip_camera"],
                    "username": record["user_cam"],
                    "password": record["password_cam"],
                    "port_transmit": record["port_transmit"],
                    "ip_transmit": record["ip_transmit"],
                    "id_device": record["id_device"],
                }

                execute_pipeline(cam_infos)
                # time.sleep(2)  # Espera 2 segundos antes de executar o próximo pipeline
    else:
        print("Error to access API: ", response.status_code)
        message_label.set("Error to login")


# def show_devices(devices):
#     device_windown = ctk.CTk()
#     device_windown.geometry("500x300")
#     device_windown.title("Devices")

#     # Criar a tabela
#     table = ctk.CTk(
#         device_windown, columns=("Name", "Model", "Status"), show="headings"
#     )
#     table.heading("Name", text="Name")
#     table.heading("Model", text="Model")
#     table.heading("Status", text="Status")
#     table.pack()
#     for device in devices:
#         if str(device["device_type"]) == "cam":
#             table.insert(
#                 "",
#                 "end",
#                 values=(
#                     device["device_name"],
#                     device["device_model"],
#                     device["status"],
#                 ),
#             )


# Configuração da janela principal
login_windown = ctk.CTk()
login_windown.geometry("500x300")
login_windown.title("Login")

textContent = ctk.CTkLabel(
    login_windown, text="Welcome to SST Client. Please do Login to continue!"
)
textContent.pack(padx=10, pady=10)

email_entry = ctk.CTkEntry(login_windown, placeholder_text="Email")
email_entry.pack(padx=10, pady=10)

password_entry = ctk.CTkEntry(login_windown, placeholder_text="Password", show="*")
password_entry.pack(padx=10, pady=10)

login_button = ctk.CTkButton(login_windown, text="Login", command=start_stream_cameras)
login_button.pack(padx=10, pady=10)

message_label = ctk.CTkLabel(login_windown, text="", text_color="red")
message_label.pack(padx=10, pady=10)



login_windown.mainloop()