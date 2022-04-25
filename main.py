import argparse
import requests
import numpy as np
import re
import urllib.parse
import queue
import copy
from bs4 import BeautifulSoup
from ratelimiter import RateLimiter


def get_links(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')
    return np.array([link['href'] for link in soup.find(id="bodyContent").find_all('a', href=True)])


def is_wiki_link(link):
    return '/wiki/' in link


def get_full_wiki_link(link):
    if 'http' not in link:
        if re.search('[а-яА-Я]', urllib.parse.unquote_plus(link)):
            return 'https://ru.wikipedia.org' + link
        else:
            return 'https://en.wikipedia.org' + link
    else:
        return link


def find_wiki_path(start_link, end_link, rate_limit, max_depth):

    @RateLimiter(max_calls=rate_limit, period=60)
    def get_content(link):
        response = requests.get(link)
        return response.content if response.reason == 'OK' else ''

    current_links = queue.Queue()
    next_links = queue.Queue()
    current_depth = 0

    next_links.put(start_link)
    link_chain = {start_link:''}

    while not next_links.empty():
        current_links.queue = copy.copy(next_links.queue)
        next_links.queue.clear()
        current_depth = current_depth + 1
        print(f'depth {current_depth}')

        while not current_links.empty():
            current_link = current_links.get()
            print(f'parse {current_link}')
            content = get_content(current_link)

            if content:
                for next_link in get_links(content):
                    if is_wiki_link(next_link):
                        next_link = get_full_wiki_link(next_link)

                        if next_link == end_link:
                            path = [end_link, current_link]
                            link = link_chain[current_link]

                            while link:
                                path.append(link)
                                link = link_chain[link]

                            print('path found:')
                            for link in path[::-1]:
                                print(link)

                            return

                        if (next_link not in link_chain) and current_depth != max_depth:
                            link_chain[next_link] = current_link
                            #print(f'add {next_link}')
                            next_links.put(next_link)

    print(f'path from {start_link} to {end_link} with depth {max_depth} was not found')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Wiki path searcher')
    parser.add_argument('--start_link', dest='start_link', type=str)
    parser.add_argument('--end_link', dest='end_link', type=str)
    parser.add_argument('--rate_limit', dest='rate_limit', type=int, default=20)
    parser.add_argument('--depth', dest='depth', type=int, default=5)
    args = parser.parse_args()

    find_wiki_path(args.start_link, args.end_link, args.rate_limit, args.depth)
