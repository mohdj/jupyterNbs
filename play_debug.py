# coding: utf-8

# In[652]:
import simplenote as sn
from io import StringIO
import pandas as pd
import datetime as dt
import my_util
import matplotlib.pyplot as plt
import ast
from IPython.core.display import display, HTML

simplenote = sn.Simplenote('mohdjamal8453@gmail.com', 'simple123')
taskNoteKey = "41d06e8ced6c42389127e0d727974230"
ilmNoteKey = "5f7cb643ec884642b250954ff3996f8c"
ilmRevLogKey = "9ad07e0dc9e84909b17795e101683c68"
monthlyGoalNoteKey = "ba7047bd84204ab49e9e271a5b164675"


def get_tasks(reference_date):
    dat = simplenote.get_note(taskNoteKey)
    tasks = ""
    curdate = ""
    for ln in dat[0]['content'].splitlines():
        if '*' not in ln and len(ln.strip()) > 0:
            curdate = ln.strip() + ' ' + str(reference_date.year)
        elif '*' in ln:
            if ln.count(",") == 3:
                ln = ln + ",1"
            tasks = tasks + "\n" + curdate + "," + ln
    tasks = tasks.splitlines()
    tasks = [ln.replace("*", "") for ln in tasks if len(ln.split(",")) == 6]
    tasks = pd.read_csv(StringIO('\n'.join(tasks)), header=None,
                        names=['Date', 'EndTime', 'Category', 'Desc', 'Duration', 'Point'])
    tasks['Date'] = pd.to_datetime(tasks['Date'], format="%b %d %Y")
    tasks.Category = tasks.Category.apply(lambda x: x.strip().lower())  # remove whitestrips
    tasks['DateStr'] = tasks.Date.apply(lambda x: dt.datetime.strftime(x, format="%b-%d"))
    tasks['Duration'] = pd.to_numeric(tasks.Duration, errors="coerce")  # coerce to numeric if any blank durations
    return tasks


def __get_goal_details(reference_date):
    rawGoal = simplenote.get_note(monthlyGoalNoteKey)
    rawGoal = rawGoal[0]['content'].splitlines()
    rawGoal = [ln for ln in rawGoal if ln.strip() != ""]

    goal_config = ast.literal_eval(rawGoal[1].strip())  # 1st line after note heading ought to be goal config
    goal_config['From'] = dt.datetime.strptime(goal_config['From'] + ' ' + str(reference_date.year), "%b %d %Y")
    goal_config['To'] = dt.datetime.strptime(goal_config['To'] + ' ' + str(reference_date.year), "%b %d %Y")
    goal_config['holidays'] = goal_config['holidays'].split(",")
    goal_config['holidays'] = [dt.datetime.strptime(x + "/" + str(reference_date.year), "%d/%m/%Y") for x in
                               goal_config['holidays']]

    goal = ""
    for ln in rawGoal:
        if '---' in ln:
            break
        elif '*' in ln:
            ln = ln.replace('*', "")
            goal = goal + "\n" + ln
    goal = goal.splitlines()
    goal = [ln for ln in goal if len(ln.split(",")) == 4]
    goal = pd.read_csv(StringIO('\n'.join(goal)), header=0, names=['short_name', 'task', 'hours_committed', 'priority'])
    goal['short_name'] = [x.strip() for x in goal['short_name']]
    return goal, goal_config


def is_task_within_goal(task_dates, goal_config):
    def isWithinGoal_func(date, startDate, endDate, holidays=[], excludeWeekend=True):
        endDate = endDate - dt.timedelta(days=1)  # increasing date by 1 for easier comparison
        # check if date within start and enddate, if not in holidays and if not a weekend
        if (excludeWeekend):
            out = (date >= startDate) & (date < endDate) & (date not in holidays) & (date.dayofweek not in [4, 5])
        else:
            out = (date >= startDate) & (date < endDate) & (date not in holidays)
        return out

    is_within_goal = task_dates.apply(isWithinGoal_func,
                                      args=[goal_config['From'], goal_config['To'], goal_config['holidays']])
    return is_within_goal


def get_goal_along_with_all_metrics(tasks, reference_date):
    # Pull goal details from simplenote
    goal, goal_config = __get_goal_details(reference_date)

    # isWithinGoal = is_task_within_goal(tasks['Date'],goal_config)
    goal_category = [x.strip() for x in goal.short_name.unique()]
    tasks_in_goal = tasks[(is_task_within_goal(tasks['Date'], goal_config)) & (tasks.Category.isin(goal_category))]
    duration_by_category = tasks_in_goal.groupby('Category', as_index=False)['Duration'].sum().rename(
        columns={'Duration': 'hours_completed'})
    point_by_category = tasks_in_goal.groupby('Category', as_index=False)['Point'].mean().rename(
        columns={'Point': 'avg_point'})
    goal = goal.merge(duration_by_category, how='left', left_on='short_name', right_on='Category')
    goal = goal.drop('Category', axis=1)
    goal = goal.merge(point_by_category, how='left', left_on='short_name', right_on='Category')
    goal = goal.drop('Category', axis=1)

    goal['hours_completed'] = round(goal['hours_completed'] / 60, 1)
    goal = goal.fillna(0)
    goal['hours_remaining'] = goal['hours_committed'] - goal['hours_completed']

    # sort as per priority - currently only based on hours remaining and additional priority for those not started.
    goal['priority'] = goal['priority'].apply(lambda x: x.strip())
    goal['priority'] = goal['priority'].apply(lambda x: 1 if x == 'L' else (10000 if x == 'M' else 100000))
    goal['priority'] = goal['priority'] + goal['hours_remaining']
    goal['priority'] = goal.apply(lambda x: x.priority if x['hours_completed'] > 0 else (x.priority + 10000), axis=1)
    goal['priority'] = goal.apply(lambda x: x.priority if x['hours_remaining'] > 0 else 0, axis=1)
    goal = goal.sort_values(['priority'], ascending=False)
    goal = goal.reset_index(drop=True)
    return goal, goal_config


def determine_n_display_goal_metrics(tasks,tasks_in_goal,goal,goal_config,reference_date):
    currentWeek = int(reference_date.strftime('%W'))
    isCurrentWeek = tasks.Date.apply(
        lambda x, currentWeek: int((x + dt.timedelta(days=1)).strftime('%W')) == currentWeek, args=[currentWeek])

    dates_in_goal_period = [x for x in pd.date_range(start=goal_config['From'], end=goal_config['To'])]
    total_days = len([x for x in dates_in_goal_period if x.weekday() not in [4, 5]]) - len(goal_config['holidays'])
    hours_available = total_days * goal_config['hours']
    hours_committed = goal.hours_committed.sum()
    hours_completed = round(goal['hours_completed'].sum(), 1)

    goal_dates_till_now = [x for x in pd.date_range(start=goal_config['From'], end=reference_date)]
    holidays_till_now = [x for x in goal_config['holidays'] if x < (reference_date + dt.timedelta(days=1))]
    total_days_till_now = len([x for x in goal_dates_till_now if x.weekday() not in [4, 5]]) - len(holidays_till_now)
    hours_to_be_completed = total_days_till_now * goal_config['hours']
    hours_lagging_by = round(hours_to_be_completed - hours_completed, 1)
    days_from_deadline = total_days - total_days_till_now

    # Goal Metrics
    goal_hrs_in_cur_week = tasks_in_goal.Duration[isCurrentWeek].sum() / 60
    days_remaining_in_cur_week = 5 - (reference_date + dt.timedelta(days=1)).weekday()
    ideal_goal_hrs_till_now_in_week = ((reference_date + dt.timedelta(days=1)).weekday()) * goal_config['hours']
    weekly_goal_hr_lagging = round(ideal_goal_hrs_till_now_in_week - goal_hrs_in_cur_week, 1)

    uncommitted_hours = hours_available - hours_committed
    comitment_metric_str = "<font color='maroon'>Uncommitted Hours: </font><b>{uncommitted_hours}</b> (out of {hours_available})".format(
        uncommitted_hours=uncommitted_hours, hours_available=hours_available)

    weekly_lagging_by_str = "Weekly lagging by:" if weekly_goal_hr_lagging >= 0 else "Weekly leading by:"
    weekly_lagging_by_str = "<font color='maroon'>" + weekly_lagging_by_str + "</font>"
    weekly_lagging_by_str += "<b>{weekly_goal_hr_lagging} hr</b> ({days_remaining_in_cur_week} days remaining in week)".format(
        weekly_goal_hr_lagging=abs(weekly_goal_hr_lagging), days_remaining_in_cur_week=days_remaining_in_cur_week)

    lagging_by_str = "Lagging by:" if hours_lagging_by >= 0 else "Leading by:"
    lagging_by_str = "<font color='maroon'>" + lagging_by_str + "</font>"
    lagging_by_str += "<b>{hours_lagging_by} hr</b> ({hours_completed} / {hours_committed})".format(
        hours_lagging_by=abs(hours_lagging_by), hours_completed=hours_completed, hours_committed=hours_committed)
    days_remaining = total_days - total_days_till_now
    days_from_deadline_str = "<font color='maroon'>Days from deadline: </font><b>{days_remaining}</b> (out of {total_days})".format(
        days_remaining=days_remaining, total_days=total_days)
    metric_goal_html_str = "<h4>Goals:</h4>" + weekly_lagging_by_str + "</br>" + lagging_by_str + "</br>" + comitment_metric_str + "</br>" + days_from_deadline_str + "</br>"
    display(HTML(metric_goal_html_str))


def determine_n_display_focused_hour_metric(tasks,tasks_in_goal,goal_config,reference_date):
    # Focused Hour Metrics
    avg_FT_task_hr_in_last3_days = (
        tasks.loc[tasks.Date.apply(lambda x: (x.weekday() not in [4, 5]) & (x.date() < reference_date.date()) & (
            x.date() >= (reference_date.date() - dt.timedelta(days=7))))]
        .groupby('Date', as_index=False)['Duration'].sum()
        .sort_values('Date', ascending=False).reset_index(drop=True).head(3)
        .loc[:, 'Duration'].mean() / 60
    )
    avg_FT_task_hr_in_last3_days_in_goal = (
        tasks_in_goal.loc[tasks_in_goal.Date.apply(lambda x: (x.date() < reference_date.date()) & (
            x.date() >= (reference_date.date() - dt.timedelta(days=7))))]
        .groupby('Date', as_index=False)['Duration'].sum()
        .sort_values('Date', ascending=False).reset_index(drop=True).head(3)
        .loc[:, 'Duration'].mean() / 60
    )
    FT_task_hr_today_in_goal = tasks_in_goal.loc[tasks_in_goal.Date.apply(lambda x: x.date() == reference_date.date())][
                                   'Duration'].sum() / 60
    FT_task_hr_today = tasks[tasks.Date.apply(lambda x: x.date() == reference_date.date())]['Duration'].sum() / 60

    last3_day_avg_in_goal_str = "<font color='maroon'>Goal: </font><b>{FT_task_hr_today_in_goal}</b> hr (avg {avg_FT_task_hr_in_last3_days_in_goal} hr out of {total_committed_goal_hour_per_day} hr)".format(
        avg_FT_task_hr_in_last3_days_in_goal=round(avg_FT_task_hr_in_last3_days_in_goal, 1),
        total_committed_goal_hour_per_day=goal_config['hours'], FT_task_hr_today_in_goal=FT_task_hr_today_in_goal)
    last3_day_avg_str = "<font color='maroon'>Total: </font><b>{FT_task_hr_today}</b> hr (avg {avg_FT_task_hr_in_last3_days} hr)".format(
        avg_FT_task_hr_in_last3_days=round(avg_FT_task_hr_in_last3_days, 1), FT_task_hr_today=FT_task_hr_today)
    metric_FT_html_str = "<h4>Focused Hours (today):</h4>" + last3_day_avg_str + "</br>" + last3_day_avg_in_goal_str + "</br>"
    display(HTML(metric_FT_html_str))


def display_goal_status(goal):
    """
    Sort by: review_type, habit_status
    Color Code:
        red - focus and missed
        black - now, later and missed
        green - scheduled review
    :param goal:
    :return:
    """
    def get_font_attribute(df):
        color = ""
        if df.hours_remaining <= 0:
            color = 'grey'
        elif df.hours_remaining <= 1:
            color = 'red'
        elif df.hours_completed > 0:
            color='blue'
        else:
            color='black'
        return 'color=' + color

    table_config = (
    {'column_name_in_order_of_display': ['short_name', 'task', 'hours_remaining', 'avg_point'],
     'column_headers': ['Name', 'Description', 'Remaining', 'Points'],
     'column_sort_by': ['priority'],
     'column_sort_by_is_asc': [True],
     'widths_in_pcntg': [20, 60, 10, 10],
     'text_alignment': ['left', 'left', 'center', 'center'],
     'column_name_whose_value_change_adds_horizontal_ruler': None,
     'column_name_needing_custom_formatting': 'task',
     'func_giving_font_attribute': get_font_attribute,
     'table_heading': 'Goal Status'
     })
    my_util.display_html_table(goal, table_config)


def calculate_n_display_task_n_goal_metrics(reference_date):
    tasks = get_tasks(reference_date)
    goal, goal_config = get_goal_along_with_all_metrics(tasks, reference_date)

    # Get hours completed against goal from tasks and append to existing goal
    goal_category = [x.strip() for x in goal.short_name.unique()]
    tasks_in_goal = tasks[(is_task_within_goal(tasks['Date'], goal_config)) & (tasks.Category.isin(goal_category))]
    determine_n_display_focused_hour_metric(tasks, tasks_in_goal, goal_config, reference_date)
    determine_n_display_goal_metrics(tasks, tasks_in_goal, goal, goal_config, reference_date)
    display_goal_status(goal)

