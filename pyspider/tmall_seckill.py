#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2016-11-06 11:20:11
# Project: tmall_seckill

from pyspider.libs.base_handler import *
from datetime import datetime
from HTMLParser import HTMLParser
import json, re, urlparse

# 修改 db_tmall.py 最后一行连接数据库，每次修改需要重启 pyspider
import db_tmall


class Handler(BaseHandler):

    crawl_config = {
        'headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en;q=0.6,fr;q=0.4',
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2272.118 Safari/537.36',
        },
        'timeout': 20,
    }

    @every(minutes=60)
    def on_start(self):

        # 会场入口页
        url_index = 'https://1111.tmall.com/?wh_act_nativebar=2&wh_main=true'
        # pass to next mathod
        save = {'act_url': '1111.tmall.com'};

        self.crawl(url_index, callback=self.index_page, age=600, priority=9, auto_recrawl=True, force_update=True, save=save)


    @catch_status_code_error
    def index_page(self, response):

        # unescape html entity
        html_text = HTMLParser().unescape(response.text)

        # 当前会场页数据入库

        url_current = response.save['act_url'];
        title = response.doc('title').text().replace(u'-上天猫，就够了', '')
        datetime_now = datetime.now()

        act_item = {
            'act_url': url_current, 
            'title': title,
            'created_at': datetime_now, 
            'updated_at': datetime_now, 
        }

        n_insert = db_tmall.insert('tmall_acts', **act_item)

        select_item = db_tmall.select_one('select * from `tmall_acts` where act_url=?', url_current)
        act_id = select_item['id'] if 'id' in select_item else 0
        act_item['id'] = act_id

        n_update = db_tmall.update('update `tmall_acts` set updated_at=? where id=?', datetime_now, act_id)

        print act_item

        # 抓取页面内所有会场

        all_act = {}
        matches = re.finditer(u'pages.tmall\.com/wow/act/16495/[a-zA-Z0-9_\-\.]+', html_text)
        for m in matches:
            all_act[m.group(0)] = m.group(0)

        print all_act

        for act_url in all_act:
            self.crawl('https://' + act_url, callback=self.index_page, age=1200, save={'act_url': act_url})


        # 抽取页面内所有店铺 shop、活动页 campaign, type = 8

        all_shop = {}
        all_campaign = {}

        matches = re.finditer(u'([a-z0-9]+)\.tmall\.(com|hk)/campaign\-([a-zA-Z0-9_\-\.]+)', html_text)
        for m in matches:
            subdomain = m.group(1)
            campaign = subdomain + '.tmall.com/campaign-' + m.group(3)

            all_shop[subdomain] = subdomain
            all_campaign[campaign] = campaign

            shop_item = {
                'subdomain': subdomain, 
                'type': 8,
                'userId': '', 
                'shopId': '', 
                'wtId': '',
                'shopName': '', 
                'shopDomain': '', 
                'userRate': '',
                'xid': '',
                'shopAge': '',
                'city': '',
                'score1': 0,
                'score2': 0,
                'score3': 0,
                'offset1': 0,
                'offset2': 0,
                'offset3': 0,
                'created_at': datetime_now, 
                'updated_at': datetime_now, 
            }

            n_insert = db_tmall.insert('tmall_shops', **shop_item)
            n_update = db_tmall.update('update `tmall_shops` set type=8 where subdomain=? and type<8', subdomain)

            campaign_item = {
                'campaign': campaign, 
                'type': 8,
                'subdomain': subdomain, 
                'created_at': datetime_now, 
                'updated_at': datetime_now, 
            }

            n_insert = db_tmall.insert('tmall_campaigns', **campaign_item)
        

        # 抽取页面所有商品，type=8 会场页商品，type=9 是秒杀商品

        all_item = {}
        matches = re.finditer(u'detail\.tmall\.(com|hk)/([a-zA-Z0-9_\-\.\?&=]+)', html_text)
        for m in matches:
            url_p = urlparse.urlparse('http:' + m.group(0))
            query = urlparse.parse_qs(url_p.query)
            if 'id' in query:
                itemId = query['id'][0]
                all_item[itemId] = itemId

                item = {
                    'itemId': itemId, 
                    'type': 8,
                    'itemTitle': '',
                    'secKillTime': '',
                    'itemNum': 0,
                    'itemSecKillPrice': 0,
                    'itemTagPrice': 0,
                    'shop_id': 0,
                    'act_id': act_id,
                    'created_at': datetime_now, 
                    'updated_at': datetime_now, 
                }

                n_insert = db_tmall.insert('tmall_items', **item)

        print all_shop
        print all_campaign
        print all_item


#解析json 字符串，is_jsonp 出去外包括号
def json_decode(json_str, is_jsonp=False):
    if is_jsonp and '(' in json_str:
        p_str = json_str[json_str.find('(') + 1:]
        if ')' in p_str:
            json_str = p_str[0: p_str.rfind(')')]
    try:
        return json.loads(json_str)
    except ValueError:
        return False

