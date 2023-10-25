from flask import Flask, url_for, redirect, render_template, request
import os
import jsonlines
from tqdm import tqdm
from nltk.tokenize.treebank import TreebankWordDetokenizer


app = Flask(__name__)


cwd = os.getcwd()
os.chdir("corpus")
corpus = []
for file in tqdm(os.listdir()[:5]):   # берем первые пять книжек, потому что и так получается большой корпус, и если взять все, то очень много времени занимает парсинг
    with jsonlines.open(file) as reader:
        corpus.append(*reader)

# собираем множество частей речи, которые выделил spacy
poses = set()
for book in tqdm(corpus):
    for sentence in book["content"]:
        poses |= set([word["pos"] for word in sentence]) 
os.chdir(cwd)


@app.route('/', methods=['GET', 'POST'])
def site():
    return redirect(url_for('search'))

# страница поиска и как он происходит
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query_dict = {}
        for k, v in request.form.items():
            if "Input" in k:
                if int(k[-1]) in query_dict.keys():
                    query_dict[int(k[-1])][k.split("Input")[0]] = v
                else:
                    query_dict[int(k[-1])] = {k.split("Input")[0]: v}
        if query_dict:
            for n in range(max(query_dict.keys())):
                if n not in query_dict.keys():
                    query_dict[n] = {}
        query = tuple(dict(sorted(query_dict.items(), key=lambda i: i[0])).values())
        return redirect(url_for("results", query=str(query)))
    return render_template("search.html", poses=list(poses))

# выдача результатов и страница результатов
@app.route('/results/<query>', methods=['GET', 'POST'])
def results(query):
    query = eval(query)
    query_res = []
    for book in corpus:
        for sentence in book["content"]:
            if len(sentence) >= len(query):
                for _ in range(len(sentence)):
                    if len(sentence[_:]) >= len(query):
                        contexts = [sentence[:_], sentence[_:][:len(query)], sentence[_:][len(query):]] # рассматриваем левые и правые контексты тоже
                        if contexts[1]:          # дальше убираем чувствительность к регистру и проверяем инфу о токене на предмет соответствия запросу
                            if all(all(d1[k].lower() == v.lower() for k, v in d2.items() if v) for d1, d2 in zip(contexts[1], query)):  
                                query_res.append((
                                    [TreebankWordDetokenizer().detokenize([word["token"] for word in s]) 
                                     for s in contexts],          # собираем обратно список токенов в предложение при помощи функции из nltk
                                    book["meta"]
                                ))
        if request.method == 'POST':
            return redirect(url_for("search"))
    return render_template("results.html", results=query_res)


if __name__ == '__main__':
    app.run(debug=True, port=1014, use_reloader=False)
