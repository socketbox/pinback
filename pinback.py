import requests
from bs4 import BeautifulSoup
import configparser
import time
import re
import logging
import sys
import argparse
from pathlib import Path
import os

RL_EP = "https://robustlinks.mementoweb.org/api/?url={0}"
CFG_SECTION = 'PINBOARD'
TOKEN_STR = 'PINBOARD_API_TOKEN'
DEF_CFG_PATH = '/.config/socketbox/pinback/pinback.cfg'


def get_resource(url: str, **payload) -> requests.Response:
    """
    Get a resource from a potentially problematic service by retrying periodically
    for up to a minute.

    :param url: the resource desired
    :return: an HTTP response
    """
    # Note that, for idempotent operations, like the initial
    # retrieving of metadata for the resource, this isn't an issue.
    # Might be a good idea to verify that, at least for Pinboard, a 50x status
    # code precludes the creation of a bookmark
    sleep_t = 2
    # we try nine times for a cumulative max of 150s
    while (resp := requests.get(url, params=payload)).status_code != 200 and sleep_t < 60:
        # potentially transient failure
        if resp.status_code == 504 or resp.status_code == 502:
            logging.warning(f'Gateway issue. Retrying after {sleep_t}')
            time.sleep(sleep_t)
            sleep_t *= 1.5
        # if status is in 400 range, recovery unlikely
        elif 400 <= resp.status_code < 500:
            logging.warning(f"Response status {resp.status_code} unexpected.")
            sys.exit(1)
    return resp


def get_original_metadata(url: str) -> dict:
    """
    :param url: the URL of the resources you want to archive and bookmark
    :return: a dict containing the title and description of the resource
    """
    logging.debug(f'Retrieving metadata from {url}')
    resp = get_resource(url)
    if resp.status_code == 200:
        soup = BeautifulSoup(resp.content, 'html.parser')
        meta_d = {'status_code': resp.status_code,
                  'title': soup.title.text,
                  'description': soup.find("meta",
                                           {'name': 'description'})['content']}
    else:
        logging.warning(f'Unable to retrieve metadata for {url}')

    return meta_d


def get_robust_response(site_url: str) -> requests.models.Response:
    """

    :param site_url:
    :return:
    """
    robust_url = RL_EP.format(site_url)
    logging.info("Getting link from Robust Link using {}".format(robust_url))
    resp = get_resource(robust_url)
    return resp


def parse_robust_response(resp: requests.models.Response) -> dict:
    """

    :param resp:
    :return:
    """
    assert (resp.status_code == 200)
    json = resp.json()
    res_dict = {
        'status_code': resp.status_code,
        'robust_url': json['data-versionurl'],
        'orig_url': json['data-originalurl']}
    return res_dict


def pin_url(url: str, tags: str = None, title: str = None,
            description: str = None, token: str = None, share: bool = False,
            unread: bool = False, replace: bool = True) -> requests.models.Response:
    """
    Construct the query to the Pinboard API and then make a request.
    These paramaters are described at https://pinboard.in/api/

    :param url: the archival URL to be bookmarked
    :param tags:
    :param title:
    :param description:
    :param token: a Pinboard API token
    :param share:
    :param unread:
    :param replace:
    """
    # https://stackoverflow.com/a/11717045/148680
    shared, to_be_read, to_be_replaced = ('no',) * 3

    # payload will contain keys that correspond to what API expects as parms
    payload = {}
    # API requires 'yes'/'no'
    if share:
        payload['shared'] = 'yes'
    if unread:
        payload['toread'] = 'yes'
    if replace:
        payload['replace'] = 'yes'

    payload['auth_token'] = token
    payload['url'] = url
    payload['description'] = title
    payload['extended'] = description
    payload['tags'] = tags
    payload['shared'] = share
    pinboard_url = 'https://api.pinboard.in/v1/posts/add'

    logging.info(f"Pinning {pinboard_url}...")
    pb_resp = requests.get(pinboard_url, payload)
    if pb_resp.status_code == 200:
        logging.info(f'Successfully saved URL {url} to Pinboard')
    if pb_resp.status_code != 200:
        logging.warning(f'Issue saving URL {url} to Pinboard; response data: {pb_resp.json()}')
    return pb_resp


def prompt_for_description():
    # TODO:  Show the user the metadata version of the description and ask them if they'd like to change it.
    """
    Prompt the user for a description.
    :return: a user-supplied string that will be used as the bookmark's title
    """
    while (desc := input("Provide a description for the pin/bookmark: ")).strip() is None:
        logging.debug(f"User-supplied title/description: {desc}")
    return desc


def prompt_for_title():
    # TODO:  Show the user the metadata version of the title and ask them if they'd like to change it.
    """
    Prompt the user for a title
    :return: a user-supplied string that will be used as the bookmark's title
    """
    title = None
    while not title or len(title) > 254:
        title = input("Provide a title of less than 256 characters for the pin/bookmark: ").strip()
    logging.debug(f"User-supplied title/titleription: {title}")
    return title


def prompt_for_tags() -> str:
    """
    Prompt the user for tags
    :return: a user-supplied string that will be used as the bookmark's tags
    """
    title = None
    while (tags_str := input("Provide a comma-delimited list of tags: ")) == '':
        logging.debug(f"User-supplied tag string: {tags_str}")
    # seems sloppy to go back and forth between strings and lists; just use regex sub
    tags = tags_str.split(',')
    tags = [t.strip() for t in tags]
    logging.debug(f"Tag list before match and after strip: {tags}")
    # only tags without whitespace are valid
    patt = re.compile(r'^\S*$')
    valid = [t for t in tags if re.match(patt, t)]
    tags_str = ' '.join(valid)
    logging.debug(f"Tag string after cleanup: {tags_str}")
    return tags_str


def parse_pinback_args() -> argparse.Namespace:
    """
    Create an ArgumentParser, add arguments, and return a Namespace.
    Most of these options are described at https://pinboard.in/api/

    :return: a Namespace resulting from the parsing of command-line arguments
    """
    parser = argparse.ArgumentParser(description='Archive a URL and save it to Pinboard', prog='pinback',
                                     usage='%(prog)s [options] url')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-k', '--token', action='store', help="A pinboard API token")
    parser.add_argument('-s', '--share', action='store_true', default=False,
                        help="Publicly Share the bookmark on Pinboard")
    parser.add_argument('-r', '--read', action='store_true', default=False, help="Mark bookmark as unread")
    parser.add_argument('-p', '--replace', action='store_true', default=True, help="Replace bookmark with similar URL")
    parser.add_argument('-g', '--tags', action='extend', nargs='+', type=str,
                        help='A space-delimited list of tags for Pinboard')
    parser.add_argument('-d', '--desc', action='store', type=str, help='A description for the Pinboard entry')
    parser.add_argument('-t', '--title', action='store', type=str,
                        help='A title for the Pinboard entry')
    parser.add_argument('-c', '--config', action='store',
                        default=str(Path.home()) + '/.config/socketbox/pinback/pinback.cfg')
    parser.add_argument('url', metavar='url', type=str, help='the original URL' +
                                                             '(non-archival URL) you intend to save to Pinboard',
                        action='store')
    return parser.parse_args()


def parse_config(cfg_file: str) -> configparser.ConfigParser:
    """
    Pinback uses an INI-style configuration file as explained in Python's configparser
    documentation. If a path is not supplied by the user with the '-c' or '--config'
    option, then pinback uses the default of $HOME/.config/socketbox/pinback/pinback.cfg'.

    :param cfg_file: a string that represents the absolute path to a configuration file
    :return: a instance of ConfigParser
    """
    cfgp = configparser.ConfigParser()
    if cfg_file:
        cfgp.read(cfg_file)
    else:
        home = str(Path.home())
        cfgp.read(home + DEF_CFG_PATH)
    return cfgp


def check_prereqs(argp: argparse.ArgumentParser, cfgp: configparser.ConfigParser):
    """
    Intended to ensure that the Pinboard API token is available. First, the
    configuration file is checked, then the command-line arguments, and finally
    the runtime environment is checked.

    Priority is given to the command-line argument, then the configuration file.
    If neither exists, then the Pinboard token is gotten from the runtime
    environment.
    :param argp:
    :param cfgp:
    :return:
    """
    token = cfgp[CFG_SECTION][TOKEN_STR]
    if not token or argp.token:
        token = argp.token
    if not token:
        if token := os.getenv(TOKEN_STR) is None:
            raise ValueError("No Pinboard API token supplied. Exiting.")
    return token


def _merge_configs(arg_ns: argparse.Namespace, cfg: configparser.ConfigParser) -> dict:
    """
    Transforms the config. object into a flat dictionary, then merges it with the
    argument parser namespace

    :return a unified dictionary of configuration KV pairs
    """
    cfg_d, uni_d = {}
    for s in cfg.sections():
        for k, v in cfg.items(s):
            cfg_d[k] = v
    # merge the cfg dict with the argparser Namespace using PEP 408 syntax
    uni_d = {**cfg_d, **(vars(arg_ns))}
    return uni_d


def _get_metadata_for_pinback_url(*args, name: str = None):
    md_str = None
    for x in args:
        if x:
            md_str = x
    if not md_str:
        fnc_name = f'prompt_for_{name}'
        this = sys.modules[__name__]
        fnc = getattr(this, fnc_name)
        md_str = fnc()
    return md_str


def main():
    # TODO merge two "configuration namespaces" into a single dictionary
    #  rather than treat separately
    arg_ns = parse_pinback_args()
    parsed_cfg = parse_config(arg_ns.config)
    # uni_cfg = _merge_configs(arg_ns, parsed_cfg)
    try:
        token = check_prereqs(arg_ns, parsed_cfg)
    except ValueError as ve:
        logging.error(ve)
        sys.exit(1)
    if arg_ns.verbose == 1:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    elif arg_ns.verbose > 1:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    md = get_original_metadata(arg_ns.url)
    resp = get_robust_response(arg_ns.url)
    parsed_resp = parse_robust_response(resp)
    title = _get_metadata_for_pinback_url(arg_ns.title, md['title'], name='title')
    desc = _get_metadata_for_pinback_url(arg_ns.desc, md['description'], name='description')
    tags = _get_metadata_for_pinback_url(arg_ns.tags, name='tags')
    # make sure the user knows something's missing
    if not tags or not desc or not title:
        logging.warning(f'Pinning without metadata {[x for x in ["tags", "desc", "title"] if not locals()[x]]}')
    pin_url(parsed_resp['robust_url'], tags=tags, description=desc, token=token,
            share=arg_ns.share, unread=arg_ns.read, replace=arg_ns.replace,
            title=title)


if __name__ == '__main__':
    main()
