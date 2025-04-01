
import psycopg2
import configparser

config = configparser.ConfigParser()
config.read('settings.ini')
db_name = config['Db_data']['db_name']
db_user = config['Db_data']['db_user']
db_password = config['Db_data']['db_password']
db_host = config['Db_data']['db_host']
db_port = config['Db_data']['db_port']

def get_db_connection():
    try:
        connection = psycopg2.connect(user=db_user,
                                      password=db_password,
                                      host=db_host,
                                      port=db_port,
                                      database=db_name)
        return connection
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}")
        return None