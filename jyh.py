#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2016-01-28 15:21:29
# author:Gavinb
# Project: jyh

import requests
import json
import re
import os

from flask import request, current_app
from pyspider.database.mysql.mysqldb import SQL
from urllib import quote
from pyspider.libs.base_handler import *

class Handler(BaseHandler):
    crawl_config = {

    }

    # 列表页地址，目标只是饰品类目，如果需要抓全站，可以根据导航栏内容获取全量categroyCodeKey
    url = 'http://www.jyh.com/web/list/listcontent?page={page}&size=20&search=%E7%AE%B1%E5%8C%85%E9%85%8D%E9%A5%B0&categroyCodeKey=449720090007&selectFacetTwo=1&newArrival=0'
    
    # 商品的价格是通过api接口动态获取的，地址和请求内容通过 fiddler 工具获取
    url_price = 'http://www.jyh.com/jsonapi/com_cmall_homepool_api_ApiGetProductPrice?api_key=betacpool&api_input=%7B%22version%22%3A1%2C%22api_token%22%3A%22%22%2C%22productCode%22%3A%22{code}%22%2C%22skuCode%22%3A%22%22%7D&api_token=&api_target=com_cmall_homepool_api_ApiGetProductPrice'

    # 商品的备注信息是通过api接口动态获取的，地址和请求内容通过 fiddler 工具获取
    url_detail = "http://www.jyh.com/jsonapi/com_cmall_homepool_api_ApiGetProductDescription?api_key=betacpool&api_input=%7B%22version%22%3A1%2C%22productCode%22%3A%22{code}%22%7D&api_token=&api_target=com_cmall_homepool_api_ApiGetProductDescription"

    # 动态监控，24小时运行
    @every(minutes=24 * 60)

    # 偷懒了，实际上判断一下页面返回值内容，就可以了，偷懒的做法是自己看一下有几页，直接写了页面地址上限
    def on_start(self):
        page = 0
        while(page < 6):
            page = page + 1
            self.crawl(self.url.format(page=page), callback=self.index_page)
    
    #分析页面内容并拆解列表页商品编号、图片和名称，将突破保存在本地目录下
    def index_page(self, response):
        for each in response.doc('li').items():
            code = each(".sprice").attr.id
            img = each("img").attr.src
            name = each(".sname ").text()
            #保存图片到本地
            img_url =img
            img_file = "/Users/Gavin/python/jyh/{code}.jpg"
            img_file = img_file.format(code=code)

            if not os.path.isfile(img_file):
                r = requests.get(img_url)
                with open(img_file, "wb") as rcode:
                    rcode.write(r.content)
                    
            result = {
                "code" : code,
                "img" : img,
                "name" : name
            }
            
            #获取价格信息
            self.crawl(self.url_price.format(code=code), callback=self.json_parser_price, save=result)

    #数据时间有效性 日*小时*分*秒
    config(age=1 * 24 * 60 * 60)
    
    #解析获取价格接口的返回内容
    def json_parser_price(self, response):     
        code = response.save['code']
        result = {
            "code":response.json['skuCode'],
            "name":response.save['name'],
            "img":response.save['img'],
            "skuAdv":response.json['skuAdv'],
            "sellPrice":response.json['sellPrice'],
            "marketPrice":response.json['marketPrice'],
            "stockNum":response.json['stockNum'],
            "skuPropertyInfo":response.json['skuPropertyInfo'],
            "salesCount":response.json['salesCount'],
            "points":response.json['points'],
            "brandName":response.json['brandName'],
            "sysDateTime":response.json['sysDateTime']
        }
        #获取资料信息
        self.crawl(self.url_detail.format(code=code), callback=self.json_parser_detail, save=result)

    #解析获取备注信息接口的返回内容，并将内容保存到mysql中
    def json_parser_detail(self, response):
        code = response.save['code']
        sql = SQL()
        desc = ""
        for x in response.json['propertyInfoList']:
            desc = desc + x['propertykey'] + ":" + x['propertyValue'] + ";"

        result = {
            "code":response.save['code'],
            "name":response.save['name'],
            "img":response.save['img'],
            "skuAdv":response.save['skuAdv'],
            "sellPrice":response.save['sellPrice'],
            "marketPrice":response.save['marketPrice'],
            "stockNum":response.save['stockNum'],
            "skuPropertyInfo":response.save['skuPropertyInfo'],
            "salesCount":response.save['salesCount'],
            "points":response.save['points'],
            "brandName":response.save['brandName'],
            "sysDateTime":response.save['sysDateTime'],
            "content" : desc
        }
        sql.replace('jyhgoods',**result)
        return response.save['name']

