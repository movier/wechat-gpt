import requests

data = """<xml>
    <ToUserName><![CDATA[gh_b0c7b706a4bd]]></ToUserName>
    <FromUserName><![CDATA[o5swUt-rzSGqTAyKuwTnQQMUKMeQ]]></FromUserName>
    <CreateTime>1699931014</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[在吗？]]></Content>
    <MsgId>24337158128753593</MsgId>
</xml>"""
headers = {"Content-Type": "application/xml"}
r = requests.post(
    "http://localhost:8000/wechat/?signature=7fc9f06bbfa1717fea29e20b021a528f2ad8e917&timestamp=1699931656&nonce=368012531&openid=o5swUt-rzSGqTAyKuwTnQQMUKMeQ",
    data=data.encode('utf-8'),
    headers=headers
)
print(r)
