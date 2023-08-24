import mysql.connector

def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        port=3306,
        user="root",
        password="asdfghjkl;'",
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
