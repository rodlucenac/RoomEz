import mysql.connector
from mysql.connector import Error

def conectar():
  try:
    conn = mysql.connector.connect(
      host='localhost',
      port=3306,
      database='RoomEz',
      user='adm',
      password='rlc20040714'
    )
    return conn
  except Error as e:
    print(f"Erro ao conectar ao MySQL: {e}")
    return None
