# 导入函数库
from jqdata import *
from jqfactor import Factor, calc_factors
import datetime
import numpy as np
import pandas as pd


# 初始化函数，设定基准等等
def initialize(context):
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 开启动态复权模式(真实价格)
    set_option('use_real_price', True)
    # 输出内容到日志 log.info()
    log.info('初始函数开始运行且全局只运行一次')
    # 过滤掉order系列API产生的比error级别低的log
    log.set_level('order', 'error')
    # g.security = "000300.XSHG"
    g.security = get_index_stocks("000300.XSHG")

    ### 股票相关设定 ###
    # 股票类每笔交易时的手续费是：买入时佣金万分之三，卖出时佣金万分之三加千分之一印花税, 每笔交易佣金最低扣5块钱
    set_order_cost(OrderCost(close_tax=0.001, open_commission=0.0003, close_commission=0.0003, min_commission=5),
                   type='stock')

    g.N = 10
    g.q = query(valuation).filter(valuation.code.in_(g.security))
    run_daily(select)


def select(context):
    df = get_fundamentals(g.q)
    df = df.sort_values("market_cap")
    df = df[:g.N]
    tohold = df["code"].values

    for stock in context.portfolio.positions:
        if stock not in tohold:
            # 卖出
            order_target(stock, 0)

    tobuy = [stock for stock in tohold if stock not in context.portfolio.positions]
    n = len(tobuy)

    # 对每一只股票进行操作
    for stock in tobuy:
        handle(context, stock, n)


def handle(context, security, n):
    df = attribute_history(security, 50, '1d', 'close')
    cash = context.portfolio.available_cash / n

    # obtain the Shiryaev-Zhou index for 40-day moving window size
    df["u"] = np.log(df["close"] / (df["close"].shift(1)))
    df["index_40"] = (df["u"].rolling(40).mean()) / (df["u"].rolling(40).var()) - 0.5
    df = df.dropna()
    df["hold"] = 0

    # obtain the code when index >0
    for i in range(1, len(df)):
        if df["index_40"][i - 1] <= 0 and df["index_40"][i] > 0:
            df["hold"][i] = 1
        elif df["index_40"][i - 1] > 0 and df["index_40"][i] > 0:
            df["hold"][i] = 1

    if security not in context.portfolio.positions:
        if df["hold"][-1] == 1 and df["hold"][-2] == 1 and df["hold"][-3] == 1:
            order_value(security, cash)
            log.info("Buying {}".format(security))
    else:
        if df["hold"][-1] == 0:
            order_target(security, 0)
            log.info("Selling {}".format(security))
