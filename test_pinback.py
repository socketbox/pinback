import logging
import os
import string
import time 
import random 
import pytest
import json
from io import StringIO

import pinback

"""
def test_get_formatted_today():
    retval = pinback.get_formatted_today()
    assert(len(retval) == 8)
    assert(retval.startswith('2020'))
"""


def test_get_robust_link():
    url = "https://peacesupplies.org"
    resp = pinback.get_robust_link(url) 
    assert(resp.status_code == 200)

def test_mementoize_url():
    url = "https://hackaday.com/2020/07/16/tend-your-garden-again/"
    resp = pinback.mementoize_url(url)
    assert resp.status_code == 200

def test_prompt_for_tags(monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO('tag1,groovy,this fails,asdoesthis ,'))
    tags = pinback.prompt_for_tags()
    assert(len(tags) == 2)


def test_prompt_for_desc_toolong(monkeypatch):
    with pytest.raises(EOFError, match=r'EOF when reading a line'):
        monkeypatch.setattr('sys.stdin', StringIO('  this si a a tset alf alsdf fasldfkja aldjfaslkdfj a;sdlfkjas;dlkfja ;sdf aslkfdj a;sdf asldfkj a;sdkfj ;alskdjf ;aslkdjf ;alskjfd ;laskdjf ;lkasjdf;lkasjdflkjas ldkfjas;lkfjd;lsadkj flaskdjf lkasdjfsfdsfd adfasdf asdf      \rThis is my not so trim description'))
        desc = pinback.prompt_for_description()


def test_prompt_for_title(monkeypatch):
    monkeypatch.setattr('sys.stdin',
            StringIO('     This is my not so trim description     '))
    title = pinback.prompt_for_description()
    assert(title == 'This is my not so trim description')


def test_pin_url():
    token = os.environ[pinback.TOKEN_STR]
    #https://stackoverflow.com/a/2257449/148680 
    rand_dom = ''.join(random.choices(string.ascii_lowercase, k=1)).join(random.choices(string.ascii_uppercase + string.digits, k=4))
    url = 'https://www.' + rand_dom + '.movie' 
    tags = ["foo", "bar", "baz"] 
    desc = "Test description."
    logging.debug("Calling pin_url with: {}, {}, {}".format(url, tags, desc)) 
    resp = pinback.pin_url(url, tags, desc, token) 
    logging.debug("pinboard response: {}".format(resp.text))
    assert(resp !=  None and resp.status_code == 200)

