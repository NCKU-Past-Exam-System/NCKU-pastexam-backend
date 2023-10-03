from typing import Optional, Union
from fastapi import FastAPI, HTTPException
from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import mysql.connector
import os

from routers import files, courses

# app = FastAPI(docs_url=None, redoc_url=None)
app = FastAPI()  # 建立一個 Fast API application

origins = [
    "http://localhost:7777",
    "https://nckucsie-pastexam.owenowenisme.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/version")  # 指定 api 路徑 (get方法)
def read_version():
    return {"version": "0.1.0"}


@app.on_event("startup")
async def startup_event():
    mysql_password = os.getenv('MYSQL_ROOT_PASSWORD', 'example')
    connection = mysql.connector.connect(
        host="db",
        port=3306,
        user="root",
        password=mysql_password,
        database="pastexam"
    )
    app.state.dbconn = connection
    cur = connection.cursor()
    sql_inits = open('dependencies/init.sql', 'r', encoding="utf-8").read()
    for sql_init in sql_inits.split(';'):
        cur.execute(sql_init)
        connection.commit()
    cur.close()


def get_db(request: Request):
    connection = request.app.state.dbconn
    db = connection.cursor()

    try:
        yield db
    finally:
        db.close()


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(files)
app.include_router(courses)
