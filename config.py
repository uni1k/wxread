# config.py 自定义配置,包括阅读次数、推送token的填写
import os
import re

"""
可修改区域
默认使用本地值如果不存在从环境变量中获取值
"""

# 阅读次数 默认40次/20分钟
READ_NUM = int(os.getenv('READ_NUM') or 40)
# 需要推送时可选，可选pushplus、wxpusher、telegram
PUSH_METHOD = "" or os.getenv('PUSH_METHOD')
# pushplus推送时需填
PUSHPLUS_TOKEN = "" or os.getenv("PUSHPLUS_TOKEN")
# telegram推送时需填
TELEGRAM_BOT_TOKEN = "" or os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "" or os.getenv("TELEGRAM_CHAT_ID")
# wxpusher推送时需填
WXPUSHER_SPT = "" or os.getenv("WXPUSHER_SPT")
# SeverChan推送时需填
SERVERCHAN_SPT = "" or os.getenv("SERVERCHAN_SPT")


# read接口的bash命令，本地部署时可对应替换headers、cookies
curl_str = os.getenv('WXREAD_CURL_BASH')

# headers、cookies是一个省略模版，本地或者docker部署时对应替换
cookies = {
    'RK': 'oxEY1bTnXf',
    'ptcz': '53e3b35a9486dd63c4d06430b05aa169402117fc407dc5cc9329b41e59f62e2b',
    'pac_uid': '0_e63870bcecc18',
    'iip': '0',
    '_qimei_uuid42': '183070d3135100ee797b08bc922054dc3062834291',
    'wr_avatar': 'https%3A%2F%2Fthirdwx.qlogo.cn%2Fmmopen%2Fvi_32%2FeEOpSbFh2Mb1bUxMW9Y3FRPfXwWvOLaNlsjWIkcKeeNg6vlVS5kOVuhNKGQ1M8zaggLqMPmpE5qIUdqEXlQgYg%2F132',
    'wr_gender': '0',
}

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,ko;q=0.5',
    'baggage': 'sentry-environment=production,sentry-release=dev-1730698697208,sentry-public_key=ed67ed71f7804a038e898ba54bd66e44,sentry-trace_id=1ff5a0725f8841088b42f97109c45862',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
}


# 真实阅读快照列表
# 每条记录包含 b/c/ci/co/sm/ps/pc 七个强关联字段，来源于真实抓包，内部完全一致
# 新增书籍时，请确保同一条记录的所有字段来自同一次真实阅读请求
reading_sessions = [
    # 《明朝那些事》
    {"b":"f1e328e072710bfaf1e87e9","c":"10632e20319a1068c6e48be","ci":23,"co":12726,"sm":"具体的事务要处理，就整天到处转悠，不是去","ps":"aa832f307a96bc70g0114a3","pc":"95a32f707a96bc6fg015ae7"},
    {"b":"f1e328e072710bfaf1e87e9","c":"10632e20319a1068c6e48be","ci":23,"co":14889,"sm":"总而言之，言官很执著，很较真，当然，也很","ps":"aa832f307a96bc70g0114a3","pc":"95a32f707a96bc6fg015ae7"},
    {"b":"f1e328e072710bfaf1e87e9","c":"10632e20319a1068c6e48be","ci":23,"co":17562,"sm":"就是国初三都，其中在朱元璋的老家凤阳营造","ps":"aa832f307a96bc70g0114a3","pc":"95a32f707a96bc6fg015ae7"},
    {"b":"f1e328e072710bfaf1e87e9","c":"17d322b0319b17d63b160d0","ci":24,"co":379,"sm":"第十七章胡惟庸案件正是因为胡惟庸对朱元璋","ps":"aa832f307a96bc70g0114a3","pc":"95a32f707a96bc6fg015ae7"},

    # 《剑来》
    {"b": "dee32e1071db086fdeef491", "c": "9243256033ee9246444dd3e", "ci": 12, "co": 33364,
     "sm": "空。宁姚站在他身边。陈平安最后一次劝说道",
     "ps": "9c332ac07a96ba04g010693", "pc": "5a332c107a96ba03g014d5f"},
    {"b": "dee32e1071db086fdeef491", "c": "9243256033ee9246444dd3e", "ci": 12, "co": 37845,
     "sm": "茶。宋集薪坐在左边客人椅子上，单手把玩一",
     "ps": "9c332ac07a96ba04g010693", "pc": "5a332c107a96ba03g014d5f"},
    {"b": "dee32e1071db086fdeef491", "c": "d7332cd033efd7322ed7215", "ci": 13, "co": 374,
     "sm": "第九章天行健陈平安这些天经常往福禄街、桃",
     "ps": "9c332ac07a96ba04g010693", "pc": "5a332c107a96ba03g014d5f"},
    {"b": "dee32e1071db086fdeef491", "c": "d7332cd033efd7322ed7215", "ci": 13, "co": 10274,
     "sm": "影响，而他对于小镇的地理形势，完全不熟悉",
     "ps": "9c332ac07a96ba04g010693", "pc": "5a332c107a96ba03g014d5f"},
    {"b": "dee32e1071db086fdeef491", "c": "d7332cd033efd7322ed7215", "ci": 13, "co": 14200,
     "sm": "宋集薪脸色不悦。不远处的李家大宅，呼喝声",
     "ps": "9c332ac07a96ba04g010693", "pc": "5a332c107a96ba03g014d5f"},

    # 《认知觉醒》
    {"b": "6a732ce07201202c6a7b30a", "c": "a6832360236a684eceeee20", "ci": 10, "co": 378,
     "sm": "第四章专注力——情绪和智慧的交叉地带第一",
     "ps": "a29322207a96ba1ag012028", "pc": "fb432b407a96ba19g017fab"},
    {"b": "6a732ce07201202c6a7b30a", "c": "a6832360236a684eceeee20", "ci": 10, "co": 9724,
     "sm": "以前女儿练钢琴时，她妈妈会要求她把新学的",
     "ps": "a29322207a96ba1ag012028", "pc": "fb432b407a96ba19g017fab"},
    {"b": "6a732ce07201202c6a7b30a", "c": "b5332110237b53b3a3d68d2", "ci": 11, "co": 358,
     "sm": "第五章学习力——学习不是一味地努力第一节",
     "ps": "a29322207a96ba1ag012028", "pc": "fb432b407a96ba19g017fab"},
    {"b": "6a732ce07201202c6a7b30a", "c": "b5332110237b53b3a3d68d2", "ci": 11, "co": 13665,
     "sm": "角，最终能否获取深度学习的能力，只能靠你",
     "ps": "a29322207a96ba1ag012028", "pc": "fb432b407a96ba19g017fab"},

    # 《被讨厌的勇气》
    {"b": "8b9329607186dc198b9bdab", "c": "006328902a8006f52e91302", "ci": 11, "co": 397,
     "sm": "不为人知的心理学“第三巨头”青年：刚才您",
     "ps": "1dd325907a96ba2ag0132aa", "pc": "a2932fc07a96ba2ag010f2b"},
    {"b": "8b9329607186dc198b9bdab", "c": "006328902a8006f52e91302", "ci": 11, "co": 20291,
     "sm": "哲人：是的，人生中思考或行为的倾向。青年",
     "ps": "1dd325907a96ba2ag0132aa", "pc": "a2932fc07a96ba2ag010f2b"},
    {"b": "8b9329607186dc198b9bdab", "c": "006328902a8006f52e91302", "ci": 11, "co": 21516,
     "sm": "哲人：当然，并不是有意地选择了“这样的我",
     "ps": "1dd325907a96ba2ag0132aa", "pc": "a2932fc07a96ba2ag010f2b"},
    {"b": "8b9329607186dc198b9bdab", "c": "36332b302a9363663881960", "ci": 12, "co": 427,
     "sm": "[插图]第二夜一切烦恼都来自人际关系青年",
     "ps": "1dd325907a96ba2ag0132aa", "pc": "a2932fc07a96ba2ag010f2b"},
]

"""
建议保留区域|默认读三体，其它书籍自行测试时间是否增加
"""
data = {
    "appId":"wb182564874663h1426868428",
    "b":"f1e328e072710bfaf1e87e9",
    "c":"17d322b0319b17d63b160d0",
    "ci":24,
    "co":379,
    "sm":"第十七章胡惟庸案件正是因为胡惟庸对朱元璋",
    "pr":5,
    "rt":20,
    "ts":1776508136879,
    "rn":354,
    "sg":"49ef76ab92db7fc8f637d2f3509f26b551fb7dd1d15fcd411b40005eaa46a2b4",
    "ct":1776508136,
    "ps":"aa832f307a96bc70g0114a3",
    "pc":"95a32f707a96bc6fg015ae7",
    "s":"b8e247b3"
    }


def convert(curl_command):
    """提取bash接口中的headers与cookies
    支持 -H 'Cookie: xxx' 和 -b 'xxx' 两种方式的cookie提取
    """
    # 提取 headers
    headers_temp = {}
    for match in re.findall(r"-H '([^:]+): ([^']+)'", curl_command):
        headers_temp[match[0]] = match[1]

    # 提取 cookies
    cookies = {}

    # 从 -H 'Cookie: xxx' 提取
    cookie_header = next((v for k, v in headers_temp.items()
                         if k.lower() == 'cookie'), '')

    # 从 -b 'xxx' 提取
    cookie_b = re.search(r"-b '([^']+)'", curl_command)
    cookie_string = cookie_b.group(1) if cookie_b else cookie_header

    # 解析 cookie 字符串
    if cookie_string:
        for cookie in cookie_string.split('; '):
            if '=' in cookie:
                key, value = cookie.split('=', 1)
                cookies[key.strip()] = value.strip()

    # 移除 headers 中的 Cookie/cookie
    headers = {k: v for k, v in headers_temp.items()
              if k.lower() != 'cookie'}

    return headers, cookies


headers, cookies = convert(curl_str) if curl_str else (headers, cookies)
