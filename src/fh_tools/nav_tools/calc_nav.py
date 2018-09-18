#! /usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author  : MG
@Time    : 2018/9/17 9:57
@File    : calc_nav.py
@contact : mmmaaaggg@163.com
@desc    : openpyxl, pandas, xlrd
"""
import xlrd
import xlutils
import xlwt
import re
import os
import pandas as pd
from src.fh_tools.fh_utils import date_2_str, str_2_date
from datetime import date, datetime
import logging

logger = logging.getLogger()


def update_nav_file(file_path, fund_nav_dic, cash=None, nav_date=date.today()):
    """
    更新净值文件中的净值
    :param file_path:
    :param fund_nav_dic:
    :param cash:
    :param nav_date:
    :return:
    """
    # nav_date 日期转换
    if nav_date is None:
        nav_date = date.today()
    elif isinstance(nav_date, str):
        nav_date = str_2_date(nav_date)

    file_path_name, file_extension = os.path.splitext(file_path)

    workbook = xlrd.open_workbook(file_path)
    sheet_names = workbook.sheet_names()
    for sheet_num, sheet_name in enumerate(sheet_names, start=0):
        sheet = workbook.sheet_by_name(sheet_name)
        # 取得名称，日期，份额数据
        fund_name = sheet.cell_value(0, 1)
        setup_date = xlrd.xldate_as_datetime(sheet.cell_value(1, 1), 0).date()
        volume = sheet.cell_value(2, 1)
        # 读取各种费用及借贷利息等信息
        fee_dic, loan_dic, name_last = {}, {}, ''
        row_num = 3
        cell_content = sheet.cell_value(row_num, 0)
        while cell_content != '日期' and cell_content != '':
            load_cost = sheet.cell_value(row_num, 5)
            if load_cost == '':
                # 费用
                name = sheet.cell_value(row_num, 0)
                fee_dic[name] = {
                    'name': sheet.cell_value(row_num, 0),
                    'rate': sheet.cell_value(row_num, 1),
                    'base_date': xlrd.xldate_as_datetime(sheet.cell_value(row_num, 3), 0).date(),
                }
                if name_last.find('管理费') == 0:
                    # 有些管理费，分段计费
                    fee_dic[name_last]['end_date'] = xlrd.xldate_as_datetime(sheet.cell_value(row_num, 3), 0).date()
            else:
                # 借款
                loan_dic[sheet.cell_value(row_num, 0)] = {
                    'name': sheet.cell_value(row_num, 0),
                    'rate': sheet.cell_value(row_num, 1),
                    'base_date': xlrd.xldate_as_datetime(sheet.cell_value(row_num, 3), 0).date(),
                    'load_cost': sheet.cell_value(row_num, 3),
                }
            row_num += 1
            cell_content = sheet.cell_value(row_num, 0)

        # 读取产品名称
        col_num = 1
        cell_content = sheet.cell_value(row_num, col_num)
        product_name_list = []
        while cell_content != '':
            product_name_list.append(cell_content)
            col_num += 3
            cell_content = sheet.cell_value(row_num, col_num)
        # 获取历史净值数据
        row_num += 1
        data_df = pd.read_excel(file_path, sheet_name=sheet_num, header=row_num, index_col=0).reset_index()
        data_df_new = data_df.append([None]).copy()
        last_row = data_df_new.shape[0] - 1
        data_df_new.iloc[last_row, 0] = nav_date
        tot_val = 0
        for prod_num, product_name in enumerate(product_name_list):
            col_num = 1 + prod_num * 3
            if product_name in loan_dic:
                # 借款：计算利息收入加上本金即为市值
                # 市值
                load_info_dic = loan_dic[product_name]
                value = load_info_dic['load_cost'] * (1 + load_info_dic['rate']) * (
                            nav_date - load_info_dic['base_date']).days / 365
                data_df_new.iloc[last_row, col_num + 2] = value
                tot_val += value
            else:
                # 净值类产品
                # nav = get_nav(product_name)
                if product_name in fund_nav_dic:
                    nav = fund_nav_dic[product_name]
                else:
                    logger.warning("%s 净值未查到，默认净值为 1", product_name)
                    nav = 1

                data_df_new.iloc[last_row, col_num] = nav
                # 份额不变
                data_df_new.iloc[last_row, col_num + 1] = data_df_new.iloc[last_row - 1, col_num + 1]
                # 市值
                value = float(data_df_new.iloc[last_row, col_num + 1]) * nav
                data_df_new.iloc[last_row, col_num + 2] = value
                tot_val += value

        # 更新现金
        if cash is None:
            cash = data_df_new['银行现金'].iloc[last_row - 1]
        data_df_new['银行现金'].iloc[last_row] = cash
        tot_val += cash

        # 计算费用
        tot_fee = 0
        for key, info_dic in fee_dic.items():
            end_date = info_dic.setdefault('end_date', nav_date)
            manage_fee = - (end_date - info_dic['base_date']).days / 365 * volume * info_dic['rate']
            data_df_new[key].iloc[last_row] = manage_fee
            tot_fee += manage_fee

        # 计算新净值
        data_df_new['总市值（费前）'].iloc[last_row] = tot_val
        data_df_new['总市值（费后）'].iloc[last_row] = tot_val + tot_fee
        data_df_new['净值（费前）'].iloc[last_row] = tot_val / volume
        data_df_new['净值（费后）'].iloc[last_row] = (tot_val + tot_fee) / volume

        # 保存文件
        # 再源文件基础上增量更新
        file_path_new = file_path_name + '_' + date_2_str(nav_date) + file_extension
        workbook_new = xlutils.copy.copy(workbook)
        sheet = workbook_new.get_sheet(sheet_num)
        # ctype = 1 # 类型 0 empty,1 string, 2 number, 3 date, 4 boolean, 5 error
        # xf = 0 # 扩展的格式化 (默认是0)
        style = xlwt.XFStyle()
        style.num_format_str = 'YYYY/M/D'
        # nav_date
        sheet.write(row_num + last_row + 1, 0, nav_date, style)
        # 各个产品的【净值	份额	市值】
        # 银行现金	管理费1	管理费2	托管费	总市值（费前）	净值（费前）	总市值（费后）	净值（费后）
        col_len = data_df_new.shape[1]
        for col_num in range(1, col_len):
            value = data_df_new.iloc[last_row, col_num]
            if value is None:
                continue
            style = xlwt.XFStyle()
            if value < 0:
                style.num_format_str = '_(#,##0.00_);[Red](#,##0.00)'
            else:
                style.num_format_str = '_(#,##0.00_);(#,##0.00)'
            sheet.write(row_num + last_row + 1, col_num, value, style)
        workbook_new.save(file_path_new)
        # 保存独立 DataFrame 文件
        file_path_df = file_path_name + '_df_' + date_2_str(nav_date) + file_extension
        data_df_new.to_excel(file_path_df)


def read_nav_files(folder_path):
    fund_dictionay = {}
    # folder_path = r'D:\WSPycharm\fund_evaluation\contact'
    file_names = os.listdir(folder_path)
    for file_name in file_names:
        # file_path = r'd:\Works\F复华投资\合同、协议\丰润\丰润一期\SK8992_复华丰润稳健一期_估值表_20170113.xls'
        file_path = os.path.join(folder_path, file_name)
        file_name_net, file_extension = os.path.splitext(file_path)
        if file_extension not in ('.xls', '.xlsx'):
            continue
        else:
            data_df = pd.read_excel(file_path, skiprows=1, header=0)
            # 获取净值
            data_df1 = pd.read_excel(file_path, skiprows=3, header=0)
            cum_nav = data_df1['科目名称'][data_df1['科目代码'] == '累计单位净值:']
            name, nav = data_df.columns[0][13:-6], float(cum_nav.values[0])
            fund_dictionay[name] = nav

    return fund_dictionay


if __name__ == "__main__":
    folder_path = r'd:\WSPych\RefUtils\src\fh_tools\nav_tools\product_nav'
    fund_nav_dic = read_nav_files(folder_path)
    file_path = r'D:\WSPych\RefUtils\src\fh_tools\nav_tools\净值计算模板 - 完整版.xls'
    cash = None
    update_nav_file(file_path, fund_nav_dic, cash=cash)
