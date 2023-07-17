from .models import *
import datetime
import json
from django.db import transaction


import logging
logger = logging.getLogger(__name__)

def backup():
    data = {
        "last_updated" : datetime.datetime.now().timestamp(),
        "recommended_problems" : []
    }
    
    recommended_problems = RecommendedProblem.objects.all().prefetch_related('problem')
    for recommended_problem in recommended_problems:
        data['recommended_problems'].append(
            {
                'handle' : recommended_problem.handle,
                'problem_id' : recommended_problem.problem.problem_id,
                'date' : recommended_problem.date
            }
        )   
    
    logger.info(f'All Recommendation Backed up : {len(recommended_problems)}')
        
    with open('backup.json', 'w') as bk:
        json.dump(data, bk, indent=2)
    

def restore():
    with open('backup.json', 'r') as bk:
        data = json.load(bk)
    
    recommended_problems_set = set(RecommendedProblem.objects.all().values_list('handle', 'problem__problem_id'))

    problems_dict = {problem.problem_id: problem for problem in Problem.objects.all()}

    recommended_problems_to_create = []

    for recommended_problem_data in data['recommended_problems']:
        handle = recommended_problem_data['handle']
        problem_id = recommended_problem_data['problem_id']
        date = recommended_problem_data['date']

        if (handle, problem_id) not in recommended_problems_set and problem_id in problems_dict:
            problem = problems_dict[problem_id]

            recommended_problem = RecommendedProblem(
                handle=handle,
                problem=problem,
                date=date
            )
            recommended_problems_to_create.append(recommended_problem)

    with transaction.atomic():
        RecommendedProblem.objects.bulk_create(recommended_problems_to_create)
    transaction.commit()
    
    logger.info(f"{len(recommended_problems_to_create)} backed up Recommendation restored")
