from statistics import fmean
from fcea.core.errors import ValidationError
from fcea.analysis.statistics import column,number,mean_difference,mean_z_pvalue,adjust_pvalues


def execute_tests(specs,evidence,multiplicity,alpha):
    records=[]; statistical=[]
    for spec in specs:
        data=evidence[spec.evidence_ref]['value']
        if not isinstance(data,list) or not data:
            raise ValidationError('Falsification tests need a nonempty row table')
        values=column(data,spec.column)
        if spec.metric=='mean': observed=fmean(values)
        elif spec.metric=='max_abs': observed=max(abs(v) for v in values)
        elif spec.metric=='count': observed=float(len(values))
        elif spec.metric=='difference':
            group=spec.parameters.get('group','treatment')
            grouped={0:[],1:[]}
            for row,val in zip(data,values):
                g=number(row.get(group))
                if g not in (0,1): raise ValidationError('Invalid test group')
                grouped[int(g)].append(val)
            observed=mean_difference(grouped[1],grouped[0])
        else:
            if spec.accept!='no_rejection':
                raise ValidationError('z_pvalue tests use no_rejection acceptance')
            observed=mean_z_pvalue(values,number(spec.parameters.get('null',0)))
            statistical.append((len(records),observed))
        if spec.accept=='lte': accepted=observed<=spec.threshold
        elif spec.accept=='gte': accepted=observed>=spec.threshold
        elif spec.accept=='abs_lte': accepted=abs(observed)<=spec.threshold
        elif spec.metric=='z_pvalue': accepted=True  # Assigned after the frozen family correction.
        else: raise ValidationError('no_rejection requires z_pvalue')
        records.append({'test_id':spec.id,'kind':spec.kind,'target':spec.target,'critical':spec.critical,
            'metric':spec.metric,'observed':observed,'threshold':spec.threshold,'accepted':accepted,
            'evidence_ref':spec.evidence_ref,'interpretation':'Test can weaken its specified target; survival is not proof of truth.'})
    adjusted=adjust_pvalues([p for _,p in statistical],multiplicity)
    for (index,_),p in zip(statistical,adjusted):
        records[index].update(adjusted_pvalue=p,accepted=p>=alpha,alpha=alpha,
            interpretation='Failure to reject a negative control is not equivalence evidence; low power can hide bias.')
    return records
