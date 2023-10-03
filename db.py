import mysql.connector


def get_db_connection():
    connection = mysql.connector.connect(
        host='db',
        port=3306,
        user="root",
        password="example",
        database="pastexam"
    )
    return connection


def get_db():
    connection = get_db_connection()
    db = connection.cursor()
    try:
        yield db
    finally:
        db.close()
        connection.close()
