from io import StringIO
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import ast
from IPython.core.display import display, HTML
import itertools

def display_html_table(df, table_config):
    # given a dataframe
    # need to print it using html table, with certain column or a column has some font (color coding, strikethrough etc to share extra info)
    # display table

    #df = habit_action
    df = df.sort_values(by=table_config['column_sort_by'], ascending=table_config['column_sort_by_is_asc'])
    df.reset_index(drop=True, inplace=True)

    font_start_tag = "<font face='verdana' size='2' {text_font_attribute}><p align='{text_alignment}'>"
    font_end_tag = "</p></font>"
    # html_horizontal_ruler_in_table="<tr><td colspan='100'><hr/></td></tr>"
    html_horizontal_ruler_in_table = "<tr style='border-bottom:1px solid black'><td colspan='100%'></td></tr>"

    font_attributes = df.apply(table_config['func_giving_font_attribute'], axis=1)
    if table_config['column_name_whose_value_change_adds_horizontal_ruler'] is not None:
        val_change_index_for_horizontal_ruler = [sum(1 for _ in l) for n, l in itertools.groupby(
            df[table_config['column_name_whose_value_change_adds_horizontal_ruler']])]
        val_change_index_for_horizontal_ruler = [x - 1 for x in
                                                 pd.Series(val_change_index_for_horizontal_ruler).cumsum()][:-1]
    else:
        val_change_index_for_horizontal_ruler = []

    status = "<h3 align='center' style='color:grey;'>{table_heading}</h3>".format(
        table_heading=table_config['table_heading'])
    status += "<table width='100%'>"
    status += " ".join(
        ["<col width='{col_width}'>".format(col_width=str(x) + "%") for x in table_config['widths_in_pcntg']])
    status += "<tr>"
    status += " ".join(
        ["<th><p align='left'>{col_name}</p></th>".format(col_name=x) for x in table_config['column_headers']])
    status += "</tr>"

    for i in range(df.shape[0]):
        status += "<tr>"
        for j in range(len(table_config['column_name_in_order_of_display'])):
            column_name = table_config['column_name_in_order_of_display'][j]
            text_font_attribute = font_attributes[i] if table_config[
                                                            'column_name_needing_custom_formatting'] == column_name else ""
            text_alignment = table_config['text_alignment'][j]
            status += (
            "<td>" + font_start_tag.format(text_font_attribute=text_font_attribute, text_alignment=text_alignment) +
            str(df.loc[i, column_name]) + font_end_tag + "</td>")
        status += "</tr>"
        if i in val_change_index_for_horizontal_ruler:
            status += html_horizontal_ruler_in_table
    status += "</table>"
    display(HTML(status))


def add_my_numbers(x,y):
    return x+y