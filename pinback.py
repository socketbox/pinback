from datetime import date, datetime
import re
import requests
import waypin
import json
import sys
import logging 

RL_EP="https://robustlinks.mementoweb.org/api/?url={0}&archive={1}"
ARCHIVE_DOMAIN="archive.org"
PB_EP="https://api.pinboard.in/v1/posts/add?auth_token={0}&url={1}&title={2}&tags={3}"

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



'''
    {
      "original_uri": "http://www.cnn.com/",
      "mementos": {
        "last": {
          "datetime": "2014-10-07T18:32:00Z",
          "uri": [
            "http://web.archive.org/web/20141007183200/http://www.cnn.com/",
            "http://wayback.vefsafn.is/wayback/20141007183200/http://www.cnn.com/"
          ]
        },
        "next": {
          "datetime": "2013-01-15T11:01:01Z",
          "uri": [
            "http://web.archive.org/web/20130115110101/http://www.cnn.com/"
          ]
        },
        "closest": {
          "datetime": "2013-01-15T09:46:43Z",
          "uri": [
            "http://web.archive.org/web/20130115094643/http://www.cnn.com/",
            "http://archive.today/aaqIY"
          ]
        },
        "first": {
          "datetime": "2000-06-20T18:02:59Z",
          "uri": [
            "http://arquivo.pt/wayback/wayback/20000620180259/http://cnn.com/"
          ]
        },
        "prev": {
          "datetime": "2013-01-15T08:17:14Z",
          "uri": [
            "http://web.archive.org/web/20130115081714/http://www.cnn.com/"
          ]
        }
      },
      "timegate_uri": "http://timetravel.mementoweb.org/timegate/http://www.cnn.com/",
      "timemap_uri": {
        "link_format": "http://timetravel.mementoweb.org/timemap/link/http://cnn.com",
        "json_format": "http://timetravel.mementoweb.org/timemap/json/http://cnn.com"
      }
    }
    '''

"""def get_formatted_today() -> date:
    return date.today().strftime('%Y%m%d')
"""

def get_robust_link(site_url:str, archive:str = "archive.org") -> requests.models.Response:
    robust_url = RL_EP.format(site_url, archive)
    logging.info("Getting link from Robust Link for {}".format(site_url))
    return requests.get(robust_url)
   
        
"""
    @
"""
def pin_url(url:str, tags:list, desc:str, token:str) -> requests.models.Response:
    pinboard_url = PB_EP.format(token, url, desc, tags) 
    logging.info("Pinning {}...".format(url))
    pb_resp = requests.get(pinboard_url) 
    return pb_resp 


"""
"""
def prompt_for_title():
    title = None 
    while not title or len(title) > 254:
        title = input("Provide a description of less than 256 characters for the pin/bookmark: ").strip()
    logging.debug("User-supplied description: {}".format(title))
    return title


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
    url, archive = check_args()
    # append the supplied date and archive to the Memento API endpoint location
    resp = get_robust_link(url, archive)
    # check for a 2xx status code 
    if resp.status_code - 200 < 100:
        tags = prompt_for_tags()
        pin_url(memento_resp)
    else:
        pass#store the url in WBK machine?


if __name__ == 'main':
    main()
