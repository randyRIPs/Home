from flask import Flask, render_template, request
import firebase_admin
from firebase_admin import credentials, firestore
import requests
from bs4 import BeautifulSoup
from spider import get_movies
import os
import json

app = Flask(__name__)

# ✅ 改用環境變數讀 Firebase 金鑰
cred_dict = json.loads(os.environ["FIREBASE_KEY"])
cred = credentials.Certificate(cred_dict)
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def home():
    return '''
        <h2>羅翊綸的網頁</h2>
        <a href="/roadsearch"><button>進入查詢頁面</button></a><br><br>
        <a href="/movie"><button>查詢即將上映電影</button></a><br><br>
        <a href="/rate"><button>爬取並存入電影資料</button></a>
    '''

@app.route('/roadsearch', methods=['GET', 'POST'])
def roadsearch():
    result = []
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        docs = db.collection("taichung")\
                 .where("路口", ">=", keyword)\
                 .where("路口", "<=", keyword + "\uf8ff").stream()
        for doc in docs:
            result.append(doc.to_dict())
    return render_template("roadsearch.html", result=result)

@app.route('/movie', methods=['GET', 'POST'])
def movie():
    result = []
    if request.method == 'POST':
        keyword = request.form.get('keyword')
        result = get_movies(keyword)
    return render_template("movie.html", result=result)

@app.route("/rate")
def rate():
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    result = sp.select(".filmListAllX li")
    lastUpdate = sp.find(class_="smaller09").text[5:]

    for x in result:
        picture = x.find("img").get("src").replace(" ", "")
        title = x.find("img").get("alt")    
        movie_id = x.find("div", class_="filmtitle").find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw" + x.find("a").get("href")

        t = x.find(class_="runtime").text
        showDate = t[5:15]

        showLength = ""
        if "片長" in t:
            t1 = t.find("片長")
            t2 = t.find("分")
            showLength = t[t1+3:t2]

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r is not None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            rate = {
                "G": "普遍級",
                "P": "保護級",
                "F2": "輔12級",
                "F5": "輔15級"
            }.get(rr, "限制級")

        doc = {
            "title": title,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": showLength,
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        doc_ref = db.collection("電影含分級").document(movie_id)
        doc_ref.set(doc)

    return "近期上映電影已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate

if __name__ == '__main__':
    app.run(debug=True)
