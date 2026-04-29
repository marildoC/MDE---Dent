from .query_router import execute_query
from .suggestions import suggestions_for


def answer_question(question):
    return execute_query(question)


def question_suggestions(query):
    return suggestions_for(query)
