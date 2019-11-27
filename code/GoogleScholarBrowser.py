# -*- coding: utf-8 -*-
import pymysql
import bs4             
import urllib.request   
from urllib.request import FancyURLopener
import networkx as nx
import urllib.parse

class AppURLopener(FancyURLopener):     			 
    version = "Mozilla/5.0"


def getSoup(url):
    html = AppURLopener().open(urllib.parse.unquote(url))
    soup = bs4.BeautifulSoup(html.read(), features= "lxml")
    return soup


def updateResearcher(soup):
    conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
    curs = conn.cursor()
    
    name = soup.find('div', {'id':'gsc_prf_in'}).text
    tmp_info = soup.findAll('td', {'class':'gsc_rsb_std'})
    citations = tmp_info[1].text
    h_index = tmp_info[3].text
    
    sql = 'update researcher set citations=%s, h_index=%s where name=%s;'
    curs.execute(sql, (citations, h_index, name))
    conn.commit()
    conn.close()
    return name
    
    
def insertCo_author(soup):
    conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
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
            next_url_list.append(scholar_url)
            sql = 'insert into researcher(name, affiliation, url) values (%s, %s, %s);'
            curs.execute(sql, (name, affiliation, scholar_url))
            conn.commit()       
    conn.close()
    return next_url_list, next_name_list
    

def insertPaperDB(soup):
    conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
    curs = conn.cursor()
    
    paper_list = soup.findAll('tr', {'class':'gsc_a_tr'})
    paper_title_List = []
    
    for paper_soup in paper_list:
        title = paper_soup.find('a').text
        paper_title_List.append(title)
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
            except:
                print('error')
                curs.execute(sql, ("", "0", "0"))
                conn.commit()
    conn.close()
    return paper_title_List

def insertPaper_Researcher(name, paper_title_List):
    conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
    curs = conn.cursor()
    
    for paper_title in paper_title_List:
        sql = 'insert into paper_researcher(paper_title, researcher_name) values (%s, %s);'
        try:
            curs.execute(sql, (paper_title, name))
            conn.commit()
        except:
            print('insertPaper_Researcher error')
            curs.execute(sql, ("", name))
            conn.commit()
    conn.close()

def makeNetwork(next_url_list, g1):
    new_next_url_list = []
    for url in next_url_list:
        soup = getSoup(url)
        next_url_list, next_name_list = insertCo_author(soup)
        name = updateResearcher(soup)
        paper_title_List = insertPaperDB(soup)
        insertPaper_Researcher(name, paper_title_List)
    
        new_next_url_list = new_next_url_list + next_url_list
        g1.add_node(name)
        
        for next_name in next_name_list:
            g1.add_node(next_name)
            g1.add_edge(name, next_name)
    
    return new_next_url_list

# 인용수 상위 top_n 논문
def findTopPaper(top_n, start_year):
    conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
    curs = conn.cursor()
    sql = 'select * from paper where year >= %s  order by citedby desc limit %s;'
    curs.execute(sql, (start_year, top_n))
    conn.close()
    return curs.fetchall()

# by(citations, h_index, n_adjacencies)를 기준으로 상위 top_n 연구자
def findTopResearcher(top_n, by):
    conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
    curs = conn.cursor()
    sql = 'select name,' + by + ' from researcher order by ' + by + ' desc limit %s;'
    curs.execute(sql, (top_n))
    conn.close()
    return curs.fetchall()


####################################################################################################################
# 시작 연구자의 경우 최초에 설정해줘야함.
start_name = 'Ian Goodfellow'
start_affiliation = ''
start_citations = 67451
start_h_index = 58
start_url = "https://scholar.google.com/citations?user=iYN86KEAAAAJ" + '&view_op=list_works&sortby=pubdate'

conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
curs = conn.cursor()

sql = 'insert into researcher(name, affiliation, citations, h_index, url) values (%s, %s, %s, %s, %s);'
curs.execute(sql, (start_name, start_affiliation, start_citations, start_h_index, start_url))
conn.commit()
conn.close()
####################################################################################################################

g1 = nx.Graph()
# 첫번째 researcher로부터 1 거리에 있는 researcher들 추가
print('================ First ================')
soup = getSoup(start_url)
next_url_list, next_name_list = insertCo_author(soup)
name = updateResearcher(soup)
paper_title_List = insertPaperDB(soup)
insertPaper_Researcher(name, paper_title_List)

g1.add_node(name)
for next_name in next_name_list:
    g1.add_node(next_name)
    g1.add_edge(name, next_name)

# 2 거리에 있는 researcher들 추가
print('================ Second ================')
next_url_list = makeNetwork(next_url_list, g1)
# =============================================================================
# # 3 거리에 있는 researcher들 추가
# print('================ Third ================')
# next_url_list = makeNetwork(next_url_list, g1)
# # 4 거리에 있는 researcher들 추가
# print('================ Fourth ================')
# next_url_list = makeNetwork(next_url_list, g1)
# # 5 거리에 있는 researcher들 추가
# print('================ Fifth ================')
# next_url_list = makeNetwork(next_url_list, g1)
# # 6 거리에 있는 researcher들 추가
# print('================ Sixth ================')
# next_url_list = makeNetwork(next_url_list, g1)
# =============================================================================

conn = pymysql.connect(host='localhost', user='root',password='Iamveryhappy12!@',db='googlescholar2',charset='utf8')
curs = conn.cursor()
for node, adjacencies in enumerate(g1.adjacency()):    
    name = adjacencies[0]
    n_adjacencies = len(adjacencies[1])
    sql = 'update researcher set n_adjacencies=%s where name=%s;'
    curs.execute(sql, (n_adjacencies, name))
    conn.commit()
conn.close()

#print(findTopPaper(top_n=10, start_year=2017))
#print(findTopResearcher(top_n=100, by='h_index'))


####################################################################################################################
# Visualization
import plotly.graph_objects as go
import plotly

edge_x = []
edge_y = []
g2 = g1.copy()

pos = nx.spring_layout(g2)
measures = nx.degree_centrality(g2)
#measures = nx.eigenvector_centrality(g1)
#measures = nx.eigenvector_centrality_numpy(g1)
#measures = nx.pagerank(g1)
#measures = nx.closeness_centrality(g1)
#measures = nx.betweenness_centrality(g1)
#nodes = nx.draw_networkx_nodes(g2, pos=pos, node_color=list(measures.values()), node_size= 100, alpha=0.01)
#nx.draw_networkx_edges(g2, pos, alpha=0.1)
#nx.draw_networkx_labels(g2, pos)

#plt.title('Network of Researchers')
#plt.colorbar(nodes)
#plt.axis('off')
#plt.show()

# 인접한 사람이 5명 미만이면 제거 
under_5 = []
for node, adjacencies in enumerate(g2.adjacency()):
    if len(adjacencies[1]) < 5:
        under_5.append(adjacencies[0])

for under5_person in under_5:
    g2.remove_node(under5_person)
    
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

edge_trace = go.Scatter(
    x=edge_x, y=edge_y,
    line=dict(width=0.5, color='#888'),
    hoverinfo='none',
    mode='lines')

node_x = []
node_y = []

for node in g2.nodes():
    x, y = g2.node[node]['pos']
    node_x.append(x)
    node_y.append(y)

node_trace = go.Scatter(
    x=node_x, y=node_y,
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
        colorbar=dict(
            thickness=15,
            title='Node Connections',
            xanchor='left',
            titleside='right'
        ),
        line_width=2))

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
plotly.offline.plot(fig, filename='new_network6.html')

  








