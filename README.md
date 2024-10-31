# INTENSIVE 3 MAXPATROL - PT Start 2024.2

## Команда для запуска данной ветки:

1. Заполните .env

2. Создайте сеть докер

```bash
sudo docker network create my_network
```

3. Запустите, собрав образ

```bash
sudo docker compose up --build
```

---

Тестирование произведено на Ubuntu 20.04

## Для установки Docker:

1. Обновление пакетов

```bash
sudo apt-get update
```

2. Установка зависимостей

```bash
sudo apt-get install ca-certificates curl
```

3. Ключ GPG Docker

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

4. Репозиторий в источники Apt

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
```

5. Установка пакетов

```bash
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

---
