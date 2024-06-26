import hashlib
import os
import re

import pendulum
from config import (DATE, FILES, NUMBER, RELATION, RICH_TEXT, SELECT, STATUS,
                    TITLE, URL, tz)
from github import Auth, Github

MAX_LENGTH = (
    1024  # NOTION 2000个字符限制https://developers.notion.com/reference/request-limits
)


def get_heading(level, content):
    if level == 1:
        heading = "heading_1"
    elif level == 2:
        heading = "heading_2"
    else:
        heading = "heading_3"
    return {
        "type": heading,
        heading: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:MAX_LENGTH],
                    },
                }
            ],
            "color": "default",
            "is_toggleable": False,
        },
    }


def get_table_of_contents():
    """获取目录"""
    return {"type": "table_of_contents", "table_of_contents": {"color": "default"}}


def get_title(content):
    return {"title": [{"type": "text", "text": {"content": content[:MAX_LENGTH]}}]}


def get_rich_text(content):
    return {"rich_text": [{"type": "text", "text": {"content": content[:MAX_LENGTH]}}]}


def get_url(url):
    return {"url": url}


def get_file(url):
    return {"files": [{"type": "external", "name": "Cover", "external": {"url": url}}]}


def get_multi_select(names):
    return {"multi_select": [{"name": name} for name in names]}


def get_relation(ids):
    return {"relation": [{"id": id} for id in ids]}


def get_date(start, end=None):
    return {
        "date": {
            "start": start,
            "end": end,
            "time_zone": "Asia/Shanghai",
        }
    }

def get_wolai_icon_url(date,icon_type,color="blue"):
    if icon_type == "Y":
        type_code = 5
    elif icon_type == "M":
        type_code = 4
    elif icon_type == "W":
        type_code = 10
    else:
        type_code = 1

    return f"https://api.wolai.com/v1/icon?type={type_code}&locale=cn&date={date}&color={color}"

def get_icon(url):
    return {"type": "external", "external": {"url": url}}


def get_select(name):
    return {"select": {"name": name}}


def get_number(number):
    return {"number": number}


def get_quote(content):
    return {
        "type": "quote",
        "quote": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content[:MAX_LENGTH]},
                }
            ],
            "color": "default",
        },
    }


def get_callout(content, style, colorStyle, reviewId):
    # 根据不同的划线样式设置不同的emoji 直线type=0 背景颜色是1 波浪线是2
    emoji = "〰️"
    if style == 0:
        emoji = "💡"
    elif style == 1:
        emoji = "⭐"
    # 如果reviewId不是空说明是笔记
    if reviewId != None:
        emoji = "✍️"
    color = "default"
    # 根据划线颜色设置文字的颜色
    if colorStyle == 1:
        color = "red"
    elif colorStyle == 2:
        color = "purple"
    elif colorStyle == 3:
        color = "blue"
    elif colorStyle == 4:
        color = "green"
    elif colorStyle == 5:
        color = "yellow"
    return {
        "type": "callout",
        "callout": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content[:MAX_LENGTH],
                    },
                }
            ],
            "icon": {"emoji": emoji},
            "color": color,
        },
    }


def get_rich_text_from_result(result, name):
    return result.get("properties").get(name).get("rich_text")[0].get("plain_text")


def get_number_from_result(result, name):
    return result.get("properties").get(name).get("number")


def format_time(time):
    """将秒格式化为 xx时xx分格式"""
    result = ""
    hour = time // 3600
    if hour > 0:
        result += f"{hour}时"
    minutes = time % 3600 // 60
    if minutes > 0:
        result += f"{minutes}分"
    return result


def get_properties(dict1, dict2):
    properties = {}
    for key, value in dict1.items():
        type = dict2.get(key)
        if value == None:
            continue
        property = None
        if type == TITLE:
            property = {
                "title": [{"type": "text", "text": {"content": value[:MAX_LENGTH]}}]
            }
        elif type == RICH_TEXT:
            property = {
                "rich_text": [{"type": "text", "text": {"content": value[:MAX_LENGTH]}}]
            }
        elif type == NUMBER:
            property = {"number": value}
        elif type == STATUS:
            property = {"status": {"name": value}}
        elif type == FILES:
            property = {
                "files": [
                    {"type": "external", "name": "Cover", "external": {"url": value}}
                ]
            }
        elif type == DATE:
            property = {
                "date": {
                    "start": pendulum.from_timestamp(
                        value, tz=tz
                    ).to_datetime_string(),
                    "time_zone": "Asia/Shanghai",
                }
            }
        elif type == URL:
            property = {"url": value}
        elif type == SELECT:
            property = {"select": {"name": value}}
        elif type == RELATION:
            property = {"relation": [{"id": id} for id in value]}
        if property:
            properties[key] = property
    return properties


def get_property_value(property):
    """从Property中获取值"""
    type = property.get("type")
    content = property.get(type)
    if content is None:
        return None
    if type == "title" or type == "rich_text":
        if len(content) > 0:
            return content[0].get("plain_text")
        else:
            return None
    elif type == "status" or type == "select":
        return content.get("name")
    elif type == "files":
        # 不考虑多文件情况
        if len(content) > 0 and content[0].get("type") == "external":
            return content[0].get("external").get("url")
        else:
            return None
    elif type == "date":
        return str_to_timestamp(content.get("start"))
    else:
        return content


def calculate_book_str_id(book_id):
    md5 = hashlib.md5()
    md5.update(book_id.encode("utf-8"))
    digest = md5.hexdigest()
    result = digest[0:3]
    code, transformed_ids = transform_id(book_id)
    result += code + "2" + digest[-2:]

    for i in range(len(transformed_ids)):
        hex_length_str = format(len(transformed_ids[i]), "x")
        if len(hex_length_str) == 1:
            hex_length_str = "0" + hex_length_str

        result += hex_length_str + transformed_ids[i]

        if i < len(transformed_ids) - 1:
            result += "g"

    if len(result) < 20:
        result += digest[0 : 20 - len(result)]
    md5 = hashlib.md5()
    md5.update(result.encode("utf-8"))
    result += md5.hexdigest()[0:3]
    return result


def transform_id(book_id):
    id_length = len(book_id)
    if re.match("^\d*$", book_id):
        ary = []
        for i in range(0, id_length, 9):
            ary.append(format(int(book_id[i : min(i + 9, id_length)]), "x"))
        return "3", ary

    result = ""
    for i in range(id_length):
        result += format(ord(book_id[i]), "x")
    return "4", [result]


def get_weread_url(book_id):
    return f"https://weread.qq.com/web/reader/{calculate_book_str_id(book_id)}"


def str_to_timestamp(date):
    if date == None:
        return 0
    dt = pendulum.parse(date)
    # 获取时间戳
    return int(dt.timestamp())


def upload_heatmap(image_name):
    token = os.getenv("GH_TOKEN")
    if token is None:
        raise ValueError("Secret 'GH_TOKEN' is not set.")

    picbed_repo = os.getenv("PICBED")
    if picbed_repo is None:
        raise ValueError("Secret 'PICBED' is not set.")

    heatmap_folder = os.getenv("HEATMAP_FOLDER")
    if heatmap_folder is None:
        heatmap_folder = "heatmap"

    remote_path = f"{heatmap_folder}/{image_name}"
    local_path = f"./OUT_FOLDER/{image_name}"

    auth = Auth.Token(token)
    gh = Github(auth=auth)
    repo = gh.get_repo(picbed_repo)

    heatmap = open(local_path, "rb")
    try:
        content = repo.get_contents(heatmap_folder)
        repo.delete_file(content[0].path, "Delete image", content[0].sha)
        repo.create_file(remote_path, "Update image", heatmap.read())
    except:
        repo.create_file(remote_path, "Upload image", heatmap.read())

    return f"https://fastly.jsdelivr.net/gh/{os.getenv('PICBED')}/{remote_path}"
