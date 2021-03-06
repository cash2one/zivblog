# !/usr/bin/python
# coding:utf-8

import logging

from models import tag as m_tag
from settings import STATUS_SAVE, STATUS_PUBLIC, STATUS_DELETE

COLL_ARTICLE = "article"

def is_unique_slug(db, slug, article_id):
    doc = db[COLL_ARTICLE].find_one({"slug":slug}, {"_id":True})
    if doc is None: return True
    if str(doc["_id"]) == article_id: return True
    return False

def update_article(db, article):
    slug = article["slug"]
    return db[COLL_ARTICLE].find_and_modify({"slug":slug}, {"$set":article},
                                            upsert=True, new=True)

def add_pageview(db, slug):
    db[COLL_ARTICLE].update({"slug":slug}, {"$inc":{"stat.pageview":1}}, w=1)

def delete_article(db, slug):
    delete_result = db[COLL_ARTICLE].delete_one({"slug":slug})
    return False if delete_result.deleted_count == 0 else True

def get_article(db, slug):
    return db[COLL_ARTICLE].find_one({"slug":slug})

def get_articles(db, tag=None, page=None, status=None, rows=0):
    filter_doc = {}
    if status is not None:
        filter_doc ["status"] = status
    if tag is not None:
        filter_doc ["tag"] = tag
    skip = rows * (page - 1) if page is not None else 0
    kwargs = {"limit":rows, "skip":skip, "sort":[("date", -1)]}
    articles_cursor = db[COLL_ARTICLE].find(filter_doc, {"_id":False}, **kwargs)
    articles = []
    article_status = {
        STATUS_SAVE: "save",
        STATUS_PUBLIC: "publish",
        STATUS_DELETE: "delete",
    }
    for article in articles_cursor:
        article["status"] = article_status.get(article["status"], "")
        articles.append(article)
    return articles

def get_hot_articles(db, limit=5):
    cursor = db[COLL_ARTICLE].find({}, {"slug":True, "title":True, "_id":False}) \
                             .sort([("stat.pageview", -1), ("_id", -1)]) \
                             .limit(limit)
    return [article for article in cursor]

def get_page_amount(db, rows, tag=None, status=None):
    article_amount = len(get_articles(db, tag=tag, status=status))
    if not isinstance(rows, int): return 0
    if rows == 0: return 0
    page_amount = article_amount % rows
    if page_amount == 0:
        # 0 / 5, 10 / 5
        page_amount = article_amount / rows
    else:
        # 1 / 5, 6 / 5
        page_amount = article_amount / rows + 1
    return page_amount

def get_tags_stats(db):
    def replace_default_amount(default_tags_stats, tag_name, amount):
        has_replace = False
        for tag_stat in default_tags_stats:
            if tag_stat["name"] == tag_name:
                tag_stat["amount"] = amount
                has_replace = True
                break
        if not has_replace:
            default_tags_stats.insert(0, {"name":tag_name, "amount":amount})

    pipeline = [
        {
            "$match":{"status":STATUS_PUBLIC}
        },
        {
            "$project":{"tag":1}
        },
        {
            "$group":{"_id":"$tag", "amount":{"$sum":1}}
        }
    ]
    cursor = db[COLL_ARTICLE].aggregate(pipeline)
    tags = m_tag.get_tags(db)
    # Set dufault stat.
    default_result = [{"name": tag_name, "amount":0} for tag_name in tags]
    for doc in cursor:
        replace_default_amount(default_result, doc["_id"], doc["amount"])
    return default_result

def get_article_id(db, slug):
    doc = db[COLL_ARTICLE].find_one({"slug":slug}, {"_id":True})
    if doc is None:
        return None
    return str(doc["_id"])