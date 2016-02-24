#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2016-01-28 15:21:29
# Project: higo
import requests
import json
import re
import os

from functools import wraps
from flask import request, current_app
from pyspider.database.mysql.mysqldb import SQL
from urllib import quote
from pyspider.libs.base_handler import *

def jsonp(func):
    """Wraps JSONified output for JSONP requests."""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            data = str(func(*args, **kwargs).data)
            content = str(callback) + '(' + data + ')'
            mimetype = 'application/javascript'
            return current_app.response_class(content, mimetype=mimetype)
        else:
            return func(*args, **kwargs)
    return decorated_function
# 思路：
# higo的列表页直接用的搜索的接口，所以直接用搜索页面，发现他们的内容返回值用的jsonp，为了使用方便，把jsonp的内容处理为json的内容
class Handler(BaseHandler):
    crawl_config = {

    }

    keywords = ["项链", "手链", "手镯", "耳钉", "耳环", "戒指"]

    url = "http://search.lehe.com/search/goods/search?m=http%3A%2F%2Fsearch.lehe.com%2Fsearch%2Fgoods%2Fsearch&keyword={keyword}&page={page}&pageSize=10&account_id=&access_token=&v=0.1&sort=sv%2B&_=1454554812067&callback=jsonp2"

    @every(minutes=24*60, seconds=10)

    def on_start(self):
        for keyword in self.keywords:
            self.crawl(self.url.format(keyword=quote(keyword), page=1), callback=self.index_parser, save={'keyword':keyword})

    def index_parser(self, response):
        jsonp_content = response.content
        json_content = re.sub(r'([a-zA-Z_0-9\.]*\()|(\);?$)','',jsonp_content)
        decoded = json.loads(json_content)
        total = decoded['data']['total']
        page_limit = total / 10
        page = 0
        keyword = response.save['keyword']
        keyword = keyword.encode("utf-8")
        while(page <= page_limit):
            page = page + 1
            self.crawl(self.url.format(keyword=quote(keyword), page=page), callback=self.json_parser, save={'keyword':keyword})

    @config(age=1 * 24 * 60 * 60)
    def json_parser(self, response):
        jsonp_content = response.content
        json_content = re.sub(r'([a-zA-Z_0-9\.]*\()|(\);?$)','',jsonp_content)
        decoded = json.loads(json_content)
        keyword = response.save['keyword']
        keyword = keyword.encode("utf-8")
        sql = SQL()
        for x in decoded['data']['list']:
            if not x or not x['goodsPicUrl']:
                return
            img_url = x['goodsPicUrl']
            img_file = "/Users/Gavin/python/higo/{keyword}/{goodsId}.jpg"
            img_file = img_file.format(keyword=keyword, goodsId=x['goodsId'])

            if not os.path.isfile(img_file):
                r = requests.get(img_url)
                with open(img_file, "wb") as code:
                    code.write(r.content)

            result = {
                "goodsId": x['goodsId'],
                "goodsName": x['goodsName'],
                "price": x['price'],
                "salePrice": x['salePrice'],
                "goodsPicUrl": x['goodsPicUrl'],
                "isWish": x['isWish'],
                "class":keyword
                }
            sql.replace('goods',**result)
        return keyword

