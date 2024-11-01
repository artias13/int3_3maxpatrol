from typing import List, Union
import logging
from typing import Any, Dict, List, Union, Tuple
from datetime import datetime
import paramiko
import psycopg2
from psycopg2 import Error, connect
from telegram import Update, ForceReply
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
)
import os
import re
from dotenv import load_dotenv
from io import StringIO

TOKEN = os.getenv("TOKEN")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")

SAVE_SYSTEM_INFO_STATE = 1
LOG_FILE_PATH = "/var/log/postgresql/postgresql.log"

# Подключаем логирование
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format=" %(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)
logging.info("Бот запущен")
logger = logging.getLogger(__name__)

def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f"Привет {user.full_name}!")


def helpCommand(update: Update, context):
    """Отправляет сообщение с информацией об использовании бота."""
    update.message.reply_text(
        "Вот список доступных команд:\n"
        "/start - начать диалог\n"
        "/help - показать эту справку\n"
        "/check_remote - проверить удаленный сервер\n"
        "/get_server - информация о системе по ip\n"
    )

def parseConnectionString(connection_string: str) -> Tuple[str, str, str, int]:
    pattern = r'^(?P<user>\w+):(?P<password>\w+)@(?P<ip>\d+\.\d+\.\d+\.\d+):(?P<port>\d+)$'
    match = re.match(pattern, connection_string)
    
    if match:
        user = match.group('user')
        password = match.group('password')
        ip = match.group('ip')
        port = int(match.group('port'))
        
        logger.info(f"Строка подключения: \nUser={user}, Password={password}, IP={ip}, Port={port}")
        return user, password, ip, port
    
    logger.error(f"Неверный формат строки: \n{connection_string}")
    return None, None, None, None

def enterConnectionString(update: Update, context):
    update.message.reply_text("Введите строку подключения к серверу: user:pass@ip:port ")
    return "checkRemote"


def checkRemote(update: Update, context):

    logger.info(
        f"Пользователь {update.message.from_user.username} ввел:\n{update.message.text}"
    )
    user_input = update.message.text

    logger.info(f"Извлекаем данные подключения в тексте:\n{user_input}")
    user, password, ip, port = parseConnectionString(user_input)

    # Если все ок
    if user and password and ip and port:
        # Process the connection details here
        logger.info(f"Получены данные подключения: \nUser={user}, IP={ip}, Port={port}")
        update.message.reply_text(f"Получены данные подключения: \nUser={user}, IP={ip}, Port={port}")

        results, return_type = gatherHostInfo(user=user, ip=ip, password=password, port=port)

        print(results)
        if results == None:
            update.message.reply_text(f"Результаты отсутствуют")
            return ConversationHandler.END

        elif return_type == "error":
            update.message.reply_text(f"Возникла ошибка: \n{results}")
            return ConversationHandler.END

        else:
            formatted_results = format_results(results)
            update.message.reply_text(formatted_results)
            # Сохраняем найденные данные подключения в контекст
            context.user_data["results"] = results

            # Завершаем работу обработчика диалога
            update.message.reply_text(
                "Хотите ли вы сохранить эти данные в базе данных? (yes/no)"
            )
            return SAVE_SYSTEM_INFO_STATE

    else:
        logger.error("Неверный формат строки")
        update.message.reply_text("Неверный формат строки. \nСледуйте формату: user:password@ip:port")
        return ConversationHandler.END

def saveSystemInfo(update: Update, context):
    logger.info(f"Пользователь {update.message.from_user.username} выбрал сохранить данные о системе")
    connection = None
    cursor = None
    try:
        # Get results from context
        results = context.user_data.get("results", [])
        
        if not results:
            raise ValueError("No system info found in context")
        
        # Connect to database
        connection = psycopg2.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_DATABASE,
        )
        
        cursor = connection.cursor()
        
        # Prepare insert query
        insert_query = """
        INSERT INTO system_info (
            ip,
            os,
            architecture,
            uptime,
            disk_space,
            memory_usage,
            mpstat_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        # Start transaction
        cursor.execute("BEGIN;")
        
        # Process results and insert them in one row
        values = []
        for result in results:
            
            values.extend([
                result.get('ip_addresses', ''),
                result.get('os', ''),
                result.get('architecture', ''),
                result.get('uptime', ''),
                result.get('disk_space', ''),
                result.get('memory_usage', ''),
                result.get('mpstat_data', ''),
            ])
        # Remove empty strings from the list
        values = list(filter(None, values))
        
        # Execute insert query with all values
        cursor.execute(insert_query, values)
        
        # Commit transaction
        cursor.execute("COMMIT;")
        
        logger.info(f"Сервер с адресами: \n{values[0]} \nуспешно добавлен в базу данных")
        update.message.reply_text(f"Сервер с адресами: \n{values[0]} \nуспешно добавлен в базу данных")

    except Exception as error:
        logger.error(f"Ошибка при сохранении системной информации: {error}")
        update.message.reply_text("Ошибка при сохранении системной информации в базу данных")
        # Rollback transaction if there's an error
        cursor.execute("ROLLBACK;")
    
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
            logger.info("Подключение закрыто")

    return ConversationHandler.END


def enterIpAddress(update: Update, context):
    update.message.reply_text("Введите IP-адрес искомого сервера")
    return "getServerByIp"


def getServerByIp(update: Update, context):
    """Get server information by IP address"""
    logger.info(f"Пользователь {update.message.from_user.username} запросил информацию о сервере по IP")
    
    # Regex pattern for IPv4 addresses
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    
    # Extract IP address from the message
    ip_address = re.search(ip_pattern, update.message.text)
    
    if ip_address:
        ip_address = ip_address.group()
        
        logger.info(f"Извлечен IP адрес: {ip_address}")
        
        try:
            connection = connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_DATABASE,
            )
            cursor = connection.cursor()
            
            query = """
            SELECT * FROM system_info
            WHERE ip LIKE %s;
            """

            # Prepare the LIKE pattern
            ip_pattern = f"%{ip_address}%"
            
            cursor.execute(query, (ip_pattern,))
            
            servers = cursor.fetchall()
            
            if servers:
                for server in servers:
                    update.message.reply_text(f"Сервер: {server[1]} ({server[0]})")
                    update.message.reply_text(f"Адрес: {server[0]}")
                    update.message.reply_text(f"Операционная система: {server[2]}")
                    update.message.reply_text(f"Архитектура: {server[3]}")
                    update.message.reply_text(f"Время работы: {server[4]}")
                    update.message.reply_text(f"Доступное место на диске: {server[5]}")
                    update.message.reply_text(f"Использование памяти: {server[6]}")
                    update.message.reply_text(f"Данные MPSTAT: {server[7]}")
                    update.message.reply_text("---")
            else:
                update.message.reply_text("Сервер с указанным IP не найден в базе данных.")
            
            logger.info(f"Информация о сервере по IP {ip_address} успешно отправлена пользователю")
        
        except Exception as error:
            logger.error(f"Ошибка при получении информации о сервере по IP: {error}")
            update.message.reply_text("Произошла ошибка при получении информации о сервере.")
        
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                connection.close()
                logger.info("Подключение закрыто")
    
    else:
        update.message.reply_text("Неверный формат IP адреса. Пожалуйста, введите корректный IP адрес.")
        logger.warning(f"Пользователь ввел некорректный IP адрес: {update.message.text}")
    
    return ConversationHandler.END


def declineSaving(update: Update, context):
    logger.info(f"Пользователь {update.message.from_user.username} отменил сохранение")
    update.message.reply_text("Сохранение отменено")
    return ConversationHandler.END


def unrecognizedMessageHandler(update: Update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id, text="Ожидаются сообщения: 'yes' или 'no'"
    )


def cancelHandler(update: Update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Диалог отменен.")
    return ConversationHandler.END


def gatherHostInfo( user, ip, password, port):
    """Подключение к хосту и выполнение команды."""
    commands = [
        'ip addr show',
        'lsb_release -a',
        'uname -a',
        'uptime',
        'df -h',
        'free -h',
        'mpstat',
    ]
    results = []
    
    try:
        logger.info(f"Выполняется подключение к {ip}")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=ip, username=user, password=password, port=port
        )
    except Exception as e:
            logger.error(f"Ошибка при подключении к хосту: {str(e)}")
            return e, "error"

    for command in commands:

        logger.info(f"Выполняется команда {command}")
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read() + stderr.read()
        error = stderr.read()

        if error:
            error = stderr.read().decode('utf-8')
            logger.error(f"Ошибка при выполнении команды {command}: {error}")
            return None, "error"
        
        parsed_output = parse_command_output(output, command)
        results.append((parsed_output))

        
    logger.info(f"Подключение закрывается")
    client.close()
    return results, "success"

def parse_command_output(output: bytes, command: str) -> Dict[str, Union[str, float]]:
    """Parse command output and extract relevant data."""
    parsed_output = {}

    if command == 'ip addr show':
        parsed_output['ip_addresses'] = extract_ip_from_ip_addr(output.decode('utf-8'))
    
    elif command == 'lsb_release -a':
        parsed_output['os'] = extract_os_from_lsb(output.decode('utf-8'))

    elif command == 'uname -a':
        parsed_output['architecture'] = extract_architecture_from_uname(output.decode('utf-8'))

    elif command == 'uptime':
        parsed_output['uptime'] = extract_uptime_from_output(output.decode('utf-8'))

    elif command == 'df -h':
        parsed_output['disk_space'] = extract_disk_space_from_df(output.decode('utf-8'))

    elif command == 'free -h':
        parsed_output['memory_usage'] = extract_memory_usage_from_free(output.decode('utf-8'))

    elif command == 'mpstat':
        parsed_output['mpstat_data'] = output.decode('utf-8').strip()

    return parsed_output

def extract_ip_from_ip_addr(output: str) -> str:
    """
    Extract IP addresses from ip addr show output and return them as a comma-separated string.
    """
    ip_addresses = set()  # Using a set to avoid duplicates
    
    # Используем регулярное выражение для поиска IP-адресов
    pattern = r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'
    
    lines = output.split('\n')
    for line in lines:
        match = re.search(pattern, line)
        if match:
            ip_address = match.group(1)
            logging.info(f"Extracted IP: {ip_address}")
            ip_addresses.add(ip_address)
        else:
            logging.debug(f"No IP found in line: \n{line.strip()}")
    
    # Convert set to sorted list and join with commas and spaces
    ip_string = ", ".join(sorted(ip_addresses))
    
    return ip_string

def extract_os_from_lsb(output: str) -> str:
    """Extract OS name from lsb_release output."""
    lines = output.split('\n')
    for line in lines:
        if "Description:" in line:
            result = line.split(":")[1].strip()
            print(f"OS {result}")
            return line.split(":")[1].strip()
    return "Unknown"

def extract_architecture_from_uname(output: str) -> str:
    """Extract architecture from uname output."""
    lines = output.split('\n')
    for line in lines:
        if "m" in line.lower():
            print(f"АРХИТЕКТУРА {line.lower()}")
            return line.strip()
    return "Unknown"

def extract_uptime_from_output(output: str) -> str:
    """Extract uptime from command output."""
    lines = output.split('\n')
    for line in lines:
        if "up" in line.lower():
            print(f"АПТАЙМ {line.lower()}")
            return line.strip()
    return "Unknown"

def extract_disk_space_from_df(output: str) -> str:
    """Extract disk space information from df command."""
    lines = output.split('\n')
    total_line = None
    for line in lines:
        if "/" in line:
            total_line = line.strip()
            break
    print(f"ДИСК {total_line}")
    return total_line if total_line else "Unknown"

def extract_memory_usage_from_free(output: str) -> str:
    """Extract memory usage information from free command."""
    lines = output.split('\n')
    mem_line = None
    for line in lines:
        if "Mem:" in line:
            mem_line = line.strip()
            break
    print(f"RAM {mem_line}")
    return mem_line if mem_line else "Unknown"

def format_results(results):
    formatted_output = ""
    
    for result in results:
        for command, value in result.items():
            if isinstance(value, str):
                formatted_output += f"\n{command.upper()}:\n"
                formatted_output += f"  {value}\n"
            elif isinstance(value, dict):
                formatted_output += f"\n{command.upper()}:\n"
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, str):
                        formatted_output += f"  {sub_key}: {sub_value}\n"
                    elif isinstance(sub_value, list):
                        formatted_output += f"  {sub_key}:\n"
                        for item in sub_value:
                            formatted_output += f"    - {item}\n"
            elif isinstance(value, list):
                formatted_output += f"\n{command.upper()}:\n"
                for item in value:
                    formatted_output += f"  - {item}\n"
    
    return formatted_output.strip()

def echo(update: Update, context):
    update.message.reply_text(
        "Вот список доступных команд:\n"

        "/help - показать эту справку\n"
    )


def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    convHandlerParseConnection = ConversationHandler(
        entry_points=[CommandHandler("check_remote", enterConnectionString)],
        states={
            "checkRemote": [MessageHandler(Filters.text & ~Filters.command, checkRemote)],
            SAVE_SYSTEM_INFO_STATE: [
                MessageHandler(Filters.regex(r"^yes$"), saveSystemInfo),
                MessageHandler(Filters.regex(r"^no$"), declineSaving),
            ],
        },
        fallbacks=[
            MessageHandler(Filters.text & ~Filters.command, unrecognizedMessageHandler),
            CommandHandler("cancel", cancelHandler),
        ],
    )

    convHandlerGetServerByIp = ConversationHandler(
        entry_points=[CommandHandler("get_server", enterIpAddress)],
        states={
            "getServerByIp": [MessageHandler(Filters.text & ~Filters.command, getServerByIp)]
        },
        fallbacks=[],
    )


    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))

    dp.add_handler(convHandlerParseConnection)
    dp.add_handler(convHandlerGetServerByIp)


    # Регистрируем обработчик текстовых сообщений
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Запускаем бота
    updater.start_polling(timeout=60)

    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == "__main__":
    main()
