# -*- coding: utf-8 -*-
import pymysql   
import networkx as nx
import sys
sys.path.append(r'C:\Users\0000\Desktop\ResearcherNet\code') # import 할 때 에러가 나서 경로를 추가해줌.
from GoogleScholar_utilities import getSoup, updateResearcher, insertCo_author, insertPaperDB, insertPaper_Researcher, makeNetwork, visualizeNetwork, findTopPaper, findTopResearcher, find_close_paper, find_paper
####################################################################################################################




####################################################################################################################
# [MySQL 기본값 설정]
hostname = 'localhost'
username = 'root'
pw = 'pw123'
charset = 'utf8'
dbname = 'googlescholar'
####################################################################################################################



'''
####################################################################################################################
# [시작 연구자 최초 설정 및 DB에 추]
start_name = 'Ian Goodfellow'
start_affiliation = ''
start_citations = 67451
start_h_index = 58
start_url = "https://scholar.google.com/citations?user=iYN86KEAAAAJ" + '&view_op=list_works&sortby=pubdate'

conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
curs = conn.cursor()

sql = 'insert into researcher(name, affiliation, citations, h_index, url) values (%s, %s, %s, %s, %s);'
try:
    curs.execute(sql, (start_name, start_affiliation, start_citations, start_h_index, start_url))
    conn.commit()
except:
    print('Researcher already exists in the database.')
conn.close()
####################################################################################################################




####################################################################################################################
# [크롤링 --> DB에 저장, 네트워크 생성]
g1 = nx.Graph() # network 생성
g1.add_node(start_name) # 최초의 연구자를 node에 추가

# 첫번째 researcher로부터 1 거리에 있는 researcher들 추가
print('================ First ================')
soup = getSoup(start_url)
next_url_list, next_name_list = insertCo_author(soup) # researcher db에 co_author를 insert
insertPaperDB(soup)
#paper_title_List = insertPaperDB(soup)
#insertPaper_Researcher(name, paper_title_List)

for next_name in next_name_list:
    g1.add_node(next_name)
    g1.add_edge(start_name, next_name)
visualizeNetwork(g1, 0, 'researcherNet_1.html')

# 2 거리에 있는 researcher들 추가
print('================ Second ================')
next_url_list = makeNetwork(next_url_list, g1)
visualizeNetwork(g1, 0, 'researcherNet_2.html')

# 3 거리에 있는 researcher들 추가
print('================ Third ================')
next_url_list = makeNetwork(next_url_list, g1)
visualizeNetwork(g1, 20, 'researcherNet_3.html')

# 4 거리에 있는 researcher들 추가
print('================ Fourth ================')
next_url_list = makeNetwork(next_url_list, g1)
visualizeNetwork(g1, 30, 'researcherNet_4.html')

# 5 거리에 있는 researcher들 추가
print('================ Fifth ================')
next_url_list = makeNetwork(next_url_list, g1)
visualizeNetwork(g1, 30, 'researcherNet_5.html')

# DB에 node별 연결 수(n_adjacencies) update
conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
curs = conn.cursor()

for node, adjacencies in enumerate(g1.adjacency()):
    name = adjacencies[0]
    n_adjacencies = len(adjacencies[1])
    sql = 'update researcher set n_adjacencies=%s where name=%s;'
    curs.execute(sql, (n_adjacencies, name))
    conn.commit()
conn.close()
####################################################################################################################




####################################################################################################################
# [Network export and import]
# Network export
result_dir = r'C:\Users\0000\Desktop\ResearcherNet\result'
nx.write_gml(g1, result_dir + r'five.gml')

# Network import
result_dir = r'C:\Users\0000\Desktop\ResearcherNet\result'
gml_graph = nx.read_gml(result_dir + r'\five.gml')
####################################################################################################################




####################################################################################################################
# [node 별 cetrality 계산]
measures = nx.degree_centrality(gml_graph)
#measures = nx.eigenvector_centrality(gml_graph)
#measures = nx.eigenvector_centrality_numpy(gml_graph)
#measures = nx.pagerank(gml_graph)
#measures = nx.closeness_centrality(gml_graph)
#measures = nx.betweenness_centrality(gml_graph) 
####################################################################################################################
'''



####################################################################################################################
# [생성된 데이터를 통해 정보 추출]

# stary_year부터 지금까지의 paper를 citedby를 기준으로 top_n개 만큼 추출.
findTopPaper(top_n=4, start_year = 2018) 

# by를 기준으로 top_n명의 researcher 추출.
findTopResearcher(top_n=4, by='n_adjacencies') 

# (start_year과 start_citedby 이상인 paper 중) input_title과 유사한 title을 가진 paper를 top_n만큼 추출. (이미 존재하고 있는 paper만 입력 가능)
find_close_paper(input_title = 'Bert: Pre-training of deep bidirectional transformers for language understanding', top_n = 5, start_year = 2017, start_citedby = 10) 

# title에 keyword가 들어간 paper를 citedby를 기준으로 top_n개 추출.
find_paper(keyword = 'cnns', top_n = 5, start_year = 2018)
####################################################################################################################