import pytest
import waypin
import json
from io import StringIO

"""
def test_get_formatted_today():
    retval = waypin.get_formatted_today()
    assert(len(retval) == 8)
    assert(retval.startswith('2020'))
"""


def test_get_robust_link():
    url = "https://thegloofactory.com"
    archive=waypin.ARCHIVE_DOMAIN
    resp = waypin.get_robust_link(url, archive) 
    assert(resp.status_code == 200)


def test_prompt_for_tags(monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO('tag1,groovy,this fails,asdoesthis ,'))
    tags = waypin.prompt_for_tags()
    assert(len(tags) == 2)


def test_prompt_for_title_toolong(monkeypatch):
    with pytest.raises(EOFError, match=r'EOF when reading a line'):
        monkeypatch.setattr('sys.stdin', StringIO('  this si a a tset alf alsdf fasldfkja aldjfaslkdfj a;sdlfkjas;dlkfja ;sdf aslkfdj a;sdf asldfkj a;sdkfj ;alskdjf ;aslkdjf ;alskjfd ;laskdjf ;lkasjdf;lkasjdflkjas ldkfjas;lkfjd;lsadkj flaskdjf lkasdjfsfdsfd adfasdf asdf      \rThis is my not so trim description'))
        title = waypin.prompt_for_title()
        #assert(title == 'This is my not so trim description')

def test_prompt_for_title(monkeypatch):
    monkeypatch.setattr('sys.stdin',
            StringIO('     This is my not so trim description     '))
    title = waypin.prompt_for_title()
    assert(title == 'This is my not so trim description')

def test_pin_url():
    #https://stackoverflow.com/a/2257449/148680 
    rand_dom = ''.join(random.choices(string.ascii_lowercase(k=1).\
            join(random.choices(string.ascii_uppercase + string.digits, k=4))
    url = "https://kiwi.concretez.movie"
    a_date = "20200201" 
    resp = waypin.check_availability(url, a_date) 
    assert(resp !=  None)
