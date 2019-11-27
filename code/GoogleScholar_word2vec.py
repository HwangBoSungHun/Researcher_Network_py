# -*- coding: utf-8 -*-
import pymysql
from nltk.corpus import stopwords 
from nltk.tokenize import word_tokenize 
import re
# from gensim.models import Word2Vec
from gensim.models import KeyedVectors
import sys
import numpy as np

#import nltk
#nltk.download('stopwords')




base_dir = r'C:\Users\0000\Desktop\Researcher_tmp\ResearcherNet\result' 
sys.path.append(base_dir) # import 할 때 에러가 나서 경로를 추가해줌.
stop_words = set(stopwords.words('english'))




####################################################################################################################
# [MySQL 기본값 설정]
hostname = 'localhost'
username = 'root'
pw = 'pw123'
charset = 'utf8'
dbname = 'googlescholar'
####################################################################################################################




####################################################################################################################
# DB의 paper 테이블에서 title만 가져옴
conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
curs = conn.cursor()
sql = 'select title from paper;'
curs.execute(sql)
rows = curs.fetchall()
titles = [row[0] for row in rows]
conn.close()
####################################################################################################################



'''
####################################################################################################################
# title을 통해서 word2vec model 생성
normalized_text = []
for title in titles:
     tokens = re.sub(r"[^a-z0-9]+", " ", title.lower())
     normalized_text.append(tokens)

sentences_token = []
sentences_token = [word_tokenize(sentence) for sentence in normalized_text]
        
result = []
# stopwords 제거
for sent in sentences_token:
    tmp_result = []
    for w in sent:
        if w not in stop_words:
            tmp_result.append(w)
    result.append(tmp_result)

model = Word2Vec(sentences=result, size=100, window=5, min_count=5, workers=4, sg=0) # 모델 생
####################################################################################################################
'''



####################################################################################################################
# model export
# model.wv.save_word2vec_format("GoogleScholar_w2v_100") 
# !python -m gensim.scripts.word2vec2tensor --input GoogleScholar_w2v --output GoogleScholar_w2v
# https://projector.tensorflow.org/

# model import
model=KeyedVectors.load_word2vec_format(r"C:\Users\0000\Desktop\SNA\ResearcherNet\result\GoogleScholar_w2v")
word_vectors = model.wv
####################################################################################################################




####################################################################################################################
def get_mean_vec(title, stop_words, word_vectors):    
    title = re.sub(r"[^a-z0-9]+", " ", title.lower())
    title_token = word_tokenize(title) 
    title_result = []
    for w in title_token:
        if w not in stop_words:
            title_result.append(w)
    title_vec = []
    for w in title_result:
        try:
            title_vec.append(word_vectors.get_vector(w))
        except:
            pass
    
    mean_vec = np.mean(title_vec, axis=0)
    
    return mean_vec

def find_close_paper2(titles, all_mean_vec, new_title, top_n=10):
    new_mean_vec = get_mean_vec(new_title, stop_words, word_vectors)
    distance = []
    for tmp_mean_vec in all_mean_vec:
        distance.append(np.linalg.norm(tmp_mean_vec - new_mean_vec))

    sorted_idx = np.argsort(distance)
    print('=' * 100)
    print('Top ' + str(top_n) + ' Papers related to [ ' + new_title + ' ]')
    print('=' * 100)   
    
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    
    for tmp_idx in sorted_idx[0:top_n]:
        title = titles[tmp_idx]
        sql = 'select citedby, year from paper where title = %s;'
        curs.execute(sql, title)
        tmp_info = curs.fetchone()
        print('-' * 100)
        print('Title: ' + title)
        print('Cited by: ', tmp_info[0])
        print('Year: ', tmp_info[1])
        print('-' * 100)

    conn.close()
    
    
from numpy import dot
from numpy.linalg import norm
def cos_sim(A, B):
    value = dot(A, B)/(norm(A)*norm(B))
    if type(value) != np.float32:
        value = 0
    return value
   
def find_close_paper3(titles, all_mean_vec, new_title, top_n=10):
    new_mean_vec = get_mean_vec(new_title, stop_words, word_vectors)
    distance = []
    for tmp_mean_vec in all_mean_vec:
        distance.append(cos_sim(tmp_mean_vec, new_mean_vec))

    
    sorted_idx = np.argsort(distance)
    print('=' * 100)
    print('Top ' + str(top_n) + ' Papers related to [ ' + new_title + ' ]')
    print('=' * 100)   
    
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    
    for tmp_idx in sorted_idx[-top_n:]:
        title = titles[tmp_idx]
        sql = 'select citedby, year from paper where title = %s;'
        curs.execute(sql, title)
        tmp_info = curs.fetchone()
        print('-' * 100)
        print('Title: ' + title)
        print('Cited by: ', tmp_info[0])
        print('Year: ', tmp_info[1])
        print('-' * 100)
    
    conn.close()
####################################################################################################################




####################################################################################################################
all_mean_vec = []
for title in titles:
    all_mean_vec.append(get_mean_vec(title, stop_words, word_vectors))
new_title = 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding'
find_close_paper2(titles, all_mean_vec, new_title, top_n=10)
find_close_paper3(titles, all_mean_vec, new_title, top_n=10)

####################################################################################################################
