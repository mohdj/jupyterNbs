def getIlmRevisionLog():
    import simplenote as sn
    from io import StringIO
    import pandas as pd
    import datetime as dt
    import matplotlib.pyplot as plt
    import ast
    import pyperclip
    #%matplotlib inline

    simplenote = sn.Simplenote('mohdjamal8453@gmail.com', 'simple123')
    taskNoteKey="41d06e8ced6c42389127e0d727974230"
    ilmNoteKey="5f7cb643ec884642b250954ff3996f8c"
    ilmRevLogKey="9ad07e0dc9e84909b17795e101683c68"
    monthlyGoalNoteKey="ba7047bd84204ab49e9e271a5b164675"

    maula_vaaz_identifier=['maula','ashara']

    revsionSchedule=[0,1,2,5,10,21,52,88,140]+[(140+(x+1)*52) for x in range(5)] # assign for next 5 years as well
    revsionSchedule=[x*7 for x in revsionSchedule]

    revsionSchedule_MaulaVaaz=[0,1,2,5,10,21,52]+[(52+(x+1)*30) for x in range(10)] # revise maula tus bayaan every 7 months all
    revsionSchedule_MaulaVaaz=[x*7 for x in revsionSchedule_MaulaVaaz]

    ilmNoteRaw=simplenote.get_note(ilmNoteKey)

    ilmNote=ilmNoteRaw[0]['content'].splitlines()[1:]
    ilmNote=[ln.replace("*","").strip() for ln in ilmNote]
    ilmcsv="\n".join(ilmNote)
    datilm=pd.read_csv(StringIO(ilmcsv))
    datilm.columns=[x.strip() for x in datilm.columns]
    datilm['date']=pd.to_datetime(datilm['date'],format="%d/%m/%y")
    datilm['weekstartdate']=datilm['date'].dt.to_period('W').apply(lambda r: r.start_time)-dt.timedelta(days=1)

    curWeekStartDate=dt.datetime.now() - dt.timedelta(days=dt.datetime.now().weekday()+1)
    datilm['daysDifference']=datilm.weekstartdate.apply(lambda ilmdate, curWeekStartDate: (curWeekStartDate-ilmdate).days,args=[curWeekStartDate])

    isAqaMaulaVaaz=datilm.name.apply(lambda x: any([y in x.lower() for y in maula_vaaz_identifier]))
    datilm_maula=datilm.loc[isAqaMaulaVaaz,:]
    datilm_other=datilm.loc[~isAqaMaulaVaaz,:]
    revlog=pd.concat([datilm_maula[datilm_maula.daysDifference.isin(revsionSchedule_MaulaVaaz)],datilm_other[datilm_other.daysDifference.isin(revsionSchedule)]])
    revlog=revlog[['name','maturity']]
    #revlog=datilm.loc[datilm.daysDifference.isin(revsionSchedule),['name','maturity']]
    revlog['date']=dt.datetime.strftime(curWeekStartDate,format="%d/%m/%y")
    revlog['rating']="na"
    revlog['timetaken']="na"
    revlog=revlog[['date','name','maturity','rating','timetaken']]
    pyperclip.copy(revlog.to_csv(index=False, header=False,line_terminator=os.linesep))
    # print(datilm[datilm.daysDifference.isin(revsionSchedule)])
    print(revlog.to_csv(index=False, header=False))
