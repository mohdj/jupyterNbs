def getIlmRevisionLog():
    import simplenote as sn
    from io import StringIO
    import pandas as pd
    import datetime as dt
    import matplotlib.pyplot as plt
    import ast
    import pyperclip
    import os
    #%matplotlib inline

    simplenote = sn.Simplenote('mohdjamal8453@gmail.com', 'simple123')
    ilm_note_key="5f7cb643ec884642b250954ff3996f8c"
    ilmRevLogKey="9ad07e0dc9e84909b17795e101683c68"

    maula_vaaz_identifier=['maula','ashara']
    # [0,1,2,5,10,21,52,88,140] earlier
    revsion_schedule=[0,1,3,5,10,21,52,88,140]+[(140+(x+1)*52) for x in range(5)] # assign for next 5 years as well
    revsion_schedule=[x*7 for x in revsion_schedule]

    # [0,1,2,5,10,21,52] earlier
    revsion_schedule_for_maula_vaaz=[0,1,3,5,10,21,52]+[(52+(x+1)*30) for x in range(10)] # revise maula tus bayaan every 7 months all
    revsion_schedule_for_maula_vaaz=[x*7 for x in revsion_schedule_for_maula_vaaz]

    ilm_note_raw=simplenote.get_note(ilm_note_key)

    ilmNote=ilm_note_raw[0]['content'].splitlines()[1:]
    ilmNote=[ln.replace("*","").strip() for ln in ilmNote]
    ilmcsv="\n".join(ilmNote)
    datilm=pd.read_csv(StringIO(ilmcsv))
    datilm.columns=[x.strip() for x in datilm.columns]
    datilm['date']=pd.to_datetime(datilm['date'],format="%d/%m/%y")
    datilm['weekstartdate']=datilm['date'].dt.to_period('W').apply(lambda r: r.start_time)-dt.timedelta(days=1)

    day_of_week = dt.datetime.now().weekday() + 1
    day_of_week = 0 if day_of_week == 7 else day_of_week
    cur_week_start_date=dt.datetime.now() - dt.timedelta(days=day_of_week)
    datilm['daysDifference']=datilm.weekstartdate.apply(lambda ilmdate, curWeekStartDate: (curWeekStartDate-ilmdate).days,args=[cur_week_start_date])

    is_aqa_maula_vaaz=datilm.name.apply(lambda x: any([y in x.lower() for y in maula_vaaz_identifier]))
    datilm_maula=datilm.loc[is_aqa_maula_vaaz,:]
    datilm_other=datilm.loc[~is_aqa_maula_vaaz,:]
    revlog=pd.concat([datilm_maula[datilm_maula.daysDifference.isin(revsion_schedule_for_maula_vaaz)],datilm_other[datilm_other.daysDifference.isin(revsion_schedule)]])
    revlog=revlog[['name','maturity']]
    #revlog=datilm.loc[datilm.daysDifference.isin(revsionSchedule),['name','maturity']]
    revlog['date']=dt.datetime.strftime(cur_week_start_date,format="%d/%m/%y")
    revlog['rating']="na"
    revlog['timetaken']="na"
    revlog=revlog[['date','name','maturity','rating','timetaken']]
    #pyperclip.copy(revlog.to_csv(index=False, header=False,line_terminator=os.linesep))
    # print(datilm[datilm.daysDifference.isin(revsionSchedule)])
    print(revlog.to_csv(index=False, header=False))
