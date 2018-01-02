import simplenote as sn
from io import StringIO
import pandas as pd
import datetime as dt
import matplotlib.pyplot as plt
import ast
from IPython.core.display import display, HTML
import itertools
import my_util

pd.options.mode.chained_assignment = None
#reference_date=pd.datetime.strptime('2017/12/10','%Y/%m/%d')
#reference_date=dt.datetime.now()-dt.timedelta(days=4) # always cehck everything from yesterday's reference (which has already passed)
simplenote = sn.Simplenote('mohdjamal8453@gmail.com', 'simple123')
taskNoteKey="41d06e8ced6c42389127e0d727974230"
ilmNoteKey="5f7cb643ec884642b250954ff3996f8c"
ilmRevLogKey="9ad07e0dc9e84909b17795e101683c68"
monthlyGoalNoteKey="ba7047bd84204ab49e9e271a5b164675"
habitKey="7b7f2636562c4f28b42f942ab2b6210d"
habitLogKey="d9a739e149bc4169a90379436a7cfe1c"
habitRevisionActionMap='6bf90144f253442bbcf102779268973b'


def get_current_habits():
    """
    Reads habit metadata from simmple note and returns the same
    :return: habit metadata (data frame)
    """
    habitraw = simplenote.get_note(habitKey)
    habit = habitraw[0]['content'].splitlines()[1:]
    habit = [ln.replace("*", "").strip() for ln in habit]
    habitcsv = "\n".join(habit)
    dathabit = pd.read_csv(StringIO(habitcsv))
    dathabit.columns = [x.strip() for x in dathabit.columns]
    dathabit.name = dathabit.name.apply(lambda x: x.strip().lower())
    dathabit.streak_type = dathabit.streak_type.apply(lambda x: x.strip().lower())
    dathabit.small_desc = dathabit.small_desc.apply(lambda x: x.strip())
    dathabit.status = dathabit.status.apply(lambda x: x.strip().lower())
    # dathabit.review_cycle=dathabit.review_cycle.apply(lambda x:x.strip().lower())
    # dathabit.missed_review_cycle=dathabit.missed_review_cycle.apply(lambda x:x.strip().lower())
    dathabit.start_date = dathabit.start_date.apply(lambda x: x.strip().lower())
    dathabit.start_date = pd.to_datetime(dathabit.start_date, errors="coerce", format="%d/%m/%y")
    return dathabit


def get_habit_log(reference_date):
    """
    Reads habit log from simmple note and returns the same

    Rules to interpret a habit log record:
    * no star, no double dash and non empty string (after stripping) - it is date - so update current date
    * no comma - means its pass with no comment (/reason) - so simply add ",,p"
    * 1 comma - means it is pass with comments (stored in reason) - simply add ",p"
    * 2 comma - nothing to do (it is fail)
    * if no star and double hash - update current year --2017--

    :return: habit log (as data frame)
    """

    habitLograw = simplenote.get_note(habitLogKey)
    habitLog = habitLograw[0]['content'].splitlines()[1:]
    habit_log_str = ""
    current_year = dt.datetime.now().year
    current_date = ""
    for ln in habitLog:
        ln = ln.strip()
        if ln == "": continue
        if '*' in ln:
            num_of_commas = ln.count(",")
            if num_of_commas == 0:
                ln += ",,p"
            elif num_of_commas == 1:
                ln += ",p"
        elif '--' in ln:
            current_year = int(ln.replace("--", ""))
        else:
            current_date = ln + ' ' + str(current_year)
        habit_log_str = habit_log_str + "\n" + current_date + "," + ln
    habit_log_str = habit_log_str.splitlines()
    habit_log_str = [ln.replace("*", "") for ln in habit_log_str if ln.count(",") == 3]
    dathabitLog = pd.read_csv(StringIO('\n'.join(habit_log_str)), header=None,
                              names=['date', 'name', 'reason', 'status'])
    dathabitLog.columns = [ln.strip() for ln in dathabitLog.columns]
    dathabitLog['name'] = dathabitLog.name.apply(lambda x: str(x).lower().strip())
    dathabitLog['reason'] = dathabitLog.reason.apply(lambda x: str(x).lower().strip())
    dathabitLog['status'] = dathabitLog.status.apply(lambda x: str(x).lower().strip())
    dathabitLog.date = pd.to_datetime(dathabitLog.date, format='%b %d %Y')
    dathabitLog = dathabitLog.loc[dathabitLog.date <= reference_date, :]  # filter logs greater than reference_date
    dathabitLog = dathabitLog.sort_values(axis=0, by=['name', 'date'], ascending=False)
    is_earlier_then_ref_date = dathabitLog.date.apply(lambda x, reference_date: x.date() <= reference_date.date(),
                                                      args=[reference_date])
    dathabitLog = dathabitLog.loc[is_earlier_then_ref_date, :]
    return dathabitLog


def get_metrics_for_a_habit_streak(log_of_a_habit, streak_type, reference_date):
    """
    Determines streak metric from a single habit streak
    :param log_of_a_habit: log of a particular habit
    :param streak_type: either day or count
    :return: a dictionary with streak metrics (cur_streak, max_streak, last_break_length)
    """
    if(streak_type== "day"):
        tmp_gpb=log_of_a_habit.groupby(['date'], as_index=False).mean().sort_values('date', ascending=False)
        tmp_gpb=tmp_gpb.reset_index(drop=True)
        tmp_gpb.loc[tmp_gpb.status<1,'status']=0
        tmp_gpb['days_from_now']=tmp_gpb.apply(lambda x: (reference_date-x.date).days if x.status==1 else -1,axis=1)
        days_delta=tmp_gpb.days_from_now[tmp_gpb.days_from_now>0].reset_index(drop=True)
        days_delta_shifted=days_delta.shift(periods=-1)
        streak=days_delta_shifted-days_delta
        streak_gpb=[sum(1 for _ in l) for n, l in itertools.groupby(streak)]
        max_streak=max(streak_gpb)+1
        #last_break_length=0
        if days_delta[0]>0:
            last_break_length=days_delta[0]
        else:
            index_last_fail=streak.index[streak>1][0]
            last_break_length=int(days_delta[index_last_fail+1]-days_delta[index_last_fail]-1)

        cur_streak= 0 if days_delta[0]!=0 else ((streak_gpb[0]+1) if streak[0]==1 else 1)
    else: # assume it is count
        days_delta = pd.Series([int(x) for x in log_of_a_habit.status])
        cur_streak = days_delta.index[days_delta == 0][0]
        streak_gpb = [sum(1 for _ in l) for n, l in itertools.groupby(days_delta)]
        max_streak = max(streak_gpb)
        last_break_length = streak_gpb[1] if days_delta[0] == 1 else streak_gpb[0]
    return {'cur_streak':cur_streak,'max_streak':max_streak,'last_break_length':last_break_length}


def get_streak_data_for_all_habits(habit_details, habit_log, reference_date):
    """
    Determines streak metrics for all the habits and returns as dataframe
    :param habit_details: habit metadata for all habits
    :param habit_log: log of all habits
    :return: streak metrics for all habits as a dataframe
    """
    # name, current_streak, max_streak, last_break_length, last_reason, priority, days_from_start, status
    habit_streak = pd.DataFrame(
        columns=['small_desc', 'current_streak', 'max_streak', 'last_break_length', 'last_reason', 'days_from_start',
                 'habit_status'], index=habit_details.name)
    # print(habit_streak)
    for index, row in habit_details.iterrows():
        # print(row)
        habit_name = row['name']
        log_of_a_habit = habit_log[habit_log.name == habit_name].reset_index(drop=True)
        log_of_a_habit['status'] = (log_of_a_habit.status == 'p')
        habit_streak.loc[habit_name, 'small_desc'] = row['small_desc']
        habit_streak.loc[habit_name, 'habit_status'] = row['status']
        habit_streak.loc[habit_name, 'streak_type'] = row['streak_type']
        habit_streak.loc[habit_name, 'days_from_start'] = (reference_date - row['start_date']).days
        if log_of_a_habit.shape[0] > 0:
            streak_metric = get_metrics_for_a_habit_streak(log_of_a_habit, row['streak_type'], reference_date)
            habit_streak.loc[habit_name, 'current_streak'] = streak_metric['cur_streak']
            habit_streak.loc[habit_name, 'max_streak'] = streak_metric['max_streak']
            habit_streak.loc[habit_name, 'last_break_length'] = streak_metric['last_break_length']

    habit_streak.current_streak.fillna(0, inplace=True)
    habit_streak.max_streak.fillna(0, inplace=True)
    habit_streak.last_break_length.fillna(0, inplace=True)
    habit_streak.last_reason.fillna("", inplace=True)
    habit_streak = habit_streak.reset_index()
    return habit_streak


def get_current_habit_status(habit_streak):
    """
    Gives simple status for awareness (could be used for revision as well)
    Goal, 4 current (3 best, 22 days)

    Ordered by:
    priority, current/days (its so long and yet habit not formed)

    Color coded:
    red critical - just started or just failed - current streak < 5
    red - current streak < 7 and priority - 1
    orange - current streak < 7 and priority -2,3
    black - current streak > 7 and < 30
    green - streak > 30
    horizontal ruler after focus

    :param habit_streak: dataframe containing streak metric for all habits
    :return: dataframe containing info showing current status of habit (name, streak_str, description, priority, current_streak_by_total_days, current_streak)
    """

    habit_status=habit_streak.loc[:,['name','small_desc','habit_status','current_streak']]
    habit_status['streak_str']=habit_streak.apply(lambda x:"{current_streak}c ({max_streak}m, {days_from_start}d)".format(current_streak=x.current_streak,max_streak=x.max_streak,days_from_start=x.days_from_start),axis=1)
    habit_status['current_streak_by_total_days']=habit_streak.apply(lambda x:x.current_streak/x.days_from_start,axis=1)
    habit_status['habit_status_as_priority_number'] = habit_status.habit_status.apply(lambda x: 1 if x == 'focus' else (2 if x == 'now' else 3))
    return habit_status


def display_habit_status(habit_status):
    """
    Ordered by:
    priority, current/days (its so long and yet habit not formed)

    Color coded:
        Red - focus and current_streak <= 5
        Orange - now or later and current_streak <= 5
        black - current_streak > 5 and <= 30 (for all)
        green - current_streak > 30 (for all)
    horizontal ruler after focus

    :param habit_status:
    :return:
    """
    def get_font_attribute(df):
        color = ""
        if df.current_streak <= 5:
            color = 'red' if df.habit_status == 'focus' else 'orange'
        elif df.current_streak <= 30:
            color = 'black'
        else:
            color = 'green'
        return 'color=' + color

    table_config = ({'column_name_in_order_of_display': ['name', 'small_desc', 'streak_str', 'habit_status'],
                     'column_headers': ['Name', 'Description', 'Streak', 'Focus'],
                     'column_sort_by': ['habit_status_as_priority_number', 'current_streak_by_total_days'],
                     'column_sort_by_is_asc': [True, True],
                     'widths_in_pcntg': [10, 60, 20, 10],
                     'text_alignment': ['left', 'left', 'left', 'left'],
                     'column_name_whose_value_change_adds_horizontal_ruler': 'habit_status',
                     'column_name_needing_custom_formatting': 'small_desc',
                     'func_giving_font_attribute': get_font_attribute,
                     'table_heading': 'Current Status'
                     })
    my_util.display_html_table(habit_status, table_config)


def get_actions_against_habits(habit_log, habit_streak, reference_date):
    """
    Determines all the action which needs to be taken against the habits (failures or successes)

    Action Rules:
    * Pass and having Comment - add revise action for each if date within 2 days from now
    * Fail - add action corresponding to reason if date within 3 days from now, FT only for 1st day

    Ordered by:
        status and entry date

    Color code:
    * orange - failed yesterday (so most important to revise)
    * black - older dates
    * green - positive ones

    :param habit_log: log of all habits
    :param habit_streak: streak metrics for all habits
    :param reference_date:
    :return: dataframe with (name, weekday, reason, action)
    """

    # prepare revise action map
    habit_rev_action_map_raw=simplenote.get_note(habitRevisionActionMap)
    habit_rev_action=habit_rev_action_map_raw[0]['content'].splitlines()[1:]
    habit_rev_action=[ln.replace("*","").strip() for ln in habit_rev_action]
    habit_rev_action_csv="\n".join(habit_rev_action)
    habit_rev_action=pd.read_csv(StringIO(habit_rev_action_csv))
    habit_rev_action.columns=[x.strip().lower() for x in habit_rev_action.columns]
    habit_rev_action.reason=habit_rev_action.reason.apply(lambda x:str(x.strip().lower()))
    habit_rev_action.action=habit_rev_action.action.apply(lambda x:x.strip())
    habit_rev_action.action_subsequent=habit_rev_action.action_subsequent.apply(lambda x:x.strip())

    #Since only last 3 days data affects, so let's filter only last 3 days logs
    # now for all those day based habits where we don't have expilicit entry let's make explicit no entry with forget reason
    last3_days_habit_log=habit_log[habit_log.date.apply(lambda x: x.date() >= (reference_date - dt.timedelta(days=2)).date())]

    #cartesian product - for getting date X name
    date_last_3_days = [reference_date.date() - dt.timedelta(days=x) for x in range(0, 3)]
    active_habit_names=habit_streak.name[(habit_streak.habit_status!="later") & (habit_streak.streak_type=="day")]
    df1 = pd.DataFrame({'key':[1 for x in range(len(date_last_3_days))], 'date':date_last_3_days})
    df2 = pd.DataFrame({'key':[1 for x in range(len(active_habit_names))], 'name':active_habit_names})
    ideal_habit_log=pd.merge(df1, df2,on='key')[['date', 'name']]
    ideal_habit_log.date=pd.to_datetime(ideal_habit_log.date)
    ideal_habit_log=pd.merge(ideal_habit_log,last3_days_habit_log,on=['date','name'],how='left')
    ideal_habit_log=pd.merge(ideal_habit_log,habit_streak[['name','current_streak','max_streak','days_from_start','habit_status','small_desc']],on=['name'],how='left')
    ideal_habit_log.reason=ideal_habit_log.apply(lambda x: x.reason if not pd.isnull(x.status) else ('forgot' if x.max_streak>0 else 'not started'),axis=1)
    ideal_habit_log.status.fillna('f',inplace=True)
    ideal_habit_log.loc[ideal_habit_log.reason=='nan','reason']=''

    action_date_considered=pd.to_datetime(date_last_3_days)
    action_date_considered=action_date_considered.sort_values(ascending=False)
    # get action from last 2 days log
    habit_action_pass=ideal_habit_log.loc[(ideal_habit_log.date.isin(action_date_considered[0:2])) & (ideal_habit_log.status=='p') & (ideal_habit_log.reason!=''),['date','name','small_desc','habit_status','reason','status']]
    habit_action_fail=ideal_habit_log.loc[(ideal_habit_log.date.isin(action_date_considered[0:3])) & (ideal_habit_log.status=='f'),['date','name','small_desc','habit_status','reason','status']]
    habit_action=pd.concat([habit_action_pass,habit_action_fail],axis=0)
    habit_action['days_from_today']=abs(habit_action.date.apply(lambda x:(x.date()-reference_date.date()).days))+1
    # group by for same name & reason
    habit_action['status']=habit_action.status.apply(lambda x:int(x=='p'))
    habit_action_gpb=habit_action.groupby(['name','small_desc','habit_status','reason'],as_index=False)
    habit_action=habit_action_gpb.agg({'days_from_today':'min','status':'mean'})
    habit_action=pd.merge(habit_action,habit_rev_action,on='reason',how='left')
    habit_action['action_new']=habit_action.apply(lambda x: x.action if x.days_from_today==1 else x.action_subsequent, axis=1)
    habit_action['action']=habit_action['action_new']
    habit_action.drop(['action_new','action_subsequent'],axis=1,inplace=True)
    habit_action.sort_values(['status','days_from_today'],inplace=True)
    habit_action.action.fillna(value=list(habit_rev_action.loc[habit_rev_action.reason=='other','action'])[0],inplace=True)
    return habit_action


def display_habit_action(habit_action):
    # Habit Action
    # Ordered by: status and entry date
    # Color code: orange - failed yesterday (so most important to revise)
    # black - older dates
    # green - positive ones

    def get_font_attribute(df):
        color = ""
        if df.status == 1:
            color = 'green'
        elif df.days_from_today == 1:
            color = 'red' if df.habit_status == 'focus' else 'orange'
        else:
            color = 'black'
        return 'color=' + color

    table_config = ({'column_name_in_order_of_display': ['name', 'small_desc', 'reason', 'action'],
                     'column_headers': ['Name', 'Description', 'Reason', 'Action'],
                     'column_sort_by': ['habit_status', 'status', 'days_from_today'],
                     'column_sort_by_is_asc': [True, True, True],
                     'widths_in_pcntg': [10, 40, 20, 30],
                     'text_alignment': ['left', 'left', 'left', 'left'],
                     'column_name_whose_value_change_adds_horizontal_ruler': 'habit_status',
                     'column_name_needing_custom_formatting': 'small_desc',
                     'func_giving_font_attribute': get_font_attribute,
                     'table_heading': 'Actions'
                     })
    my_util.display_html_table(habit_action, table_config)


def get_habits_to_be_reviewed(habit_details, habit_log, habit_status, reference_date):
    # Habit Reviews
    # review happens on all days of week

    common_col_names=['name','review_type']
    # No entry in log - Review
    habit_last_entered_date=habit_log.groupby('name', as_index=False).agg({'date': 'max'})
    habit_last_entered_date['days_from_last_entry']=habit_last_entered_date.date.apply(lambda x,reference_date: (reference_date-x).days,args=[reference_date])
    habit_last_entered_date.drop(['date'],inplace=True,axis=1)
    missed_habit_review=pd.merge(habit_details[['id', 'name', 'streak_type', 'missed_review_cycle']], habit_last_entered_date, on='name', how='left')
    missed_habit_review=missed_habit_review.loc[missed_habit_review.streak_type=='count',:]
    missed_habit_review.days_from_last_entry.fillna(999,inplace=True) # if no entry found, add a big number
    missed_habit_review['days_from_last_entry']=missed_habit_review.days_from_last_entry.astype('int',copy=True)
    missed_habit_review=missed_habit_review.loc[missed_habit_review.days_from_last_entry>=missed_habit_review.missed_review_cycle]
    missed_habit_review['review_type']='Missed'
    missed_habit_review=missed_habit_review.loc[:,common_col_names]
    missed_habit_review

    # Scheduled Reviews
    def is_review_date_reached(habit_id,reference_date,review_cycle):
        offset_to_balance_load_across_days=habit_id%review_cycle # add 1 to avoid 0 date
        number_of_days_from_year_start=(reference_date.date()-dt.datetime.strptime(str(reference_date.year)+"/01/01","%Y/%m/%d").date()).days
        eligible_review_days=[offset_to_balance_load_across_days+x*review_cycle for x in range(int(365/review_cycle))]
        return (number_of_days_from_year_start in eligible_review_days)

    habit_review=habit_details[habit_details.apply(lambda x, reference_date: is_review_date_reached(x.id, reference_date, x.review_cycle), args=[reference_date], axis=1)]
    habit_review['review_type']='Scheduled'
    habit_review=habit_review.loc[:,common_col_names]
    habit_review=habit_review.loc[habit_review.name.isin(missed_habit_review.name)==False]

    habit_review=pd.concat([habit_review,missed_habit_review])
    habit_review=pd.merge(habit_review,habit_status,on='name',how='inner')
    habit_review.drop(['current_streak','current_streak_by_total_days'],inplace=True,axis=1)
    return habit_review


def display_habit_review(habit_review):
    """
    Sort by: review_type, habit_status
    Color Code:
        red - focus and missed
        black - now, later and missed
        green - scheduled review
    :param habit_review:
    :return:
    """
    def get_font_attribute(df):
        color = ""
        if df.review_type.lower() == 'missed':
            color = 'red' if df.habit_status == 'focus' else 'black'
        else:
            color = 'green'
        return 'color=' + color

    table_config = (
    {'column_name_in_order_of_display': ['name', 'small_desc', 'streak_str', 'habit_status', 'review_type'],
     'column_headers': ['Name', 'Description', 'Streak', 'Focus', 'Review Type'],
     'column_sort_by': ['review_type', 'habit_status'],
     'column_sort_by_is_asc': [True, True],
     'widths_in_pcntg': [10, 50, 20, 10, 10],
     'text_alignment': ['left', 'left', 'center', 'center', 'center'],
     'column_name_whose_value_change_adds_horizontal_ruler': None,
     'column_name_needing_custom_formatting': 'small_desc',
     'func_giving_font_attribute': get_font_attribute,
     'table_heading': 'Habit Review'
     })
    my_util.display_html_table(habit_review, table_config)


def display_habit_marked_as_later(habit_later, reference_date):
    """
    Sort by: start_date
    Color Code:
        red - if start_date > reference_date
        black - else
    :param habit_later: habit_details dataframe
    :param reference_date:
    :return:
    """
    habit_later['reference_date']=reference_date.date()  # so that it can be used in below function
    habit_later.start_date=habit_later.start_date.apply(lambda x:x.date())

    def get_font_attribute(df):
        color = "red" if df.start_date > df.reference_date else "black"
        return 'color=' + color

    table_config = (
    {'column_name_in_order_of_display': ['name', 'small_desc', 'streak_type', 'start_date'],
     'column_headers': ['Name', 'Description', 'Streak Type', 'Planned Start Date'],
     'column_sort_by': ['start_date'],
     'column_sort_by_is_asc': [True],
     'widths_in_pcntg': [10, 60, 15, 15],
     'text_alignment': ['left', 'left', 'center', 'center'],
     'column_name_whose_value_change_adds_horizontal_ruler': None,
     'column_name_needing_custom_formatting': 'small_desc',
     'func_giving_font_attribute': get_font_attribute,
     'table_heading': 'Habit On Hold'
     })
    my_util.display_html_table(habit_later, table_config)


def display_all_habit_metric_n_status(reference_date):
    habit_details_all = get_current_habits()
    habit_details = habit_details_all.loc[habit_details_all.status != 'later', :]
    habit_log = get_habit_log(reference_date)
    habit_log = habit_log.loc[habit_log.name.isin(habit_details.name), :]
    habit_streak = get_streak_data_for_all_habits(habit_details, habit_log, reference_date)
    habit_action = get_actions_against_habits(habit_log, habit_streak, reference_date)
    habit_status = get_current_habit_status(habit_streak)
    habit_review = get_habits_to_be_reviewed(habit_details, habit_log, habit_status, reference_date)
    habit_details_later = habit_details_all.loc[habit_details_all.status == 'later', :]
    display_habit_action(habit_action)
    display(HTML("</br><hr>"))
    display_habit_review(habit_review)
    display(HTML("</br><hr>"))
    display_habit_status(habit_status)
    display(HTML("</br><hr>"))
    display_habit_marked_as_later(habit_details_later, reference_date)

# lets try to commit some comembts