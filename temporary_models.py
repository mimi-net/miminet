# Temporary
from random import randint


class Quiz:
    def __init__(self, id):
        self.id = id
        self.guid = id
        self.title = f'Название теста номер {id}'
        self.description = f'Описание теста номер {id}'
        self.sections = randint(1, 9)
        self.passed = randint(0, self.sections)


class Section:
    def __init__(self, id):
        self.id = id
        self.guid = id
        self.title = f'Название темы номер {id}'
        self.description = f'Описание темы номер {id}'
