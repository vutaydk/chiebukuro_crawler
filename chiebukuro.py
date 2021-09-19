import os
import logging
import asyncio
import multiprocessing
import json
import shutil

from bs4 import BeautifulSoup

from utils import OUTPUT_DIR, Requester, chunks, save_json, save_html, FILE_STORAGE_CONFIG


LOGGER = logging.getLogger()
CPU_CORES = os.cpu_count()


CATEGORY_LISTING_PAGE = "https://chiebukuro.yahoo.co.jp/category"
ALL_POST_OF_CATEGORY_PAGE = "https://chiebukuro.yahoo.co.jp/category/{category_id}/question/list?flg=3&page={page}"
POST_DETAIL_PAGE_URL = "https://detail.chiebukuro.yahoo.co.jp/qa/question_detail/{question_id}?sort=1&page={page}"


class QuestionIDCrawler:
    OUT_FILENAME = "{category_id}_part_{index}.json"

    async def execute(self):
        categories_id = await self._get_all_category_id()

        with multiprocessing.Pool(CPU_CORES) as executor_pool:
            executor_pool.map(self.start_crawl, categories_id)
        
        LOGGER.info("Question ID crawling finished")

    def start_crawl(self, category_id):
        try:
            asyncio.run(self._get_all_question_id_of_cate(category_id))
        except Exception as e:
            LOGGER.exception(str(e))

    async def _get_all_category_id(self):
        """return all of leaf category id

        Leaf category is category doesn't have child category
        """

        def get_leaf_cates_urls(soup):
            """get all leaf categories in hierarchy tree

            grandparent A
                parent B
                    child C
                    child D
                parent E(no chid)
            grandparent F
                parent G
                    child F
                    child J
                parent K
                    child L
                    child H
            Output: C, D, E, F, J, L, H

            Args:
                soup ([type]): [description]

            Yields:
                dict: [description]
            """
            for grandparent_wrapper in soup.find_all(class_="ClapLv2CategoryList_Chie-CategoryList__CategoryWrapper__1dJCh"):
                for parent_wrapper in grandparent_wrapper.find_all("div"):
                    if "ClapLv2CategoryList_Chie-CategoryList__Category1TextWrapper__fG-4s" in parent_wrapper['class'] \
                        and (
                            not parent_wrapper.next_sibling
                            or "ClapLv2CategoryList_Chie-CategoryList__Category1TextWrapper__fG-4s"
                            in parent_wrapper.next_sibling['class']
                        ):
                        yield parent_wrapper.a['href']
                    if "ClapLv2CategoryList_Chie-CategoryList__Category2Wrapper__llQoL" in parent_wrapper["class"]:
                        for child in parent_wrapper.find_all("a"):
                            yield child['href']

        LOGGER.info("Crawling category list: Start")
        html = await Requester.get(CATEGORY_LISTING_PAGE)
        soup = BeautifulSoup(html, "html5lib")
        cates_url = get_leaf_cates_urls(soup)
        LOGGER.info("Crawling category list: Finished")
        # url ='/category/2080401272/question/list'
        return [url.split("/")[2] for url in cates_url]

    async def _get_all_question_id_of_cate(self, cate_id):
        LOGGER.info("Crawling questions of category: Start")
        for chunk_index, pages_in_chunk in enumerate(chunks(range(1, 101), 25)):
            questions_in_chunk = []
            for page in pages_in_chunk:
                html = await Requester.get(ALL_POST_OF_CATEGORY_PAGE.format(category_id=cate_id, page=page))
                if not html:
                    continue
                soup = BeautifulSoup(html, "html5lib")

                #because when you request the page that exceed max page it doesn't return error, it returns data of last page
                if soup.find(class_="ClapLv1Pagination_Chie-Pagination__Anchor--Current__2xIeZ").string != str(page):
                    LOGGER.warning("Excced max page number, you are trying to get page {}".format(page))
                    await save_json(questions_in_chunk, self.OUT_FILENAME.format(category_id=cate_id, index=chunk_index), FILE_STORAGE_CONFIG.QUESTION_STOCK)
                    LOGGER.info(f"Saving part {chunk_index} of questions of cateogry({cate_id}): Done")
                    return

                for qa in soup.find(id="qa_lst").find_all("a"):
                    try:
                        question_id = qa["href"].split("/")[-1]
                        questions_in_chunk.append(question_id)
                    except:
                        LOGGER.exception(f"fail extract question detail, question id: {question_id}")

            await save_json(questions_in_chunk, self.OUT_FILENAME.format(category_id=cate_id, index=chunk_index), FILE_STORAGE_CONFIG.QUESTION_STOCK)
            LOGGER.info(f"Saving part {chunk_index} of questions of cateogry({cate_id}): Done")
        LOGGER.info("Crawling questions of category: Done")


class QuestionDetailCrawler:
    def execute(self):
        with multiprocessing.Pool(CPU_CORES) as executor_pool:
            for dirpath, _, filenames in os.walk(FILE_STORAGE_CONFIG.QUESTION_STOCK):
                for filename in filenames:
                    if ".done" in filename:
                        continue
                    try:
                        executor_pool.apply(self.entry, args=( dirpath, filename))
                    except:
                        LOGGER.exception("")
    
    def entry(self, dirpath, filename):
        asyncio.run(self.xxx(dirpath, filename))

    async def xxx(self, dirpath, filename):
        category_id = filename.split("_")[0]

        input_filepath = os.path.join(dirpath, filename)
        with open(input_filepath, "r") as f:
            questions_id = json.load(f)

            LOGGER.info(f"Start get detail for {len(questions_id)} questions in file: {filename}")
            questions = await self._start_crawl(category_id, questions_id)

            out_filename = filename.replace("_part", "")
            await save_json(questions, out_filename)
            shutil.move(input_filepath, input_filepath + ".done")

            LOGGER.info(f"Saved {len(questions)} questions into file: {out_filename}")

    async def _start_crawl(self, category_id, questions_id):
        questions = []
        if not questions_id:
            return questions

        max_concurrent_task = 5
        tasks = []
        for q_id in questions_id:
            task = asyncio.create_task(self._crawl(category_id, q_id))
            tasks.append(task)
            if len(tasks) >= max_concurrent_task:
                tasks_result = await asyncio.gather(*tasks)
                questions.extend(tasks_result)
                tasks = []

        if tasks: #when tasks in last chunk is less than max_conccurent_number
            tasks_result = await asyncio.gather(*tasks)
            questions.extend(tasks_result)    

        return questions

    async def _crawl(sefl,category_id, question_id):
        def parse_answers(soup):
            answers = []
            answers_wrapper = soup.find_all(class_="ClapLv2AnswerItem_Chie-AnswerItem__Item__1lGUu")
            for wrapper in answers_wrapper:
                answer = {
                    "answer": "",
                    "replies": []
                }
                answer["answer"] = wrapper.find(class_="ClapLv2AnswerItem_Chie-AnswerItem__ItemText__3yFYH").get_text()

                reply_items = wrapper.find_all(class_="ClapLv2ReplyItem_Chie-ReplyItem__Item__1FMx3")
                for reply_item  in reply_items:
                    reply_text = reply_item.find(class_="ClapLv2ReplyItem_Chie-ReplyItem__ItemText__33ftJ").get_text()
                    answer["replies"].append(reply_text)
                
                answers.append(answer)
            return answers

        first_page_html = await Requester.get(POST_DETAIL_PAGE_URL.format(question_id=question_id, page=1))
        if not first_page_html:
            return
        await save_html(first_page_html, os.path.join(category_id, f"{question_id}_1.html"))

        qa = {
            "category": "",
            "question_id": question_id,
            "question": "",
            "thanks_comment": "",
            "answers": []
        }

        first_page = BeautifulSoup(first_page_html, "html5lib")
        question_wrapper = first_page.find(class_="ClapLv2QuestionItem_Chie-QuestionItem__Item__HQiuJ")
        qa["question"] = question_wrapper.find(class_="ClapLv2QuestionItem_Chie-QuestionItem__Text__1AI-5").get_text()
        qa["answers"].extend(parse_answers(first_page))
        thanks_wrapper = first_page.find(class_="ClapLv2Thanks_Chie-Thanks__3cXza")
        if thanks_wrapper:
            qa["thanks_comment"] = thanks_wrapper.find(class_="ClapLv2Thanks_Chie-Thanks__Text__1uplY").get_text()
        
        if not first_page.find(class_="ClapLv1Pagination_Chie-Pagination__2n_DF"): #have one page only
            return qa

        for page in range(2, 100):
            try:
                nth_page_url = POST_DETAIL_PAGE_URL.format(question_id=question_id, page=page)
                nth_page_html = await Requester.get(nth_page_url)
                if not nth_page_html:
                    continue
                save_html(nth_page_html, os.path.join(category_id, f"{question_id}_{page}.html"))
                nth_page = BeautifulSoup(first_page_html, "html5lib")

                #exceed maximum page number
                if nth_page.find(class_="ClapLv1Pagination_Chie-Pagination__Anchor--Current__2xIeZ").string != str(page):
                    break

                answers = parse_answers(nth_page)
                qa["answers"].extend(answers)
            except:
                LOGGER.exception(f"Extract answers of post fail: {nth_page_url}")
        return qa