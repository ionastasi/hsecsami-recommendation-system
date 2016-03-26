#!/usr/bin/python3
# -*- coding: utf-8 -*-
# ionastasi@gmail.com


import argparse
import sys
from html.parser import HTMLParser
import urllib.request
import os
from datetime import datetime

import log
from config import *


LINK_PREFIX_POST = "http://geektimes.ru/post/"
LINK_PREFIX_ALL_PAGE = "http://geektimes.ru/all/page"


class ParserPageAll(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self._posts = list()


    def handle_starttag(self, tag, attrs):
        if tag == 'div':
            attrs = dict(attrs)
            if attrs.get('class'):
                if 'post ' in attrs['class'] and 'shortcuts_item' in attrs['class']:
                # 'post shortcuts_item', 'post translation shortcuts_item', may be smth else
                # and it can't be 'posts shortcuts_item'
                    self._posts.append(int(attrs['id'].replace('post_', '')))  # post_1234 -> 1234


    def parse(self, page):
        self.feed(page)
        return self._posts


def parse_argument():
    update = argparse.ArgumentParser(
        prog='update',
        description="Downloading pages. You can download last posts or some range of posts.",
    )
    update.add_argument(
        '--log',
        default='error',
        choices=['critical', 'error',  'debug'],
        dest='log_level',
        help="log level, 'error' is default value"
    )
    update.add_argument(
        '--print-ids',
        action='store_true',
        dest='print_ids',
        help="print articles' ids"
    )
    update.add_argument(
        '--force',
        action='store_true',
        dest='update_force',
        help='download articles, even if they have been downloaded yet'
    )
    update_subs = update.add_subparsers(
        dest='update_mode'
    )
    update_last = update_subs.add_parser(
        'last',
        description="Download latest 1000 articles, if they have not been downloaded yet.",
        help='download last 1000 posts'
    )
    update_range = update_subs.add_parser(
        'range',
        description='''Download range of posts.
                       Stops if starts downloading already downloaded posts.
                       Of course, you should set the range by --from and --to.''',
        help='download range of posts'
    )
    update_range.add_argument(
        '--from',
        required=True,
        type=int,
        dest='start_down',
        help='start of range'
    )
    update_range.add_argument(
        '--to',
        required=True,
        type=int,
        dest='end_down',
        help='end of range'
    )
    if 'range' not in sys.argv and 'last' not in sys.argv:
        update.print_help()
        return

    return update.parse_args()


def download(url, NotFound_error=True):
    try:
        response = urllib.request.urlopen(url)
        log.debug('Load "{}"... {} {}'.format(url, response.reason, response.getcode()))
    except (urllib.error.URLError, urllib.error.HTTPError) as exception:
        if exception.code == 404 and not NotFound_error:
            log.debug('Load "{}"... {} {}'.format(url, exception.reason, exception.code))
        else:
            log.error('Load "{}"... {} {}'.format(url, exception.reason, exception.code))
    else:
        return response.read().decode('utf-8')


def download_post(url, NotFound_error=True):
    text = download(url, NotFound_error)
    if not text:
        return
    id_page = url.replace(LINK_PREFIX_POST, '')
    path = '{}.html'.format(HTML_DIR + id_page)
    open(path, 'w').write(text)
    log.debug('Store {} to {}... {} KB'.format(url, path, round(os.path.getsize(path) // KB_SIZE)))


def download_list(ids_list, post_to_date,
                  print_ids=False, force=False, NotFound_error=True):
    try:
        for post_id in ids_list:
            if force or post_id not in post_to_date:
                download_post(LINK_PREFIX_POST + str(post_id), NotFound_error)
                post_to_date[post_id] = datetime.today()
                if print_ids:
                    print(post_id)
            else:
                log.debug("Skip post {}. It's already downloaded.".format(post_id))
    except KeyboardInterrupt:
        log.debug("KeyboardInterrupt.")
    except Exception as exc:
        exception, value, traceback = sys.exc_info()
        log.critical('{}'.format(value))  # it doesn't work without formatting
    finally:
        with open(HTMLS_INDEX, 'w') as fout:
            for post, date in post_to_date.items():
                fout.write('{} {}\n'.format(post, date.strftime(DATE_FORMAT)))


def main():
    post_to_date = dict()
    for x in open(HTMLS_INDEX).readlines():
        post, date = x.split()
        post_to_date[int(post)] = datetime.strptime(date, DATE_FORMAT)

    args = parse_argument()
    if not args:
        return

    log.config(log.level(args.log_level))

    if args.update_mode == 'last':
        try:
            ids = list()
            NotFound_error = True
            for page_n in range(1, 101):
                url = LINK_PREFIX_ALL_PAGE + str(page_n)
                text = download(url)
                ids += ParserPageAll().parse(text)
        except KeyboardInterrupt:
            log.debug("KeyboardInterrupt.")
            return
        except Exception as exc:
            exception, value, traceback = sys.exc_info()
            log.critical('{}'.format(value))  # it doesn't work without formatting
            return
    elif args.update_mode == 'range':
        NotFound_error = False
        ids = [x for x in range(args.start_down, args.end_down + 1)]

    download_list(ids, post_to_date, args.print_ids,
                  args.update_force, NotFound_error)


if __name__ == '__main__':
    main()
