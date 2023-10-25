# обкачивааем gutenberg.org
from urllib import request, error
from bs4 import BeautifulSoup
from tqdm import tqdm
import jsonlines
import spacy
import os


# создадим функцию для деления текстов на фрагменты, удобоваримые для spacy
def text_splitter(t, max_l):
    if len(t) <= max_l:
        return [t]
    else:
        d = t.rfind(". ", 0, max_l) + 1
        return [t[:d]] + text_splitter(t[d+1:], max_l)


# соберём список url книг
gt = "https://www.gutenberg.org/"
res = request.urlopen(gt + "browse/scores/top")
soup = BeautifulSoup(res, features="html.parser")
books_nums = [_["href"].split("/")[-1] for _ in soup.find_all('ol')[4].find_all('a')]

# запишем всё содержимое в jsonl файлы
try:
    os.mkdir("corpus")
except FileExistsError:
    pass
finally:
    os.chdir("corpus")
nlp = spacy.load("en_core_web_sm")
for en, _ in tqdm(enumerate(books_nums)):
    if f"{en + 1}.jsonl" not in os.listdir():
        try:
            res = request.urlopen(gt + f"cache/epub/{_}/pg{_}.txt")
            soup = BeautifulSoup(res, features="html.parser")
            splited = soup.get_text().split("***")
            book = {"meta": {"Author": "", "Title": "", "Language": ""}}
            for n, fragment in enumerate(splited):
                if fragment.startswith(" START"):
                    start = n
                if fragment.startswith(" END"):
                    end = n
                if any(key in fragment for key in book["meta"].keys()) \
                        and all(not value for value in book["meta"].values()):
                    for line in fragment.split("\n"):
                        if any(at in line for at in book["meta"].keys()):
                            book["meta"][line.split(": ")[0]] = "; ".join(line.split(": ")[1:]).strip('\r')
            if book["meta"]["Language"] == "English":
                text = "***".join(splited[start + 1:end]).strip().replace("\n", " ").replace("\r", "")
                book["content"] = []
                subtexts = text_splitter(text, 500000)
                for subtext in subtexts:
                    book["content"] += [[{"token": token.orth_, "lemma": token.lemma_, "pos": token.pos_}
                                         for token in sent] for sent in nlp(subtext).sents]
                with jsonlines.open(f"{en+1}.jsonl", mode='w') as writer:
                    writer.write(book)
        except error.HTTPError as e:
            pass
