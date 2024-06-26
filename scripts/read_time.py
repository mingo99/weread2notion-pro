import os

import pendulum
from config import tz
from notion_helper import NotionHelper
from utils import (get_date, get_icon, get_number, get_relation, get_title,
                   get_wolai_icon_url, upload_heatmap)
from weread_api import WeReadApi


def insert_to_notion(page_id, timestamp, duration):
    date = pendulum.from_timestamp(timestamp, tz=tz)
    parent = {"database_id": notion_helper.day_database_id, "type": "database_id"}
    properties = {
        "标题": get_title(date.strftime("%Y年%m月%d日")),
        "日期": get_date(
            start=date.format(
                "YYYY-MM-DD HH:mm:ss"
            )
        ),
        "时长": get_number(duration),
        "时间戳": get_number(timestamp),
        "年": get_relation(
            [
                notion_helper.get_year_relation_id(date),
            ]
        ),
        "月": get_relation(
            [
                notion_helper.get_month_relation_id(date),
            ]
        ),
        "周": get_relation(
            [
                notion_helper.get_week_relation_id(date),
            ]
        ),
    }

    icon_url = get_wolai_icon_url(date.format("YYYY-MM-DD"),"D")

    if page_id != None:
        notion_helper.client.pages.update(page_id=page_id, icon=get_icon(icon_url), properties=properties)
    else:
        notion_helper.client.pages.create(
            parent=parent,
            icon=get_icon(icon_url),
            properties=properties,
        )


def get_file():
    # 设置文件夹路径
    folder_path = "./OUT_FOLDER"

    # 检查文件夹是否存在
    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        entries = os.listdir(folder_path)

        file_name = entries[0] if entries else None
        return file_name
    else:
        print("OUT_FOLDER does not exist.")
        return None


if __name__ == "__main__":
    notion_helper = NotionHelper()
    weread_api = WeReadApi()
    image_file = get_file()
    if image_file:
        image_url = upload_heatmap(image_file)
        block_id = os.getenv("HEATMAP_BLOCK_ID")
        if block_id == None or block_id.strip() == "":
            block_id = notion_helper.image_dict.get("id")
        if image_url and block_id:
            notion_helper.update_image_block_link(block_id, image_url)
    api_data = weread_api.get_api_data()
    readTimes = {int(key): value for key, value in api_data.get("readTimes").items()}
    now = pendulum.now("Asia/Shanghai").start_of("day")
    today_timestamp = now.int_timestamp
    if today_timestamp not in readTimes:
        readTimes[today_timestamp] = 0
    readTimes = dict(sorted(readTimes.items()))
    results = notion_helper.query_all(database_id=notion_helper.day_database_id)
    for result in results:
        timestamp = result.get("properties").get("时间戳").get("number")
        duration = result.get("properties").get("时长").get("number")
        id = result.get("id")
        if timestamp in readTimes:
            value = readTimes.pop(timestamp)
            if value != duration:
                insert_to_notion(page_id=id, timestamp=timestamp, duration=value)
    for key, value in readTimes.items():
        insert_to_notion(None, int(key), value)
