from datetime import date, datetime
import time
import re
import requests
import json
import logging 
import sys
import os

RL_EP="https://robustlinks.mementoweb.org/api/?url={0}"
ARCHIVE_DOMAIN="archive.org"
PB_EP="https://api.pinboard.in/v1/posts/add?auth_token={0}&url={1}&description={2}&tags={3}&shared='no'"
TOKEN_STR='PINBOARD_API_TOKEN'

'''
check that PINBOARD_API_TOKEN is set
get url and, optionally, archive from user
append URL to Robust Links API URL
make the call using requests
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



"""def get_formatted_today() -> date:
    return date.today().strftime('%Y%m%d')
"""



def get_robust_link(site_url:str) -> requests.models.Response:
    robust_url = RL_EP.format(site_url)
    logging.debug("Getting link from Robust Link using {}".format(robust_url))
    resp = requests.models.Response()
    sleep_t = 10 
    attempts = 0
    while resp.status_code != 200 and attempts < 11:
        print("Retrieving a link from Robust Link service...This could take quite some time.")
        attempts += 1 
        resp = requests.get(robust_url)
        # this is not unusual; the Archive is very slow, so we wait and retry
        if resp.status_code == 504 or resp.status_code == 502:
            logging.warning("Gateway issue. Retrying after {}".format(sleep_t)) 
            time.sleep(sleep_t)
            sleep_t *= 1.5
        # if status is in 400 range, recovery unlikely
        elif resp.status_code >= 400 and resp.status_code < 500:
            logging.warn(f"Response status {resp.status_code} unexpected.")
            break
    return resp


"""
    @
"""
def pin_url(url:str, tags:list, desc:str, token:str) -> requests.models.Response:
    pinboard_url = PB_EP.format(token, url, desc, tags) 
    logging.info("Pinning {}...".format(pinboard_url))
    pb_resp = requests.get(pinboard_url) 
    return pb_resp 


"""
"""
def prompt_for_description():
    desc = None 
    while not desc or len(desc) > 254:
        desc = input("Provide a description of less than 256 characters for the pin/bookmark: ").strip()
    logging.debug("User-supplied description: {}".format(desc))
    return desc


def prompt_for_tags():
    tags_str = None 
    while not tags_str:
        tags_str = input("Provide a comma-delimited list of tags: ") 
    else:
        logging.debug("User-supplied tag string: {}".format(tags_str))
        patt = re.compile(r"^.*\s.*$")
        # check for bad chars (whitespace)
        tags = tags_str.split(',')
        logging.debug("Tag list: {}".format(tags))
        # return only tags matching the regex above 
        valid = [t for t in tags if re.match(patt, t)]
    return valid


def main():
    url = sys.argv[1] #TODO check_args()
    token = os.environ[TOKEN_STR]
    if not token:
        print("Please provide a Pinboard API token. Currently that means setting {} in the environment".format(TOKEN_STR))
        exit(1) 
    # append the supplied date and archive to the Memento API endpoint location
    resp = get_robust_link(url)
    desc = prompt_for_description()
    tags = prompt_for_tags()
    pin_url(resp, tags, desc, token)
    
if __name__ == '__main__':
    main()

