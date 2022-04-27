import argparse
import requests
import numpy as np
import re
import urllib.parse
import queue
import copy
from bs4 import BeautifulSoup
from ratelimiter import RateLimiter

# ограничение на один язык
LANG_PREFIX = 'en'


def get_links(page_content):
    soup = BeautifulSoup(page_content, 'html.parser')
    content = soup.find(id="bodyContent")

    if content:
        return np.array([unquote_link(link['href']) for link in content.find_all('a', href=True)])
    else:
        return np.empty()


def is_wiki_link(link):
    return re.search('(https://).*(wiki).*(/wiki/)', link)


def unquote_link(link):
    return urllib.parse.unquote_plus(link)


def get_full_wiki_link(link):
    global LANG_PREFIX

    # если ссылка уже корректно сформирована, то ничего не делаем
    if 'https' not in link:
        return 'https://' + LANG_PREFIX + '.wikipedia.org' + link
    else:
        return link


def find_wiki_path(start_link, end_link, rate_limit, max_depth):
    @RateLimiter(max_calls=rate_limit, period=60)
    def get_content(link):
        try:
            response = requests.get(link)
            return response.content if response.reason == 'OK' else ''
        except Exception as e:
            print(f'can\'t get content from {link}\n')
            return ''

    start_link = unquote_link(start_link)
    end_link = unquote_link(end_link)

    # глубина контролируется с помощью 2х очередей
    # current_links - очередь из ссылок текущего уровня глубины
    # next_links - очередь из ссылок следующего уровня глубины

    current_links = queue.Queue()
    next_links = queue.Queue()
    current_depth = 0
    next_links.put(start_link)

    # словарь пар типа [дочерняя ссылка : родительская ссылка]
    link_chain = {start_link: ''}

    # пока не достигли заданного уровня глубины
    while not next_links.empty():
        current_links.queue = copy.copy(next_links.queue)
        next_links.queue.clear()
        current_depth = current_depth + 1
        print(f'depth {current_depth}')

        # пока не перебрали все ссылки на текущем уровне глубины
        while not current_links.empty():
            current_link = current_links.get()
            print(f'parse {current_link} \n')

            content = get_content(current_link)

            if content:
                for next_link in get_links(content):
                    next_link = get_full_wiki_link(next_link)

                    if is_wiki_link(next_link):

                        # если нашли искомую ссылку
                        if next_link == end_link:
                            path = [end_link, current_link]
                            link = link_chain[current_link]

                            # восстанавливаем путь до начальной страницы
                            while link:
                                path.append(link)
                                link = link_chain[link]

                            print('path found:')

                            # меняем порядок цепочки ссылок
                            for link in path[::-1]:
                                print(link)

                            return

                        # если еще не использовали ссылку и не достигли максимальной глубины поиска
                        if (next_link not in link_chain) and current_depth != max_depth:
                            link_chain[next_link] = current_link
                            # print(f'add {next_link}')
                            next_links.put(next_link)

    print(f'path from {start_link} to {end_link} with depth {max_depth} was not found')


def get_wiki_link_lang(link):
    return re.search(r'(https://)(.*?)(.wiki)', args.start_link).group(2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wiki path searcher')
    parser.add_argument('--start_link', type=str, required=True, help='Wiki start page link')
    parser.add_argument('--end_link', type=str, required=True, help='Wiki destination page link')
    parser.add_argument('--rate_limit', type=int, default=20, help='Rate limit per minute')
    parser.add_argument('--depth', type=int, default=5, help='Search depth')
    args = parser.parse_args()

    if not is_wiki_link(args.start_link) or not is_wiki_link(args.end_link):
        print('You have to set only wiki page links')
        exit(-1)

    # получаем префикс языка

    start_link_lang = get_wiki_link_lang(args.start_link)
    end_link_lang = get_wiki_link_lang(args.end_link)

    if start_link_lang != end_link_lang:
        print('Wiki pages have to be in same language')
        exit(-1)

    LANG_PREFIX = start_link_lang

    find_wiki_path(args.start_link, args.end_link, args.rate_limit, args.depth)
