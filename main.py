import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Wiki path searcher')
    parser.add_argument('--start_link', dest='start_link', type=str)
    parser.add_argument('--end_link', dest='end_link', type=str)
    parser.add_argument('--rate_limit', dest='rate_limit', type=int)

    args = parser.parse_args()

    print(args.start_link, args.end_link, args.rate_limit)