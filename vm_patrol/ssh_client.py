import paramiko

class SSHClient:
    def __init__(self, host, username, password, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(hostname=self.host, username=self.username, password=self.password, port=self.port)
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False

    def execute_command(self, command):
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()
            return output.strip(), error.strip()
        except Exception as e:
            print(f"Ошибка выполнения команды: {e}")
            return None, str(e)

    def close(self):
        if self.client:
            self.client.close()
