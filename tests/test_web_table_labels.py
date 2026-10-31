from bs4 import BeautifulSoup

from gaia_agent.tools import label_simple_tables


def test_columns_keep_meaning_and_navigation_links_survive():
    soup=BeautifulSoup('<h2>Approved May 2018</h2><table><tr><th>Project</th><th>Display date</th><th>Applicant</th></tr>'
        '<tr><td><a href="/project">Example</a></td><td>June 2019</td><td>Alice</td></tr></table>', 'html.parser')
    label_simple_tables(soup)
    cells=soup.find_all('td')
    assert cells[1].get_text(' ',strip=True)=='Display date: June 2019'
    assert cells[2].get_text(' ',strip=True)=='Applicant: Alice'
    assert soup.find('a')['href']=='/project'


def test_complex_spanned_tables_are_not_mislabelled():
    soup=BeautifulSoup('<table><tr><th>A</th><th>B</th></tr><tr><td colspan="2">Merged</td></tr></table>', 'html.parser')
    before=str(soup)
    label_simple_tables(soup)
    assert str(soup)==before
