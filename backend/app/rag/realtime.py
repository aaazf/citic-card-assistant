"""Realtime-intent allowlist for the bank customer assistant.

The assistant answers strictly from business materials. The only exception
is realtime-style questions (current date, weather, FX rates, ...), which
may be answered from general knowledge with an explicit disclaimer.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RealtimeCategory:
    key: str
    label: str
    keywords: tuple[str, ...]


REALTIME_CATEGORIES: tuple[RealtimeCategory, ...] = (
    RealtimeCategory(
        key="datetime",
        label="日期时间",
        keywords=(
            "现在几点",
            "几点了",
            "现在时间",
            "当前时间",
            "今天几号",
            "几号了",
            "星期几",
            "周几",
            "现在日期",
            "今天日期",
            "放假安排",
            "什么时候放假",
            "节假日",
            "假期安排",
        ),
    ),
    RealtimeCategory(
        key="weather",
        label="天气",
        keywords=(
            "天气",
            "气温",
            "多少度",
            "下雨",
            "下雪",
            "空气质量",
            "雾霾",
            "pm2.5",
            "紫外线",
        ),
    ),
    RealtimeCategory(
        key="exchange_rate",
        label="外汇汇率",
        keywords=(
            "汇率",
            "牌价",
            "换汇",
            "结汇",
            "购汇",
            "美元兑",
            "欧元兑",
            "日元兑",
            "港币兑",
        ),
    ),
    RealtimeCategory(
        key="market_rate",
        label="市场利率",
        keywords=(
            "lpr",
            "基准利率",
            "存款利率",
            "贷款利率",
            "降息",
            "加息",
            "存款准备金率",
        ),
    ),
    RealtimeCategory(
        key="gold",
        label="贵金属行情",
        keywords=(
            "金价",
            "黄金价格",
            "白银价格",
            "铂金价格",
            "贵金属价格",
        ),
    ),
    RealtimeCategory(
        key="stock",
        label="股市基金行情",
        keywords=(
            "股市",
            "股票",
            "大盘",
            "上证指数",
            "沪指",
            "深证成指",
            "创业板指",
            "a股",
            "基金净值",
        ),
    ),
    RealtimeCategory(
        key="fuel",
        label="油价",
        keywords=(
            "油价",
            "汽油价格",
            "柴油价格",
            "92号",
            "95号",
        ),
    ),
    RealtimeCategory(
        key="news",
        label="新闻资讯",
        keywords=(
            "新闻",
            "热搜",
            "头条",
        ),
    ),
)


def detect_realtime_category(query: str) -> RealtimeCategory | None:
    lowered = query.lower()
    for category in REALTIME_CATEGORIES:
        if any(keyword in lowered for keyword in category.keywords):
            return category
    return None


def build_realtime_system_prompt(
    category: RealtimeCategory,
    now: datetime | None = None,
) -> str:
    now = now or datetime.now().astimezone()
    weekday = "一二三四五六日"[now.weekday()]
    return (
        "你是中信银行信用卡智能客服。客户询问的是实时信息类问题"
        f"（{category.label}），不在信用卡业务资料范围内，可以使用通用知识简要回答。\n"
        f"当前服务器时间：{now:%Y年%m月%d日} 星期{weekday} {now:%H:%M}。\n"
        "回答规则：\n"
        "1. 开头标注“以下为通用信息，仅供参考”。\n"
        "2. 日期、时间、星期类问题，根据上面的服务器时间准确回答。\n"
        "3. 天气、汇率、金价、行情等无法联网核实的数据，不要编造具体数值，"
        "改为告知查询渠道（中信银行手机银行 App、官方网站或权威平台）。\n"
        "4. 结尾提示：信用卡业务问题可以继续咨询，或致电客服热线 95558。"
    )
