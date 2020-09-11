import configparser
import time
import re
import requests
import logging
import sys
import argparse
from pathlib import Path
import os

RL_EP = "https://robustlinks.mementoweb.org/api/?url={0}"
PB_EP = "https://api.pinboard.in/v1/posts/add?auth_token={0}&url={1}&description={2}&tags={3}&shared='no'"
CFG_SECTION = 'PINBOARD'
TOKEN_STR = 'PINBOARD_API_TOKEN'
DEF_CFG_PATH = '/.config/socketbox/pinback/pinback.cfg'

'''
Pseudocode overview:
1. check that PINBOARD_API_TOKEN is set, either in the env, or in
    ~/.config/socketbox/pinback.cfg
2. get url and, optionally, archive from user
3. append URL to Robust Links API URL
4. make the call using requests
check the response for status
if 2xx
    if json has no errors, 
        return URL
    else
        log error and exit
    prompt user for tags
    prompt user for description
    make call to pinboard
if 4xx
    log error and exit
if other ie redirect
    log condition and exit
'''


def get_robust_response(site_url: str) -> requests.models.Response:
    """

    :param site_url:
    :return:
    """
    robust_url = RL_EP.format(site_url)
    logging.info("Getting link from Robust Link using {}".format(robust_url))
    resp = requests.get(robust_url)
    return resp


def parse_robust_response(resp: requests.models.Response) -> dict:
    """

    :param resp:
    :return:
    """
    assert(resp.status_code == 200)
    json = resp.json()
    res_dict = {
        'robust_url': json['version_url'],
        'orig_url': json['data-originalurl']}
    return res_dict



def pin_url(url: str, tags: list, desc: str, token: str, share: bool) -> requests.models.Response:
    """

    :param share:
    :param desc:
    :param tags:
    :param url:
    :type token: object
    """
    # take the Pinboard URL and add query args
    pinboard_url = PB_EP.format(token, url, desc, tags, share)
    logging.info(f"Pinning {pinboard_url}...")
    pb_resp = requests.get(pinboard_url)
    return pb_resp


def prompt_for_description():
    desc = None
    while not desc or len(desc) > 254:
        desc = input("Provide a description of less than 256 characters for the pin/bookmark: ").strip()
    logging.debug(f"User-supplied description: {desc}")
    return desc


def prompt_for_tags():
    tags_str = None
    while not tags_str:
        tags_str = input("Provide a comma-delimited list of tags: ")
    else:
        logging.debug(f"User-supplied tag string: {tags_str}")
        patt = re.compile(r"^.*\s.*$")
        # check for bad chars (whitespace)
        tags = tags_str.split(',')
        logging.debug(f"Tag list: {tags}")
        # return only tags matching the regex above 
        valid = [t for t in tags if re.match(patt, t)]
    return valid


def parse_pinback_args(args: list) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Save an archived URL to Pinboard', prog='pinback',
                                     usage='%(prog)s [options] url')
    parser.add_argument('-v', '--verbose', action='count', default=0)
    parser.add_argument('--version', action='version', version='%(prog)s 1.0')
    parser.add_argument('-k', '--token', action='store', help="A pinboard API token")
    parser.add_argument('-t', '--tags', action='extend', nargs='+', type=str,
                        help='A space-delimited list of tags for Pinboard')
    parser.add_argument('-d', '--desc', action='store', type=str,
                        help='A description (title) for the Pinboard entry')
    parser.add_argument('-c', '--config', action='store',
                        default=str(Path.home()) + '/.config/socketbox/pinback/pinback.cfg')
    parser.add_argument('url', metavar='url', type=str, help='the original URL' +
                                                             '(non-archival URL) you intend to save to Pinboard',
                        action='store')
    return parser.parse_args(args)


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


def main():
    # TODO merge two "configuration namespaces" into a single dictionary
    #  rather than treat separately
    arg_ns = parse_pinback_args(sys.argv)
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

    sleep_t = 2
    # if the service returned a good response, proceed
    while (resp := get_robust_response(arg_ns.url).status_code != 200 and
        sleep_t < 60):
        # potentially transient failure
        if  resp.status_code == 504 or resp.status_code == 502:
            logging.warning(f'Gateway issue. Retrying after {sleep_t}')
            time.sleep(sleep_t)
            sleep_t *= 1.5
        # if status is in 400 range, recovery unlikely
        elif 400 <= resp.status_code < 500:
            logging.warning(f"Response status {resp.status_code} unexpected.")
            sys.exit(1)

    parsed_resp = parse_robust_response(resp)
    if desc := arg_ns.desc is None:
        desc = prompt_for_description()
    if tags := arg_ns.tags is None:
        tags = prompt_for_tags()
    if not tags or not desc:
        logging.warning("Pinning without ")
    pin_url(parsed_resp, parsed_resp['robust_url'], tags, desc, token, arg_ns.shared)


if __name__ == '__main__':
    main()
