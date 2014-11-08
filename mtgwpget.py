import collections
import datetime
import math
import os
import os.path
import re
import sys
import urllib.request
import xml.parsers.expat
import time

from datetime import datetime, date, timedelta
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urljoin

WALLPAPER_LIST_URL = 'http://magic.wizards.com/en/articles/wallpapers' 
WALLPAPER_PATH = '~/_Home/Wallpaper/'

def nowstr():
    return str(datetime.now())

def print_(message):
    print(nowstr() + ' ' + message)

def get_wallpaper_urls(wallpaper_list_url):
    
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
            if (href.startswith('http://magic.wizards.com/sites/mtg/' + 
                               'files/images/wallpaper/') 
                and '1920x1080' in href
                and href.endswith('.jpg')):
                self.urls.append(urljoin(wallpaper_list_url, href))

    pagestring = open_page(wallpaper_list_url)

    linkfinder = WallpaperUrlSearcher()
    linkfinder.feed(pagestring)

    return linkfinder.urls

def open_page(url):
    print_('Opening ' + url)
    response = urllib.request.urlopen(url)
    charset = response.headers.get_content_charset()
    return response.read().decode(charset)

def download_latest_unused_wallpaper():
    urls = get_wallpaper_urls(WALLPAPER_LIST_URL)

    for url in urls:
        filename = url.split('/')[-1]
        local_path = os.path.join(os.path.expanduser(WALLPAPER_PATH), filename)
        if not os.path.exists(local_path):
            try:
                print_('Downloading ' + url + ' to ' + WALLPAPER_PATH)
                download_file(url, local_path)
            except urllib.error.HTTPError as error:
                print_('ERROR: Download failed with HTTP error ' + str(error.code))
            return local_path

def download_file(url, path):
    filename = url.split('/')[-1]
    response = urllib.request.urlopen(url)
    content_length = int(response.getheader('Content-Length'))

    print_('File size: ' + str(content_length // 1000) + 'kb')

    downloaded = 0
    chunk_length = int(10E3)

    with open(path, 'wb') as file_:
        while True:
            bytes_ = response.read(chunk_length)
            file_.write(bytes_)

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
    else:
        #TODO...
        pass

def set_as_desktop_wallpaper(path):
    if os.name == 'nt':
        SPI_SETDESKWALLPAPER = 0x0014
        SPIF_UPDATEINIFILE = 1
        SPIF_SENDWININICHANGE = 2

        from ctypes import windll
        windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, path,
            SPIF_UPDATEINIFILE or SPIF_SENDWININICHANGE)
    else:
        cmd = ('ln -sf {} {}'.format(
            path,
            os.path.join(WALLPAPER_PATH, 'current')))
        os.system(cmd)

def set_latest_wallpaper_as_desktop():
    print_('Starting wallpaper refresh')
    path = download_latest_unused_wallpaper()
    if path: 
        set_as_desktop_wallpaper(path)
    print_('Done')

if __name__ == '__main__':
    current = get_desktop_wallpaper_path()
    mtime = current.stat().st_mtime
    if datetime.fromtimestamp(mtime) > datetime.today() - timedelta(days = 7):
        print('Aborting as the current wallpaper is already fresh')
        exit()
    set_latest_wallpaper_as_desktop()
