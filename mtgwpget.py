#!/usr/bin/env python3

import collections
import datetime
import math
import os
import os.path
import re
import sys
import urllib.request
import urllib.parse
import xml.parsers.expat
import time

import json

from datetime import datetime, date, timedelta
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin

WALLPAPER_LIST_URL_TEMPLATE = (
    'http://magic.wizards.com/see-more-wallpaper'
    '?page={}&filter_by=DESC&search=')

WALLPAPER_BASE_URL = (
    'http://magic.wizards.com/sites/mtg/'
    'files/images/wallpaper/')

wallpaper_dir = Path(os.path.expanduser('~/Pictures'))

def nowstr():
    return str(datetime.now())

def print_(message):
    print(nowstr() + ' ' + message)

def get_wallpaper_urls(pagenum):
    
    class WallpaperUrlSearcher(HTMLParser):
        def __init__(self):
            self.urls = []
            HTMLParser.__init__(self)

        def handle_starttag(self, tag, attrs):
            if tag != 'a':
                return

            hrefs = [value for name, value in attrs if name == 'href']
            if not hrefs:
                return 

            href = hrefs[0]
            if (href.startswith(WALLPAPER_BASE_URL) 
                and '1920x1080' in href
                and href.endswith('.jpg')):
                self.urls.append(href)

    pagestring = get_wallpaper_article_page(pagenum)

    linkfinder = WallpaperUrlSearcher()
    linkfinder.feed(pagestring)

    return linkfinder.urls

def get_wallpaper_article_page(pagenum):
    url = WALLPAPER_LIST_URL_TEMPLATE.format(pagenum)
    print_('Opening ' + url)
    response = urllib.request.urlopen(url)
    resp_string = response.read().decode('utf8')
    resp_json = json.loads(resp_string)
    return resp_json['data']

def download_latest_unused_wallpaper(opts):

    for pagenum in range(1, 11):
        urls = get_wallpaper_urls(pagenum)
        for url in urls:
            filename = url.split('/')[-1]
            local_path = wallpaper_dir / filename
            if not local_path.exists():
                try:
                    print_('Downloading ' + url + ' to ' + str(wallpaper_dir))
                    download_file(opts, url, local_path)
                except urllib.error.HTTPError as error:
                    print_('ERROR: Download failed with HTTP error ' + str(error.code))
                return local_path
            else:
                print('    ' + filename + ' already downloaded')

def download_file(opts, url, path):
    filename = url.split('/')[-1]
    response = urllib.request.urlopen(url)
    content_length = int(response.getheader('Content-Length'))

    print_('File size: ' + str(content_length // 1000) + 'kb')

    downloaded = 0
    chunk_length = int(10E3)

    with path.open('wb') as file_:
        while True:
            bytes_ = response.read(chunk_length)
            file_.write(bytes_)

            if opts['--progress']:
                downloaded += len(bytes_)
                print_progress_bar(60, downloaded, content_length)

                if len(bytes_) < chunk_length:
                    print('')
                    break

def print_progress_bar(width, current, total):
    sys.stdout.write('\r')
    sys.stdout.write('[')

    done_width = math.floor(current/total * width) 
    sys.stdout.write(done_width * '#')
    sys.stdout.write((width - done_width) * ' ')

    sys.stdout.write('] ')
    sys.stdout.write(str(current // 1000))
    sys.stdout.write('/')
    sys.stdout.write(str(total // 1000))
    sys.stdout.write('kb')
    sys.stdout.flush()


def get_desktop_wallpaper_path():
    if os.name == 'nt':
        SPI_GETDESKWALLPAPER = 0x0073

        import ctypes
        from ctypes import windll
        path_buffer = ctypes.create_unicode_buffer(256)
        windll.user32.SystemParametersInfoW(
            SPI_GETDESKWALLPAPER,
            len(path_buffer),
            ctypes.byref(path_buffer),
            0);

        return Path(path_buffer.value)
    elif os.name == 'posix':
        #Only Gnome 3 is supported
        from gi.repository import Gio

        gsettings = Gio.Settings.new('org.gnome.desktop.background')

        pictureuri = gsettings.get_string('picture-uri')
        urlpath = urllib.parse.urlparse(pictureuri).path
        pathname = urllib.request.url2pathname(urlpath)

        return Path(pathname)
    else:
        print ('OS not supported')
        exit(1)

def set_as_desktop_wallpaper(path):
    if os.name == 'nt':
        SPI_SETDESKWALLPAPER = 0x0014
        SPIF_UPDATEINIFILE = 1
        SPIF_SENDWININICHANGE = 2

        from ctypes import windll
        windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, str(path),
            SPIF_UPDATEINIFILE or SPIF_SENDWININICHANGE)
    elif os.name == 'posix':
        #Only Gnome 3 is supported
        from gi.repository import Gio
        gsettings = Gio.Settings.new('org.gnome.desktop.background')
        gsettings.set_string('picture-uri', path.as_uri())
        gsettings.apply()
    else:
        print ('OS not supported')
        exit(1)

def set_latest_wallpaper_as_desktop(opts):
    print_('Starting wallpaper refresh')
    path = download_latest_unused_wallpaper(opts)
    if path: 
        set_as_desktop_wallpaper(path)
    print_('Done')

def print_usage():
    print("mtgwpget")
    print("Magic: The Gathering wallpaper download utility")
    print("")
    print("Options:")
    print("  --force     Skip freshness check on currect wallpaper")
    print("  --progress  Show a textual download progress bar")

if __name__ == '__main__':
    opts = { '--force' : False, '--progress' : False }

    for arg in sys.argv[1:]:
        if arg not in opts:
            print_usage()
            exit(1)

        opts[arg] = True

    _7days = timedelta(days = 7)

    current = get_desktop_wallpaper_path()
    mtime = current.stat().st_mtime
    isfresh = datetime.today() - datetime.fromtimestamp(mtime) < _7days

    if not opts['--force'] and isfresh:
        print('Aborting as the current wallpaper is already fresh')
        exit()

    set_latest_wallpaper_as_desktop(opts)
