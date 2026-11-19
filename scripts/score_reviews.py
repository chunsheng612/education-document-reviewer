"""Validate evidence-backed reviews, score and group them. No document/LLM grading."""
import argparse,csv,json,statistics
from collections import Counter,defaultdict
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

DIMS=('R','C','E','U','F')
GROUP_FIELDS=('task_id','document_type','stage','requirements_id','template_id')

def nonempty(value,label):
    if not isinstance(value,str) or not value.strip():raise ValueError(label+' must be nonempty text')

def rounded(value):return float(Decimal(value).quantize(Decimal('.01'),rounding=ROUND_HALF_UP))

def grade(score):
    return 'A' if score>=85 else 'B' if score>=70 else 'C' if score>=50 else 'D'

def summarize(payload):
    if payload.get('schema_version')!=1:raise ValueError('schema_version must be1')
    rubric=payload.get('rubric',{})
    nonempty(rubric.get('version'),'rubric.version')
    weights=rubric.get('weights',{})
    if set(weights)!=set(DIMS):raise ValueError('weights must contain R,C,E,U,F')
    if any(isinstance(v,bool) or not isinstance(v,(float,int)) or v<=0 for v in weights.values()):raise ValueError('weights must be positive numbers')
    dw={k:Decimal(str(v)) for k,v in weights.items()}
    if sum(dw.values())!=100:raise ValueError('weights must sum to100')
    reviews=payload.get('reviews')
    if not isinstance(reviews,list) or not reviews:raise ValueError('reviews must be nonempty')
    seen=set();results=[];groups=defaultdict(list)
    for r in reviews:
        sid=r.get('submission_id');nonempty(sid,'submission_id')
        if sid in seen:raise ValueError('duplicate submission_id: '+sid)
        seen.add(sid)
        for f in ('revision','reviewer_id','review_mode'):nonempty(r.get(f),f)
        comp=r.get('comparison',{})
        for f in GROUP_FIELDS:nonempty(comp.get(f),'comparison.'+f)
        criteria=r.get('criteria',{})
        if set(criteria)!=set(DIMS):raise ValueError(sid+':criteria must contain all5 dimensions')
        lower=Decimal(0);unknown_weight=Decimal(0);dimension_scores={}
        for dim in DIMS:
            c=criteria[dim];level=c.get('level');nonempty(c.get('reason'),sid+':'+dim+'.reason')
            if level is None:
                unknown_weight+=dw[dim];dimension_scores[dim]=None;continue
            if type(level) is not int or not 0<=level<=4:raise ValueError(sid+':level must be integer0..4 or null')
            evid=c.get('evidence',[])
            if not isinstance(evid,list) or not evid:raise ValueError(sid+':'+dim+' needs evidence')
            for e in evid:
                for f in ('location','quote','judgment'):nonempty(e.get(f),sid+':'+dim+'.'+f)
            value=dw[dim]*Decimal(level)/4;lower+=value;dimension_scores[dim]=rounded(value)
        issues=r.get('issues',[])
        if not isinstance(issues,list):raise ValueError('issues must be list')
        issue_ids=set()
        for issue in issues:
            iid=issue.get('id');nonempty(iid,'issue.id')
            if iid in issue_ids:raise ValueError(sid+':duplicate issue id')
            issue_ids.add(iid)
            if issue.get('severity') not in ('blocking','major','minor','advisory'):raise ValueError('invalid severity')
            if issue.get('primary_dimension') not in DIMS:raise ValueError('invalid issue dimension')
            for f in ('category','location','evidence','impact','required_change','acceptance'):nonempty(issue.get(f),'issue.'+f)
        blockers=r.get('blockers',[])
        if not isinstance(blockers,list):raise ValueError('blockers must be list')
        block_ids=set()
        for b in blockers:
            iid=b.get('issue_id')
            if b.get('verified') is not True or iid not in issue_ids:raise ValueError('blocker must reference verified issue')
            if not any(i['id']==iid and i['severity']=='blocking' for i in issues):raise ValueError('blocker must reference blocking issue')
            if iid in block_ids:raise ValueError('duplicate blocker')
            block_ids.add(iid)
        if {i['id'] for i in issues if i['severity']=='blocking'}!=block_ids:raise ValueError('all blocking issues require verified blockers')
        exact=unknown_weight==0;score=rounded(lower) if exact else None
        state=('關鍵退修' if blockers else '資料不足暫緩判定' if not exact else
               '修訂後使用' if any(i['severity']!='advisory' for i in issues) or score<85 else '可用')
        result={'submission_id':sid,'revision':r['revision'],'comparison':comp,
                'score':score,'score_lower':rounded(lower),'score_upper':rounded(lower+unknown_weight),
                'observed_weight':rounded(100-unknown_weight),'grade':grade(score) if exact else None,
                'status':state,'rank':None,'rank_eligible':exact and not blockers,
                'dimension_scores':dimension_scores,'criteria':criteria,'issues':issues,'blockers':blockers,
                'verification_gaps':r.get('verification_gaps',[]),'strengths':r.get('strengths',[]),
                'reviewer_id':r['reviewer_id'],'review_mode':r['review_mode']}
        key=tuple(comp[f] for f in GROUP_FIELDS)+(rubric['version'],tuple(weights[d] for d in DIMS))
        results.append(result);groups[key].append(result)
    group_output=[]
    for records in groups.values():
        eligible=sorted((r for r in records if r['rank_eligible']),key=lambda r:(-r['score'],r['submission_id']))
        rank=0;previous=None
        for i,r in enumerate(eligible,1):
            if r['score']!=previous:rank=i
            r['rank']=rank;previous=r['score']
        counts=Counter(cat for r in records for cat in {i['category'] for i in r['issues']})
        group_output.append({'comparison':records[0]['comparison'],'count':len(records),
             'ranked_count':len(eligible),'grade_distribution':dict(Counter(r['grade'] or '暫緩' for r in records)),
             'status_distribution':dict(Counter(r['status'] for r in records)),
             'dimension_level_means':{d:round(statistics.mean(vals),2) if (vals:=[r['criteria'][d]['level'] for r in records if r['criteria'][d]['level'] is not None]) else None for d in DIMS},
             'issue_document_counts':dict(counts),'submission_ids':[r['submission_id'] for r in records]})
    return {'schema_version':1,'rubric':rubric,'reviews':results,'groups':group_output,
            'limits':'Scores depend on reviewer judgments; script does not inspect documents or validate semantic evidence. Ranks are only within identical comparison groups.'}

def csvsafe(value):
    s='' if value is None else str(value)
    return "'"+s if s.startswith(('=','+','-','@')) else s

def export(result,output_dir):
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    (out/'批改彙整.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    fields=['submission_id','revision',*GROUP_FIELDS,'score','score_lower','score_upper','grade','status','rank','observed_weight']
    with (out/'作品比較.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in result['reviews']:
            row={**r,**r['comparison']};writer.writerow({k:csvsafe(row.get(k)) for k in fields})
    with (out/'問題清單.csv').open('w',encoding='utf-8-sig',newline='') as f:
        cols=['submission_id','id','category','severity','primary_dimension','location','evidence','impact','required_change','acceptance']
        writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader()
        for r in result['reviews']:
            for issue in r['issues']:writer.writerow({k:csvsafe(({**issue,'submission_id':r['submission_id']}).get(k)) for k in cols})

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('input');parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();payload=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    try:result=summarize(payload)
    except (ValueError,KeyError,TypeError) as e:parser.exit(2,'Invalid review data: '+str(e)+'\n')
    export(result,args.output_dir)
    print(json.dumps({'reviews':len(result['reviews']),'groups':len(result['groups']),'output_dir':str(Path(args.output_dir).resolve())},ensure_ascii=False))

if __name__=='__main__':main()
