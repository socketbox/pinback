from unittest.mock import Mock
import configparser
import argparse
import logging
import os
import string
import random
import pytest
from io import StringIO
from requests import Response
import pinback


@pytest.fixture
def fake_args():
    desc = 'This is the description'
    token = 'foo:123456789ABDEF'
    tags = 'my little lamb goes to the market'
    url = 'https://www.example.com/birth.html'
    args = ["-vv", "-k", token, "-d", desc, url, "-t"]
    args.extend(tags.split())
    return args


def test_get_robust_response():
    url = "https://peacesupplies.org"
    resp = pinback.get_robust_response(url)
    assert (resp.status_code == 200)


def test_parse_robust_resp():
    json_resp = '''{
      "anchor_text": null,
      "api_version": "0.8.1",
      "data-originalurl": "https://abcnews.go.com",
      "data-versiondate": "2020-06-15",
      "data-versionurl": "https://archive.li/wip/hWZdd",
      "request_url": "https://abcnews.go.com",
      "request_url_resource_type": "original-resource",
      "robust_links_html": {
          "memento_url_as_href": "<a href=\"https://archive.li/wip/hWZdd\"\ndata-originalurl=\"https://abcnews.go.com\"\ndata-versiondate=\"2020-06-15\">https://archive.li/wip/hWZdd</a>",
          "original_url_as_href": "<a href=\"https://abcnews.go.com\"\ndata-versionurl=\"https://archive.li/wip/hWZdd\"\ndata-versiondate=\"2020-06-15\">https://abcnews.go.com</a>"
      }
    }'''
    resp = Mock(spec=Response)
    resp.status_code = 200
    resp.return_value = json_resp
    # url = "https://peacesupplies.org"
    parsed_resp = pinback.parse_robust_response(resp)
    assert (parsed_resp['status_code'] == 200)


def test_parse_pinback_args(fake_args):
    parser = pinback.parse_pinback_args(fake_args)
    assert(parser.verbose == 2)
    assert(parser.desc == fake_args[4])
    assert(len(parser.tags) == 7)
    assert(parser.url == fake_args[5])


def test_parse_config():
    import tempfile
    tmpf = tempfile.mkstemp(text=True)
    f = open(tmpf[0], mode='w')
    f.write("[DEFAULT]\nPINBOARD_API_TOKEN=fooschnickens:FDEC3459Q\n\n[BEST_IN_SHOW]\nWINNER=mitzy")
    f.close()
    cfg = pinback.parse_config(tmpf[1])
    os.remove(tmpf[1])
    assert(len(cfg.sections()) == 1)
    assert(cfg.sections()[0] == 'BEST_IN_SHOW')
    assert(cfg['DEFAULT']['PINBOARD_API_TOKEN'] == 'fooschnickens:FDEC3459Q')


@pytest.mark.dependency(depends=[test_parse_pinback_args])
def test_check_prereqs(fake_args):
    """
    Check if config is overridden by command-line arguments
    """
    ns = pinback.parse_pinback_args(fake_args)
    cfg = configparser.ConfigParser()
    cfg['PINBOARD'] = {'PINBOARD_API_TOKEN': 'configtokenvalue'}
    tkn = pinback.check_prereqs(ns, cfg)
    assert(tkn == ns.token)


def test_merge_configs():
    pass


def test_prompt_for_tags(monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO('tag1,groovy,this fails,asdoesthis ,'))
    tags = pinback.prompt_for_tags()
    assert (len(tags) == 2)


def test_prompt_for_desc_toolong(monkeypatch):
    with pytest.raises(EOFError, match=r'EOF when reading a line'):
        monkeypatch.setattr('sys.stdin', StringIO(
            '  this si a a tset alf alsdf fasldfkja aldjfaslkdfj a;sdlfkjas;dlkfja ;sdf aslkfdj a;sdf asldfkj a;sdkfj ;alskdjf ;aslkdjf ;alskjfd ;laskdjf ;lkasjdf;lkasjdflkjas ldkfjas;lkfjd;lsadkj flaskdjf lkasdjfsfdsfd adfasdf asdf      \rThis is my not so trim description'))
        desc = pinback.prompt_for_description()


def test_prompt_for_desc(monkeypatch):
    monkeypatch.setattr('sys.stdin', StringIO('Job description for Java Developer at Foobar'))
    desc = pinback.prompt_for_description()
    assert (desc == 'Job description for Java Developer at Foobar')


def test_pin_url():
    token = os.environ[pinback.TOKEN_STR]
    # https://stackoverflow.com/a/2257449/148680
    rand_dom = ''.join(random.choices(string.ascii_lowercase, k=1)).join(
        random.choices(string.ascii_uppercase + string.digits, k=4))
    shared = False
    url = 'https://www.' + rand_dom + '.movie'
    tags = ["foo", "bar", "baz"]
    desc = "Test description."
    logging.debug("Calling pin_url with: {}, {}, {}, {}".format(url, tags, desc, shared))
    resp = pinback.pin_url(url, tags, desc, token, shared)
    logging.debug("pinboard response: {}".format(resp.text))
    assert (resp != None and resp.status_code == 200)
