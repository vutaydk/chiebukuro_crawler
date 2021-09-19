
import logging
import argparse
import asyncio

from chiebukuro import QuestionIDCrawler, QuestionDetailCrawler

logging.basicConfig(filename="log.txt", filemode="w", level=logging.INFO)
LOGGER = logging.getLogger()



parser = argparse.ArgumentParser()
parser.add_argument("--step2", help="get detail of question", type=str)
parser.add_argument("--step1", help="get id of questions of category")
args = parser.parse_args()

if __name__ == "__main__":
    if not args.step1 and not args.step2:#run all
        asyncio.run(QuestionIDCrawler().execute())
        QuestionDetailCrawler().execute()

    if args.step1:
        asyncio.run(QuestionIDCrawler().execute())
    if args.step2:
        QuestionDetailCrawler().execute()

