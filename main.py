# main.py 主逻辑：包括字段拼接、模拟请求
import json
import time
import random
import logging
import hashlib
import requests
import urllib.parse
from push import push
from config import data, headers, cookies, READ_NUM, PUSH_METHOD, reading_sessions

# 配置日志格式
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)-8s - %(message)s')

# 加密盐及其它默认值
KEY = "3c5c8717f3daf09iop3423zafeqoi"
# 续签接口的多种payload变体，依次尝试以兼容接口变更（移植自上游 fix: wr_skey）
COOKIE_DATA_VARIANTS = [
    {"rq": "%2Fweb%2Fbook%2Fread", "ql": False},
    {"rq": "%2Fweb%2Fbook%2Fread", "ql": True},
    {"rq": "%2Fweb%2Fbook%2Fread"},
]
READ_URL = "https://weread.qq.com/web/book/read"
RENEW_URL = "https://weread.qq.com/web/login/renewal"
FIX_SYNCKEY_URL = "https://weread.qq.com/web/book/chapterInfos"

# 添加全局requests session以保持连接
session = requests.Session()

# 网络级异常的退避重试间隔：瞬时抖动通常在1分钟内恢复，总计可容忍约7.5分钟中断
NETWORK_RETRY_DELAYS = (30, 60, 120, 240)
# 续签失败后的整轮重试间隔（每轮内部已依次尝试3种payload变体）
REFRESH_RETRY_DELAYS = (60, 120)


def encode_data(data):
    """数据编码"""
    return '&'.join(f"{k}={urllib.parse.quote(str(data[k]), safe='')}" for k in sorted(data.keys()))


def cal_hash(input_string):
    """计算哈希值"""
    _7032f5 = 0x15051505
    _cc1055 = _7032f5
    length = len(input_string)
    _19094e = length - 1

    while _19094e > 0:
        _7032f5 = 0x7fffffff & (_7032f5 ^ ord(input_string[_19094e]) << (length - _19094e) % 30)
        _cc1055 = 0x7fffffff & (_cc1055 ^ ord(input_string[_19094e - 1]) << _19094e % 30)
        _19094e -= 2

    return hex(_7032f5 + _cc1055)[2:].lower()


def get_wr_skey():
    """刷新cookie密钥：依次尝试多种payload变体，从响应cookies中提取wr_skey"""
    for cookie_data in COOKIE_DATA_VARIANTS:
        try:
            response = session.post(RENEW_URL, headers=headers, cookies=cookies,
                                    data=json.dumps(cookie_data, separators=(',', ':')),
                                    timeout=30)
            if response.status_code != 200:
                logging.warning(f"RENEW_URL请求失败（payload={cookie_data}），状态码: {response.status_code}")
                continue

            if 'wr_skey' in response.cookies:
                skey = response.cookies['wr_skey'][:8]  # 取前8位
                logging.info(f"✅ 成功提取到wr_skey: {skey[:2]}***")
                return skey

            logging.warning(f"RENEW_URL响应中无wr_skey（payload={cookie_data}）")
        except requests.exceptions.RequestException as e:
            logging.warning(f"RENEW_URL请求异常（payload={cookie_data}）: {e}")
    return None


def fix_no_synckey():
    try:
        response = session.post(FIX_SYNCKEY_URL, headers=headers, cookies=cookies,
                                data=json.dumps({"bookIds":["3300060341"]}, separators=(',', ':')),
                                timeout=30)
        logging.info(f"FIX_SYNCKEY_URL response status: {response.status_code}")
        logging.info(f"FIX_SYNCKEY_URL response: {response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"请求FIX_SYNCKEY_URL时发生异常: {e}")
    except Exception as e:
        logging.error(f"处理FIX_SYNCKEY_URL响应时发生异常: {e}")


def post_with_retry(url, **kwargs):
    """发起POST请求，网络级异常按间隔退避重试，重试耗尽后抛出最后一个异常"""
    try:
        return session.post(url, **kwargs)
    except requests.exceptions.RequestException as e:
        for delay in NETWORK_RETRY_DELAYS:
            logging.warning(f"🌐 网络异常: {e}，{delay}秒后重试...")
            time.sleep(delay)
            try:
                return session.post(url, **kwargs)
            except requests.exceptions.RequestException as exc:
                e = exc
        raise e


def refresh_cookie():
    """刷新cookie：多轮重试容忍续签接口瞬时故障，全部失败才推送并终止"""
    for round_no in range(1, len(REFRESH_RETRY_DELAYS) + 2):
        logging.info(f"🍪 刷新cookie（第 {round_no} 轮）")
        new_skey = get_wr_skey()
        if new_skey:
            cookies['wr_skey'] = new_skey
            logging.info(f"✅ 密钥刷新成功，新密钥：{new_skey[:2]}***")
            logging.info(f"🔄 重新本次阅读。")
            return
        if round_no <= len(REFRESH_RETRY_DELAYS):
            delay = REFRESH_RETRY_DELAYS[round_no - 1]
            logging.warning(f"本轮续签失败，{delay}秒后重试...")
            time.sleep(delay)
    ERROR_CODE = "❌ 无法获取新密钥或者WXREAD_CURL_BASH配置有误，终止运行。"
    logging.error(ERROR_CODE)
    push(ERROR_CODE, PUSH_METHOD, is_success=False)
    raise Exception(ERROR_CODE)

# 随机启动延迟 0~15 分钟，消除固定时间点触发的规律性特征
startup_delay = random.randint(0, 180)  # 0~3分钟，cron已错开整点，无需更长延迟
logging.info(f"⏳ 随机启动延迟 {startup_delay // 60} 分 {startup_delay % 60} 秒...")
time.sleep(startup_delay)

refresh_cookie()
index = 1
# 累计阅读时间（秒）
total_read_time = 0
# 设置初始lastTime为当前时间减去一个30-45秒之间的随机值
random_interval = random.randint(30, 45)
lastTime = int(time.time()) - random_interval
logging.info(f"⏱️ 一共需要阅读 {READ_NUM} 次...")

# 整次运行只"读"一本书：按书ID分组后随机选定，在该书的快照中随机切换章节/位置
_book_ids = list({s['b'] for s in reading_sessions})
_chosen_book = random.choice(_book_ids)
book_sessions = [s for s in reading_sessions if s['b'] == _chosen_book]
logging.info(f"📚 本次选定书籍（ID: {_chosen_book}），共 {len(book_sessions)} 个阅读快照")

while index <= READ_NUM:
    data.pop('s', None)  # 使用pop的默认值避免KeyError
    # 在当前书的快照中随机选位置，保证 b/c/ci/co/sm/ps/pc 七个字段内部一致
    session_snap = random.choice(book_sessions)
    data.update({k: session_snap[k] for k in ('b', 'c', 'ci', 'co', 'sm', 'ps', 'pc')})
    thisTime = int(time.time())
    data['ct'] = thisTime
    data['rt'] = thisTime - lastTime
    data['ts'] = int(thisTime * 1000) + random.randint(0, 1000)
    data['rn'] = random.randint(0, 1000)
    data['sg'] = hashlib.sha256(f"{data['ts']}{data['rn']}{KEY}".encode()).hexdigest()
    data['s'] = cal_hash(encode_data(data))

    logging.info(f"⏱️ 尝试第 {index} 次阅读...")
    logging.info(f"📕 data: {data}")
    try:
        response = post_with_retry(READ_URL, headers=headers, cookies=cookies,
                                   data=json.dumps(data, separators=(',', ':')), timeout=30)
        resData = response.json()
        logging.info(f"📕 response: {resData}")
    except requests.exceptions.RequestException as e:
        # 网络级异常已退避重试多次仍失败，说明中断时间超过容忍窗口，明确失败并终止
        ERROR_CODE = f"❌ 网络持续异常（已退避重试{len(NETWORK_RETRY_DELAYS)}次），终止运行: {e}"
        logging.error(ERROR_CODE)
        push(ERROR_CODE, PUSH_METHOD, is_success=False)
        raise Exception(ERROR_CODE)
    except Exception as e:
        logging.error(f"处理READ_URL响应时发生异常: {e}")
        logging.warning("❌ 响应处理异常，尝试刷新cookie...")
        refresh_cookie()
        continue

    if 'succ' in resData:
        # 检查是否有 synckey
        if 'synckey' in resData:
            lastTime = thisTime
            index += 1
            # ── 真实阅读时间模型 ────────────────────────────────────────────
            # 1. 正态分布休眠：均值37秒，标准差8秒，夹在20~90秒之间
            sleep_time = int(max(20, min(90, random.gauss(37, 8))))

            # 2. 时段感知：凌晨0~7点模拟用户疲劳，阅读节奏放慢1.5倍
            current_hour = time.localtime().tm_hour
            if 0 <= current_hour < 7:
                sleep_time = int(sleep_time * 1.5)
                logging.info(f"🌙 凌晨时段，阅读节奏放慢，调整休眠至 {sleep_time} 秒")

            # 3. 偶发长停顿：5% 概率模拟翻页思考（120~300秒）
            if random.random() < 0.05:
                long_pause = random.randint(120, 300)
                logging.info(f"💭 模拟翻页思考，额外停顿 {long_pause} 秒...")
                time.sleep(long_pause)
                total_read_time += long_pause
            # ────────────────────────────────────────────────────────────────

            time.sleep(sleep_time)
            # 累计实际阅读时间
            total_read_time += sleep_time
            logging.info(f"✅ 阅读成功，累计阅读：{total_read_time // 60}分{total_read_time % 60}秒，本次休眠{sleep_time}秒")
        else:
            # succ为真但没有synckey，调用chapterInfos接口刷新
            logging.warning("❌ 无synckey, 尝试修复...")
            fix_no_synckey()
    elif 'errCode' in resData and resData['errCode'] == -2012:
        # errCode为-2012时，需要刷新cookie的wr_skey
        logging.warning("❌ errCode为-2012, 尝试刷新cookie...")
        refresh_cookie()
    else:
        logging.warning("❌ cookie 已过期或其他错误，尝试刷新...")
        refresh_cookie()

logging.info("🎉 阅读脚本已完成！")

if PUSH_METHOD not in (None, ''):
    logging.info("⏱️ 开始推送...")
    push(f"🎉 微信读书自动阅读完成！\n⏱️ 阅读时长：{total_read_time // 60}分{total_read_time % 60}秒。", PUSH_METHOD, is_success=True)
