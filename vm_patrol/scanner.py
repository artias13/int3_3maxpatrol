import json
from ssh_client import SSHClient
from db_client import DBClient
import os
from dotenv import load_dotenv

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
VM_IP=os.getenv("VM_IP")
VM_USERNAME=os.getenv("VM_USERNAME")
VM_PASSWORD=os.getenv("VM_PASSWORD")
VM_PORT=os.getenv("VM_PORT")

def detect_os(output):
    if "Debian GNU/Linux" in output:
        return "Debian"
    elif "Ubuntu" in output:
        return "Ubuntu"
    elif "Manjaro Linux" in output:
        return "Manjaro"
    else:
        return "Unknown Linux"

def get_vm_info(ip, username, password, port):
    ssh_client = SSHClient(ip, username, password, port)
    if not ssh_client.connect():
        return None
    
    try:
        # Получаем информацию об ОС
        os_info, _ = ssh_client.execute_command("cat /etc/os-release")
        detected_os = detect_os(os_info)

        # Получаем версию ОС
        version, _ = ssh_client.execute_command("grep VERSION_ID /etc/os-release | cut -d '=' -f 2")

        # Получаем архитектуру
        architecture, _ = ssh_client.execute_command("uname -m")

        return {
            "ip": ip,
            "os": detected_os,
            "version": version.strip('"'),
            "architecture": architecture,
            "detected_os": detected_os
        }
    finally:
        ssh_client.close()

def main():
    # Загрузка конфигурации
    db_client = DBClient(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    if not db_client.connect():
        print("Не удалось подключиться к базе данных")
        return

    try:
        # Сканирование VM
        vm_info = get_vm_info(
            ip=VM_IP,
            username=VM_USERNAME,
            password=VM_PASSWORD,
            port=VM_PORT
        )

        if vm_info:
            # Запись результатов в базу данных
            result = db_client.insert_scan_result(vm_info)
            print(f"Результат сканирования успешно записан: {result}")
        else:
            print("Не удалось получить информацию о VM")
    finally:
        db_client.close()

if __name__ == "__main__":
    main()
