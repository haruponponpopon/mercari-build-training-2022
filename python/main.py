import os
import logging
import pathlib
import sqlite3
import hashlib
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
logger = logging.getLogger("uvicorn")
logger.level = logging.INFO
images = pathlib.Path(__file__).parent.resolve() / "image"
origins = [os.environ.get("FRONT_URL", "http://localhost:3000")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, world!"}


@app.post("/items")
def add_item(name: str = Form(...), category: str = Form(...), image: str = Form(...)):
    # データベースに接続する
    conn = sqlite3.connect("../db/mercari.sqlite3")
    c = conn.cursor()
    # c.execute("""drop table items;""")  # デバッグ用
    c.execute("SELECT COUNT(*) FROM sqlite_master WHERE TYPE='table' AND name='items'")
    if c.fetchone()[0] == 0:  # テーブルが存在していなかったらテーブルを作成
        c.execute(
            "CREATE TABLE items(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,category TEXT, image TEXT)"
        )
    # データの挿入
    c.execute(
        "INSERT INTO items(name,category,image) values (?, ?, ?)",
        (name, category, hashlib.sha256(image.encode("utf-8")).hexdigest() + ".jpg"),
    )

    # 挿入した結果を保存（コミット）する
    conn.commit()

    # データベースへのアクセスが終わったら close する
    conn.close()
    return {"message": f"item received: {name}"}


@app.get("/items")
def get_item():
    # データベースに接続する
    conn = sqlite3.connect("../db/mercari.sqlite3")
    c = conn.cursor()

    # データの取得
    result = c.execute("SELECT name, category, image FROM items").fetchall()
    list = {
        "items": [
            {"name": name, "category": category, "image": image}
            for name, category, image in result
        ]
    }
    # 挿入した結果を保存（コミット）する
    conn.commit()

    # データベースへのアクセスが終わったら close する
    conn.close()
    return list


@app.get("/search")
def search_item(keyword: str):
    conn = sqlite3.connect("../db/mercari.sqlite3")
    c = conn.cursor()
    result = c.execute(
        "SELECT name, category FROM items WHERE name like (?)",
        (f"%{keyword}%",),
    ).fetchall()
    list = {
        "items": [{"name": name, "category": category} for name, category in result]
    }
    conn.commit()
    conn.close()
    return list


@app.get("/image/{items_image}")
async def get_image(items_image):
    # Create image path
    image = images / items_image

    if not items_image.endswith(".jpg"):
        raise HTTPException(status_code=400, detail="Image path does not end with .jpg")

    if not image.exists():
        logger.debug(f"Image not found: {image}")
        image = images / "default.jpg"

    return FileResponse(image)
