# -*- coding: utf-8 -*-
import pymysql
import bs4             
import urllib.request   
from urllib.request import FancyURLopener
import networkx as nx
import urllib.parse

####################################################################################################################
# [MySQL 기본값 설정]
hostname = 'localhost'
username = 'root'
pw = 'pw123'
charset = 'utf8'
dbname = 'googlescholar'
####################################################################################################################




####################################################################################################################
# [크롤링 관련 함수]
class AppURLopener(FancyURLopener):     			 
    version = "Mozilla/5.0"


def getSoup(url):
    html = AppURLopener().open(urllib.parse.unquote(url))
    soup = bs4.BeautifulSoup(html.read(), features= "lxml")
    return soup
####################################################################################################################




####################################################################################################################
# [DB 관련 함수]
    
# Researcher 정보 update
def updateResearcher(soup):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    
    name = soup.find('div', {'id':'gsc_prf_in'}).text
    tmp_info = soup.findAll('td', {'class':'gsc_rsb_std'})
    try:
        citations = tmp_info[1].text
    except:
        citations = str(0)
    try:
        h_index = tmp_info[3].text
    except:
        h_index = 0
    
    sql = 'update researcher set citations=%s, h_index=%s where name=%s;'
    curs.execute(sql, (citations, h_index, name))
    conn.commit()
    conn.close()
    return name
    
# co_author의 정보(name, affiliation, url)를 db에 insert하고, co_author들의 name과 url은 list 형태로 반환(다음 단계에서 사용할 수 있도록 반환함)
def insertCo_author(soup):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    
    co_author_list = soup.findAll("span", {"class":"gsc_rsb_a_desc"})
    next_url_list = []
    next_name_list = []
    
    for co_author_soup in co_author_list:
        name = co_author_soup.find('a').text
        next_name_list.append(name)
        affiliation = co_author_soup.find('span', {'class':'gsc_rsb_a_ext'}).text
        scholar_url = "https://scholar.google.com/" + co_author_soup.a.get('href') + '&view_op=list_works&sortby=pubdate'
        
        sql = 'select exists (select * from researcher where name = %s) as success;'
        curs.execute(sql,(name))
        row = curs.fetchone()
        
        # 이미 db에 존재하면 추가하지 않음
        if row[0] == 0:
            #next_url_list.append(scholar_url)
            try:
            	sql = 'insert into researcher(name, affiliation, url) values (%s, %s, %s);'
            	curs.execute(sql, (name, affiliation, scholar_url))
            	conn.commit(); next_url_list.append(scholar_url);
            except:
                print('insertCo_author error')
    conn.close()
    return next_url_list, next_name_list
    
# 가장 최근 paper들의 정보(title, citedby, year)를 db에 insert
def insertPaperDB(soup):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    
    paper_list = soup.findAll('tr', {'class':'gsc_a_tr'})
    #paper_title_List = []
    
    for paper_soup in paper_list:
        title = paper_soup.find('a').text
        #paper_title_List.append(title)
        citedby = paper_soup.find('td', {'class':'gsc_a_c'}).find('a').text
        year = paper_soup.find('td', {'class':'gsc_a_y'}).find('span').text
        
        if citedby == '':
            citedby = str(0)
        if year == '':
            year = str(0)
        # 이미 db에 존재하면 추가하지 않음
        sql = 'select exists (select * from paper where title = %s) as success;'
        curs.execute(sql,(title))
        row = curs.fetchone()
        if row[0] == 0:            
            sql = 'insert into paper(title, citedby, year) values (%s, %s, %s);'
            try:
                curs.execute(sql, (title, citedby, year))
                conn.commit()
                #paper_title_List.append(title)
            except:
                print('insertPaperDB error')
            
    conn.close()
    #return paper_title_List

# [paper - researcher] db에 추가하는 함수인데 사용하지 않음.
def insertPaper_Researcher(name, paper_title_List):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    
    for paper_title in paper_title_List:
        sql = 'insert into paper_researcher(paper_title, researcher_name) values (%s, %s);'
        try:
            curs.execute(sql, (paper_title, name))
            conn.commit()
        except:
            print('insertPaper_Researcher error')

    conn.close()
####################################################################################################################
    



####################################################################################################################
# [위의 함수들을 이용해서 DB에 정보 추가하고, network도 생성]
def makeNetwork(next_url_list, g1):
    new_next_url_list = []
    print('Size of url: ', len(next_url_list))
    i = 0
    for url in next_url_list:
        if i % 100 == 0:
            print(i)
        
        try:             
            soup = getSoup(url)            
        except:
            pass
        else:
            next_url_list, next_name_list = insertCo_author(soup);
            name = updateResearcher(soup)
            insertPaperDB(soup)
            #paper_title_List = insertPaperDB(soup)
            #insertPaper_Researcher(name, paper_title_List)
    
            new_next_url_list = new_next_url_list + next_url_list
                
            for next_name in next_name_list: 
                g1.add_node(next_name);
                g1.add_edge(name, next_name);
        i = i + 1
    return new_next_url_list
####################################################################################################################
    


####################################################################################################################
# [생성된 DB를 통해서 정보 추출]
    
# 인용수 상위 top_n 논문
def findTopPaper(top_n, start_year):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    sql = 'select * from paper where year >= %s  order by citedby desc limit %s;'
    curs.execute(sql, (start_year, top_n))
    conn.close()
    rows = curs.fetchall()
    
    print('=' * 100)
    print('Top ' + str(top_n) + ' Papers from ' + str(start_year) + ' (ordered by citations)')
    print('=' * 100) 
    
    for row in rows:
        print('-' * 100)
        print('Title: ' + row[0])
        print('Cited by: ' + str(row[1]))
        print('Year: ' + str(row[2]))
        print('-' * 100)

# by(citations, h_index, n_adjacencies)를 기준으로 상위 top_n 연구자
def findTopResearcher(top_n, by):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    sql = 'select name, affiliation, citations, h_index, n_adjacencies from researcher order by ' + by + ' desc limit %s;'
    curs.execute(sql, (top_n))
    conn.close()
    
    rows = curs.fetchall()
    
    print('=' * 100)
    print('Top ' + str(top_n) + ' Researchers by ' + by)
    print('=' * 100) 
    
    for row in rows:
        print('-' * 100)
        print('Name: ' + row[0])
        print('Affiliation: ' + row[1])
        print('Citations: ' + str(row[2]))
        print('h index: ' + str(row[3]))
        print('# of adjacencies: ' + str(row[4]))
        print('-' * 100)

# cosine similarty를 이용해서 제목이 비슷한 논문 찾음.
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from numpy import dot
from numpy.linalg import norm

def cos_sim(A, B):
       return dot(A, B)/(norm(A)*norm(B))
   
# 주의!: 너무 많은 범위에 해당하는 start_year, start_citedby를 입력할 경우 메모리 에러가 날 가능성이 있음.
# 주의!: start_year를 기준으로 DB에 존재하는 paper에 대해서만 가능.
def find_close_paper(input_title, top_n, start_year = 2018, start_citedby = 20):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    sql = 'select title from paper where year >= %s and citedby >= %s;'
    curs.execute(sql,(start_year, start_citedby))
    
    rows = curs.fetchall()
    title_list = []
    
    for row in rows:
        title_list.append(row[0])
        
    tfidf = TfidfVectorizer(stop_words='english')
    tfidf_matrix = tfidf.fit_transform(title_list)
    cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
    sim_scores = list(enumerate(cosine_sim[title_list.index(input_title)]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[0:top_n]
    title_indices = [i[0] for i in sim_scores]
    
    
    print('=' * 100)
    print('Top ' + str(top_n) + ' Papers related to [ ' + input_title + ' ]')
    print('=' * 100)   
    for title_index in title_indices:
        title = title_list[title_index]
        sql = 'select citedby, year from paper where title = %s;'
        curs.execute(sql, title)
        tmp_info = curs.fetchone()
        print('-' * 100)
        print('Title: ' + title)
        print('Cited by: ', tmp_info[0])
        print('Year: ', tmp_info[1])
        print('-' * 100)
    conn.close()

# title에 keyword가 들어간 paper를 citedby를 기준으로 top_n개 추출.
def find_paper(keyword, top_n, start_year):
    conn = pymysql.connect(host=hostname, user=username, password=pw, db=dbname, charset=charset)
    curs = conn.cursor()
    sql = 'select * from paper where year >='+ str(start_year) +' and title like lower(\'%'+keyword+'%\') order by citedby desc limit '+ str(top_n) +';'

    curs.execute(sql)
    conn.close()
    rows = curs.fetchall()
    
    print('=' * 100)  
    print('Top ' + str(top_n) + ' ['+ keyword + '] related papers')
    print('=' * 100)   
    for row in rows[0:(top_n + 1)]:
        print('-' * 100)
        print('Title: ' + row[0])
        print('Cited by: ', str(row[1]))
        print('Year: ', str(row[2]))
        print('-' * 100)
####################################################################################################################
        
        
        
        
####################################################################################################################
# [Visualization]
# n_adjacencies가 cut_n 이상인 node만 plotting.
import plotly.graph_objects as go
import plotly

def visualizeNetwork(g1, cut_n, filename):
    edge_x = []
    edge_y = []
    g2 = g1.copy()

    pos = nx.spring_layout(g2)
    #measures = nx.degree_centrality(g2)
    #measures = nx.eigenvector_centrality(g1)
    #measures = nx.eigenvector_centrality_numpy(g1)
    #measures = nx.pagerank(g1)
    #measures = nx.closeness_centrality(g1)
    #measures = nx.betweenness_centrality(g1)

    # 인접한 사람이 cut_n명 미만이면 제거 
    under_cut_n = []
    for node, adjacencies in enumerate(g2.adjacency()):
        if len(adjacencies[1]) < cut_n:
            under_cut_n.append(adjacencies[0])

    for under_n_person in under_cut_n:
        g2.remove_node(under_n_person)
    
    #for node, adjacencies in enumerate(g2.adjacency()):
    #   print(adjacencies[0], len(adjacencies[1]))

    nx.set_node_attributes(g2, pos, 'pos')
    for edge in g2.edges():
        x0, y0 = g2.node[edge[0]]['pos']
        x1, y1 = g2.node[edge[1]]['pos']
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#888'), hoverinfo='none', mode='lines')

    node_x = []
    node_y = []

    for node in g2.nodes():
        x, y = g2.node[node]['pos']
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
            x=node_x, 
            y=node_y,
            mode='markers',
            hoverinfo='text',
            marker=dict(
                    showscale=True,
                    # colorscale options
                    #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
                    #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
                    #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
                    colorscale='YlGnBu',
                    reversescale=True,
                    color=[],
                    size=10,
                    colorbar=dict(thickness=15,title='Node Connections',xanchor='left',titleside='right'),line_width=2))

    node_adjacencies = []
    node_text = []
    i = 0
    names = list(g2.nodes())

    for node, adjacencies in enumerate(g2.adjacency()):
        node_adjacencies.append(len(adjacencies[1]))
        node_text.append(names[i] +'# of connections: '+str(len(adjacencies[1])))
        i += 1

    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text

    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                            title='<br>Researcher network',
                            titlefont_size=16,
                            showlegend=False,
                            hovermode='closest',
                            margin=dict(b=20,l=5,r=5,t=40),
                            annotations=[ dict(
                                    text="Python code: <a href='https://plot.ly/ipython-notebooks/network-graphs/'> https://plot.ly/ipython-notebooks/network-graphs/</a>",
                                    showarrow=False,
                                    xref="paper", yref="paper",
                                    x=0.005, y=-0.002 ) ],
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    plotly.offline.plot(fig, filename=filename)
####################################################################################################################




































